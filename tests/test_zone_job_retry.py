"""Tests for the single retry of a zone job the mower did not acknowledge.

Home Assistant and pyworxcloud are stubbed so the real coordinator methods
run against a fake mower: the first publish can time out (the mower sleeps
at its base), the retry waits for the mower to report in, and a second
timeout raises a repair issue.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

PACKAGE = "worx_retry_pkg"
SOURCE = Path(__file__).parents[1] / "custom_components" / "worx_vision_cloud"


def _module(name: str, **attrs) -> ModuleType:
    module = sys.modules.get(name) or ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


class HomeAssistantError(Exception):
    """Stub of homeassistant.exceptions.HomeAssistantError."""


class TimeoutException(Exception):
    """Stub of pyworxcloud's response timeout."""


class NoConnectionError(Exception):
    """Stub of pyworxcloud's connection error."""


class _Coordinator:
    def __class_getitem__(cls, _item):
        return cls


ISSUES: dict[str, dict] = {}


def _create_issue(_hass, _domain, issue_id, **kwargs):
    ISSUES[issue_id] = kwargs


def _delete_issue(_hass, _domain, issue_id):
    ISSUES.pop(issue_id, None)


def _install_stubs() -> None:
    _module("aiohttp", ClientError=Exception, ClientTimeout=object)
    _module("homeassistant")
    _module("homeassistant.config_entries", ConfigEntry=object)
    _module("homeassistant.core", HomeAssistant=object, callback=lambda func: func)
    _module("homeassistant.exceptions", HomeAssistantError=HomeAssistantError)

    class _Platform:
        def __getattr__(self, name):
            return name.lower()

    _module("homeassistant.const", Platform=_Platform())
    _module("homeassistant.helpers")
    _module("homeassistant.helpers.device_registry")
    _module(
        "homeassistant.helpers.issue_registry",
        async_create_issue=_create_issue,
        async_delete_issue=_delete_issue,
        IssueSeverity=SimpleNamespace(WARNING="warning"),
    )
    sys.modules["homeassistant.helpers"].device_registry = sys.modules[
        "homeassistant.helpers.device_registry"
    ]
    sys.modules["homeassistant.helpers"].issue_registry = sys.modules[
        "homeassistant.helpers.issue_registry"
    ]
    _module("homeassistant.helpers.aiohttp_client", async_get_clientsession=None)
    _module(
        "homeassistant.helpers.event",
        async_call_later=None,
        async_track_time_interval=None,
    )
    _module("homeassistant.helpers.storage", Store=_Coordinator)
    _module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=_Coordinator,
        UpdateFailed=Exception,
    )
    util = _module("homeassistant.util", slugify=lambda v: str(v).lower())
    util.dt = _module("homeassistant.util.dt")
    _module("pyworxcloud", DeviceHandler=object, LandroidEvent=object, WorxCloud=object)
    _module(
        "pyworxcloud.exceptions",
        NoACSModuleError=Exception,
        NoConnectionError=NoConnectionError,
        NoCuttingHeightError=Exception,
        NoOfflimitsError=Exception,
        NoPartymodeError=Exception,
        TimeoutException=TimeoutException,
    )
    _module("pyworxcloud.utils")
    _module("pyworxcloud.utils.requests", AGET=None, HEADERS=None)


def _load_coordinator():
    _install_stubs()
    package = ModuleType(PACKAGE)
    package.__path__ = [str(SOURCE)]
    sys.modules[PACKAGE] = package
    for name in ("const", "helpers", "statistics", "coordinator"):
        spec = importlib.util.spec_from_file_location(
            f"{PACKAGE}.{name}", SOURCE / f"{name}.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"{PACKAGE}.{name}"] = module
        spec.loader.exec_module(module)
    return sys.modules[f"{PACKAGE}.coordinator"]


COORDINATOR = _load_coordinator()
HELPERS = sys.modules[f"{PACKAGE}.helpers"]
SERIAL = "SN-TEST"
ISSUE_ID = f"zone_mowing_not_acknowledged_{SERIAL}"


def _now_iso(offset_seconds: float = 0) -> str:
    moment = datetime.now(UTC) + timedelta(seconds=offset_seconds)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _device() -> SimpleNamespace:
    return SimpleNamespace(
        name="Test mower",
        raw_cfg={"rtk": {"zs": [{"id": 1}, {"id": 2}]}},
        raw_dat={"cut": {"tsk": []}},
    )


class FakeMower:
    """Plays one outcome per attempt: "ack", "lost" or "late".

    "late" is what was seen live: no answer in time, yet the mower created
    the task at once.
    """

    def __init__(self, device, outcomes: list[str]) -> None:
        self.device = device
        self.outcomes = outcomes
        self.sent: list[dict] = []

    async def publish(self, _uuid, _topic, message, _protocol) -> None:
        self.sent.append(message)
        outcome = self.outcomes[len(self.sent) - 1]
        if outcome in ("ack", "late"):
            self.device.raw_dat["cut"]["tsk"] = [
                {
                    "tm": _now_iso(),
                    "tr": 1,
                    "st": 0,
                    "z": [{"id": zone, "p": 0} for zone in message["cut"]["z"]],
                }
            ]
        if outcome != "ack":
            raise TimeoutException("Timed out waiting for device response")


def _coordinator(mower: FakeMower):
    coordinator = object.__new__(COORDINATOR.WorxVisionCoordinator)
    tasks: list[asyncio.Task] = []

    def _background(_hass, coro, _name):
        task = asyncio.get_running_loop().create_task(coro)
        tasks.append(task)
        return task

    coordinator.hass = None
    coordinator.data = {SERIAL: mower.device}
    coordinator.config_entry = SimpleNamespace(async_create_background_task=_background)
    coordinator.cloud = SimpleNamespace(
        get_mower=lambda _serial: {
            "online": True,
            "protocol": 1,
            "uuid": "uuid-1",
            "mqtt_topics": {"command_in": "topic/in"},
        }
    )
    coordinator._zone_job_retries = {}
    coordinator._mower_heard = {}
    coordinator.raise_if_updating = lambda _serial: None
    coordinator._async_publish_command = mower.publish

    async def _refresh(_serial):
        return None

    coordinator._async_request_device_update_best_effort = _refresh
    coordinator.tasks = tasks
    return coordinator


async def _settle(*tasks: asyncio.Task) -> None:
    """Wait for the retry tasks, failing fast instead of hanging a run."""
    await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 2)


async def _report(coordinator) -> bool:
    """Make the mower report in, if the retry is waiting for it."""
    for _ in range(5):
        await asyncio.sleep(0)
    heard = coordinator._mower_heard.get(SERIAL)
    if heard is None:
        return False
    heard.set()
    return True


class ZoneJobRetryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        ISSUES.clear()

    async def _start(self, outcomes: list[str], zones=(2,)):
        mower = FakeMower(_device(), outcomes)
        coordinator = _coordinator(mower)
        await coordinator.async_start_zone_mowing(SERIAL, list(zones), True, True)
        return mower, coordinator

    async def test_acknowledged_first_time_sends_once_and_clears_the_alert(self):
        ISSUES[ISSUE_ID] = {}
        mower, coordinator = await self._start(["ack"])
        self.assertEqual(len(mower.sent), 1)
        self.assertEqual(coordinator.tasks, [])
        self.assertNotIn(ISSUE_ID, ISSUES)

    async def test_late_answer_with_a_task_is_not_sent_again(self):
        ISSUES[ISSUE_ID] = {}
        mower, coordinator = await self._start(["late", "ack"])
        await _report(coordinator)
        await _settle(*coordinator.tasks)
        self.assertEqual(len(mower.sent), 1)
        self.assertNotIn(ISSUE_ID, ISSUES)
        self.assertEqual(coordinator._zone_job_retries, {})

    async def test_lost_job_is_sent_again_when_the_mower_reports_in(self):
        ISSUES[ISSUE_ID] = {}
        mower, coordinator = await self._start(["lost", "ack"])
        self.assertEqual(len(mower.sent), 1)
        self.assertTrue(await _report(coordinator))
        await _settle(*coordinator.tasks)
        self.assertEqual(len(mower.sent), 2)
        self.assertEqual(mower.sent[0], mower.sent[1])
        self.assertNotIn(ISSUE_ID, ISSUES)
        self.assertEqual(coordinator._zone_job_retries, {})
        self.assertEqual(coordinator._mower_heard, {})

    async def test_retry_answered_late_is_confirmed_by_the_next_report(self):
        mower, coordinator = await self._start(["lost", "late"])
        self.assertTrue(await _report(coordinator))
        await _settle(*coordinator.tasks)
        self.assertEqual(len(mower.sent), 2)
        self.assertNotIn(ISSUE_ID, ISSUES)

    async def test_lost_twice_raises_the_alert(self):
        mower, coordinator = await self._start(["lost", "lost"])
        await _report(coordinator)
        self.assertTrue(await _report(coordinator))
        await _settle(*coordinator.tasks)
        self.assertEqual(len(mower.sent), 2)
        self.assertIn(ISSUE_ID, ISSUES)
        self.assertEqual(
            ISSUES[ISSUE_ID]["translation_placeholders"]["mower_name"], "Test mower"
        )

    async def test_retry_is_sent_anyway_if_the_mower_stays_silent(self):
        original = COORDINATOR.ZONE_JOB_RETRY_WAIT
        COORDINATOR.ZONE_JOB_RETRY_WAIT = timedelta(seconds=0.01)
        try:
            mower, coordinator = await self._start(["lost", "ack"])
            await _settle(*coordinator.tasks)
        finally:
            COORDINATOR.ZONE_JOB_RETRY_WAIT = original
        self.assertEqual(len(mower.sent), 2)
        self.assertNotIn(ISSUE_ID, ISSUES)

    async def test_a_newer_job_cancels_the_pending_retry(self):
        mower, coordinator = await self._start(["lost", "ack"])
        pending = coordinator.tasks[0]
        await asyncio.sleep(0)
        await coordinator.async_start_zone_mowing(SERIAL, [1], False, True)
        await _settle(pending)
        self.assertTrue(pending.cancelled())
        self.assertEqual(len(mower.sent), 2)
        self.assertEqual(mower.sent[1]["cut"]["z"], [1])
        self.assertEqual(coordinator._zone_job_retries, {})

    async def test_a_pushed_update_wakes_the_waiting_retry_after_merging(self):
        coordinator = object.__new__(COORDINATOR.WorxVisionCoordinator)
        heard = asyncio.Event()
        merged: list[str] = []
        coordinator._mower_heard = {SERIAL: heard}
        coordinator._event_lock = asyncio.Lock()
        for name in (
            "_preserve_enriched_attributes",
            "_remember_rtk_map_id",
            "_remember_rtk_position",
            "_update_daily_statistics",
            "_sync_repair_issues",
            "_note_connectivity",
            "_note_state_durations",
            "_note_current_zone",
        ):
            setattr(coordinator, name, lambda *_args: None)
        coordinator.async_set_updated_data = lambda data: merged.extend(
            [] if heard.is_set() else list(data)
        )
        coordinator.data = {}
        await coordinator._handle_push_update(SimpleNamespace(serial_number=SERIAL))
        self.assertTrue(heard.is_set())
        self.assertEqual(merged, [SERIAL])


class ZoneJobTaskStartedTests(unittest.TestCase):
    COMMAND = {"cmd": 1, "cut": {"b": 0, "z": [1, 2], "zo": 0}}

    def _started(self, task: dict, sent_offset: float = 0) -> bool:
        device = SimpleNamespace(raw_dat={"cut": {"tsk": [task]}})
        sent_at = datetime.now(UTC) + timedelta(seconds=sent_offset)
        return HELPERS.zone_job_task_started(device, self.COMMAND, sent_at)

    def test_manual_task_after_the_command_on_requested_zones(self):
        self.assertTrue(self._started({"tm": _now_iso(2), "tr": 1, "z": [{"id": 1}]}))

    def test_mower_clock_slightly_behind_is_tolerated(self):
        self.assertTrue(self._started({"tm": _now_iso(-30), "tr": 1, "z": [{"id": 2}]}))

    def test_task_from_before_the_command_does_not_count(self):
        self.assertFalse(self._started({"tm": _now_iso(-300), "tr": 1, "z": [{"id": 1}]}))

    def test_scheduled_task_does_not_count(self):
        self.assertFalse(self._started({"tm": _now_iso(2), "tr": 2, "z": [{"id": 1}]}))

    def test_task_on_other_zones_does_not_count(self):
        self.assertFalse(self._started({"tm": _now_iso(2), "tr": 1, "z": [{"id": 3}]}))

    def test_task_without_zones_does_not_count(self):
        self.assertFalse(self._started({"tm": _now_iso(2), "tr": 1, "z": []}))

    def test_missing_or_bad_task_list(self):
        sent_at = datetime.now(UTC)
        for raw_dat in ({}, {"cut": {"tsk": None}}, {"cut": {"tsk": [{"tm": "x", "tr": 1}]}}):
            device = SimpleNamespace(raw_dat=raw_dat)
            self.assertFalse(HELPERS.zone_job_task_started(device, self.COMMAND, sent_at))


if __name__ == "__main__":
    unittest.main()
