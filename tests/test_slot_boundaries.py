"""Tests for the border cut of weekly slots, kept from the mower's own pushes.

The mower publishes each slot's border cut (`cfg.cut.b`) in the messages it
sends on its own. Its answer to a status request or a command, sent every 5
minutes, has it off on every slot, and so has the Worx cloud's copy: the
schedule lost the border cut a few minutes after each push.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from test_zone_job_retry import COORDINATOR, HELPERS  # noqa: E402

SERIAL = "SN-TEST"


def _raw_slot(day: int, start: int, boundary: int | None) -> dict:
    cut = {"z": [1, 2]}
    if boundary is not None:
        cut["b"] = boundary
    return {"d": day, "s": start, "t": 240, "cfg": {"cut": cut}}


def _cfg(*boundaries: int | None) -> dict:
    # Monday (1) 08:05 and 14:00, Wednesday (3) 08:05.
    slots = [(1, 485), (1, 840), (3, 485)]
    return {"sc": {"slots": [_raw_slot(d, s, b) for (d, s), b in zip(slots, boundaries)]}}


def _parsed(boundary: bool) -> list[dict]:
    return [
        {"day": "monday", "start": "08:05", "boundary": boundary},
        {"day": "monday", "start": "14:00", "boundary": boundary},
        {"day": "wednesday", "start": "08:05", "boundary": boundary},
    ]


class FakeStore:
    def __init__(self) -> None:
        self.saves = 0

    def async_delay_save(self, data_func, _delay) -> None:
        self.saves += 1
        data_func()


def _coordinator():
    coordinator = object.__new__(COORDINATOR.WorxVisionCoordinator)
    coordinator._slot_boundaries = {}
    coordinator._replies_expected = {}
    coordinator._slot_boundary_store = FakeStore()
    return coordinator


def _device(cfg: dict | None, parsed_boundary: bool = False, *, with_message: bool = True) -> SimpleNamespace:
    """A device as pyworxcloud leaves it after a message: raw_data is that message."""
    device = SimpleNamespace(raw_cfg=cfg, schedules={"slots": _parsed(parsed_boundary)})
    if with_message:
        device.raw_data = {"dat": {"act": 1}} if cfg is None else {"cfg": cfg, "dat": {"act": 1}}
    return device


class RawBoundariesTest(unittest.TestCase):
    def test_keys_are_raw_day_and_start(self) -> None:
        self.assertEqual(
            HELPERS.raw_slot_boundaries(_cfg(0, 1, 1)),
            {"1:485": False, "1:840": True, "3:485": True},
        )

    def test_slots_without_the_flag_are_left_out(self) -> None:
        self.assertEqual(HELPERS.raw_slot_boundaries(_cfg(None, 1, None)), {"1:840": True})
        self.assertEqual(HELPERS.raw_slot_boundaries({}), {})
        self.assertEqual(HELPERS.raw_slot_boundaries(None), {})


class ScheduleSlotsTest(unittest.TestCase):
    def test_pushed_boundaries_win_over_the_parsed_ones(self) -> None:
        device = _device(_cfg(0, 0, 0), parsed_boundary=False)
        device._worx_vision_slot_boundaries = {"1:840": True, "3:485": True}
        self.assertEqual(
            [s["boundary"] for s in HELPERS.schedule_slots(device)], [False, True, True]
        )
        # The parsed slots are left untouched.
        self.assertFalse(device.schedules["slots"][1]["boundary"])

    def test_without_pushed_boundaries_the_parsed_ones_stay(self) -> None:
        device = _device(_cfg(1, 1, 1), parsed_boundary=True)
        self.assertEqual([s["boundary"] for s in HELPERS.schedule_slots(device)], [True] * 3)


class CoordinatorTest(unittest.TestCase):
    def test_a_push_teaches_the_boundaries_and_a_refresh_keeps_them(self) -> None:
        coordinator = _coordinator()
        pushed = _device(_cfg(0, 1, 1))
        coordinator._note_pushed_schedule(SERIAL, pushed)
        self.assertEqual(coordinator._slot_boundaries[SERIAL], {"1:485": False, "1:840": True, "3:485": True})
        self.assertEqual([s["boundary"] for s in HELPERS.schedule_slots(pushed)], [False, True, True])

        # API refresh: pyworxcloud builds a new device from the cloud's copy.
        refreshed = _device(_cfg(0, 0, 0), with_message=False)
        coordinator._attach_slot_boundaries(SERIAL, refreshed)
        self.assertEqual([s["boundary"] for s in HELPERS.schedule_slots(refreshed)], [False, True, True])

    def test_the_answer_to_a_status_request_teaches_nothing(self) -> None:
        coordinator = _coordinator()
        coordinator._note_pushed_schedule(SERIAL, _device(_cfg(0, 1, 1)))

        coordinator._expect_reply(SERIAL)
        answer = _device(_cfg(0, 0, 0))
        coordinator._note_pushed_schedule(SERIAL, answer)
        self.assertEqual([s["boundary"] for s in HELPERS.schedule_slots(answer)], [False, True, True])
        self.assertEqual(coordinator._slot_boundary_store.saves, 1)

        # The next message the mower sends on its own is learnt again.
        coordinator._note_pushed_schedule(SERIAL, _device(_cfg(1, 1, 1)))
        self.assertEqual(coordinator._slot_boundaries[SERIAL]["1:485"], True)

    def test_each_request_is_answered_once(self) -> None:
        coordinator = _coordinator()
        coordinator._expect_reply(SERIAL)
        coordinator._expect_reply(SERIAL)
        coordinator._note_pushed_schedule(SERIAL, _device(_cfg(0, 0, 0)))
        coordinator._note_pushed_schedule(SERIAL, _device(_cfg(0, 0, 0)))
        self.assertNotIn(SERIAL, coordinator._slot_boundaries)
        coordinator._note_pushed_schedule(SERIAL, _device(_cfg(0, 1, 1)))
        self.assertEqual(coordinator._slot_boundaries[SERIAL]["1:840"], True)

    def test_an_answer_that_never_came_is_no_longer_awaited(self) -> None:
        coordinator = _coordinator()
        coordinator._expect_reply(SERIAL)
        count, sent = coordinator._replies_expected[SERIAL]
        coordinator._replies_expected[SERIAL] = (count, sent - COORDINATOR.MOWER_REPLY_WINDOW - 1)
        coordinator._note_pushed_schedule(SERIAL, _device(_cfg(0, 1, 1)))
        self.assertEqual(coordinator._slot_boundaries[SERIAL]["1:840"], True)

    def test_a_message_without_cfg_teaches_nothing(self) -> None:
        coordinator = _coordinator()
        # The device still holds the cloud's cfg, the message had only dat.
        device = _device(None)
        device.raw_cfg = _cfg(0, 0, 0)
        coordinator._note_pushed_schedule(SERIAL, device)
        self.assertNotIn(SERIAL, coordinator._slot_boundaries)

    def test_a_message_without_cfg_does_not_use_up_an_answer(self) -> None:
        coordinator = _coordinator()
        coordinator._expect_reply(SERIAL)
        coordinator._note_pushed_schedule(SERIAL, _device(None))
        coordinator._note_pushed_schedule(SERIAL, _device(_cfg(0, 0, 0)))
        self.assertNotIn(SERIAL, coordinator._slot_boundaries)

    def test_an_edit_in_the_app_replaces_the_boundaries(self) -> None:
        coordinator = _coordinator()
        coordinator._note_pushed_schedule(SERIAL, _device(_cfg(1, 1, 1)))
        coordinator._note_pushed_schedule(SERIAL, _device(_cfg(0, 1, 1)))
        self.assertEqual(coordinator._slot_boundaries[SERIAL]["1:485"], False)
        self.assertEqual(coordinator._slot_boundary_store.saves, 2)

    def test_a_json_message_is_read_too(self) -> None:
        coordinator = _coordinator()
        device = _device(_cfg(0, 1, 1))
        device.raw_data = json.dumps(device.raw_data)
        coordinator._note_pushed_schedule(SERIAL, device)
        self.assertEqual(coordinator._slot_boundaries[SERIAL]["3:485"], True)


if __name__ == "__main__":
    unittest.main()
