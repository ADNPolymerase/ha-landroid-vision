"""Coordinator for Worx Vision Cloud Plus."""
from __future__ import annotations

import asyncio
from collections import deque
from datetime import UTC, datetime, time, timedelta
import json
import logging
from urllib.parse import quote
from typing import Any, Callable

from aiohttp import ClientError, ClientTimeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from pyworxcloud import DeviceHandler, LandroidEvent, WorxCloud
from pyworxcloud.exceptions import (
    NoACSModuleError,
    NoConnectionError,
    NoCuttingHeightError,
    NoOfflimitsError,
    NoPartymodeError,
    TimeoutException,
)
from pyworxcloud.utils.requests import AGET, HEADERS

from .const import (
    BORDER_DISTANCE_OPTIONS_MM,
    CONF_BATTERY_SERVICE_CYCLES,
    CONF_BLADE_SERVICE_HOURS,
    CONF_DISCONNECT_GRACE,
    DEFAULT_BATTERY_SERVICE_CYCLES,
    DEFAULT_BLADE_SERVICE_HOURS,
    DEFAULT_DISCONNECT_GRACE,
    DOMAIN,
)
from .helpers import (
    DOCKED_STATUS_IDS,
    MOWING_STATUS_IDS,
    STARTING_STATUS_IDS,
    device_display_name,
    get_dict_value,
    masked_connectivity,
    rtk_map_id,
    rtk_position,
)
from .statistics import DailyStatisticsTracker

_LOGGER = logging.getLogger(__name__)

RTK_MAP_CACHE_TTL = timedelta(minutes=30)
RTK_ADDRESS_CACHE_TTL = timedelta(hours=24)
RTK_ADDRESS_COORD_PRECISION = 7
RTK_ADDRESS_ENDPOINT = "https://nominatim.openstreetmap.org/reverse"
RTK_ADDRESS_USER_AGENT = (
    "Worx Landroid Vision PLUS Home Assistant custom integration "
    "(https://github.com/ADNPolymerase/ha-landroid-vision)"
)
PRODUCT_ITEM_CACHE_TTL = timedelta(minutes=5)
LIVE_REFRESH_INTERVAL = timedelta(minutes=5)
FIRMWARE_UPGRADE_CACHE_TTL = timedelta(minutes=30)
STATISTICS_STORAGE_VERSION = 1
STATISTICS_SAVE_DELAY = 60
LOCAL_OPTIONS_STORAGE_VERSION = 1
RTK_TRAIL_STORAGE_VERSION = 1
RTK_TRAIL_SAVE_DELAY = 60
# A generous per-day safety cap, not a rolling window: the trail is reset at
# local midnight (see _remember_rtk_position), so this only guards against
# unbounded growth if positions ever streamed in absurdly often.
RTK_TRAIL_MAX_POINTS_PER_DAY = 4000
RTK_MAP_ID_STORAGE_VERSION = 1
STATE_DURATION_STORAGE_VERSION = 1
DEFAULT_ONE_TIME_MOWING_RUNTIME = 60
DEFAULT_ONE_TIME_MOWING_EDGE_CUT = False


def _device_map(cloud: WorxCloud) -> dict[str, DeviceHandler]:
    """Build a serial-number-indexed map of devices from pyworxcloud."""
    devices: dict[str, DeviceHandler] = {}
    for device in cloud.devices.values():
        serial = getattr(device, "serial_number", None)
        if serial is not None:
            devices[str(serial)] = device
    return devices


def _normalize_zone_ids(zones: list[int] | None) -> list[int]:
    """Return ordered, de-duplicated positive zone identifiers."""
    normalized: list[int] = []
    for zone in zones or []:
        zone_id = int(zone)
        if zone_id > 0 and zone_id not in normalized:
            normalized.append(zone_id)
    return normalized


class WorxVisionCoordinator(DataUpdateCoordinator[dict[str, DeviceHandler]]):
    """Coordinate push and manual updates."""

    def __init__(
        self, hass: HomeAssistant, cloud: WorxCloud, config_entry: ConfigEntry
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=None,
            # `_device_map()` returns the same DeviceHandler instances pyworxcloud
            # already holds, and `_enrich_device()` mutates them in place (e.g. the
            # product-item area_mowed figure). With always_update=False the
            # coordinator compares data by equality, which is always True here
            # (same object references), so it silently skips notifying entities
            # even when the mutated attributes actually changed.
            always_update=True,
        )
        self.cloud = cloud
        self._statistics_store = Store[dict[str, Any]](
            hass,
            STATISTICS_STORAGE_VERSION,
            f"{DOMAIN}.{config_entry.entry_id}.statistics",
        )
        self._statistics = DailyStatisticsTracker()
        self._statistics_save_pending = False
        self._shutdown_complete = False
        self._local_options_store = Store[dict[str, Any]](
            hass,
            LOCAL_OPTIONS_STORAGE_VERSION,
            f"{DOMAIN}.{config_entry.entry_id}.local_options",
        )
        self._local_options: dict[str, dict[str, Any]] = {}
        self._event_lock = asyncio.Lock()
        self._rtk_address_lock = asyncio.Lock()
        self._last_rtk_address_lookup: datetime | None = None
        self._rtk_map_cache: dict[str, tuple[datetime, dict[str, Any]]] = {}
        self._rtk_address_cache: dict[str, tuple[datetime, dict[str, Any]]] = {}
        self._product_item_cache: dict[str, tuple[datetime, dict[str, Any]]] = {}
        # Tracks when the product-item payload last actually CHANGED (not just
        # when it was re-fetched), so the "cloud statistics updated" sensor
        # only moves when the statistics move -- avoids recorder churn.
        self._product_item_changed_at: dict[str, datetime] = {}
        self._firmware_upgrade_cache: dict[
            str, tuple[datetime, dict[str, Any]]
        ] = {}
        self._rtk_position_trails: dict[
            str, deque[tuple[datetime, float, float]]
        ] = {}
        self._rtk_trail_day: dict[str, str] = {}
        self._rtk_trail_store = Store[dict[str, Any]](
            hass,
            RTK_TRAIL_STORAGE_VERSION,
            f"{DOMAIN}.{config_entry.entry_id}.rtk_trail",
        )
        self._rtk_trail_save_pending = False
        # Independent last-known-good cache, decoupled from pyworxcloud's
        # DeviceHandler (which it mutates in place, so it never holds a
        # true "previous" snapshot to preserve from - see
        # _remember_rtk_map_id). Persisted: a mower's map id is stable for
        # long stretches (it only changes if the boundary gets remapped in
        # the Worx app), so this is one short string per mower, not
        # something that grows over time.
        self._rtk_map_ids: dict[str, str] = {}
        self._rtk_map_id_store = Store[dict[str, str]](
            hass,
            RTK_MAP_ID_STORAGE_VERSION,
            f"{DOMAIN}.{config_entry.entry_id}.rtk_map_id",
        )
        self._one_time_mowing_options: dict[str, dict[str, Any]] = {}
        self._unsub_periodic_refresh: Callable[[], None] | None = None
        # First observed moment of an ongoing disconnection, per
        # (serial_number, kind) with kind in ("online", "mqtt"). Used to hide
        # short drops from the connectivity binary sensors (see
        # masked_connectivity); in-memory only, so after an HA restart an
        # already-offline mower gets one fresh grace period before showing
        # as disconnected.
        self._disconnected_since: dict[tuple[str, str], datetime] = {}
        # Start of the mower's current docked / error stretch, per mower.
        # Both reset the moment the mower leaves that state, so these are
        # "how long has it been like this right now" timers, not totals.
        # In-memory only: they restart from zero after a Home Assistant
        # restart, like the connectivity timestamps above.
        self._docked_since: dict[str, datetime] = {}
        self._error_since: dict[str, datetime] = {}
        self._state_duration_store = Store[dict[str, Any]](
            hass,
            STATE_DURATION_STORAGE_VERSION,
            f"{DOMAIN}.{config_entry.entry_id}.state_durations",
        )
        self._connectivity_recheck_unsubs: dict[
            tuple[str, str], Callable[[], None]
        ] = {}

    async def async_setup(self) -> None:
        """Attach pyworxcloud callbacks."""
        self._statistics = DailyStatisticsTracker(
            await self._statistics_store.async_load()
        )
        stored_options = await self._local_options_store.async_load()
        if isinstance(stored_options, dict):
            self._local_options = {
                str(serial): dict(options)
                for serial, options in stored_options.items()
                if isinstance(options, dict)
            }

        await self._load_rtk_trail()

        stored_map_ids = await self._rtk_map_id_store.async_load()
        if isinstance(stored_map_ids, dict):
            self._rtk_map_ids = {
                str(serial): str(value)
                for serial, value in stored_map_ids.items()
                if value
            }

        await self._load_state_durations()

        def _on_data_received(name: str, device: DeviceHandler) -> None:
            del name
            self._schedule_push_update(device)

        def _on_api_update(api_data: dict[str, Any], **_: Any) -> None:
            del api_data
            self._schedule_api_refresh()

        def _on_mqtt_connection(state: bool, **_: Any) -> None:
            # Without this event, a connect/disconnect only reaches the
            # connectivity sensors on the next data push or 5-minute refresh:
            # the disconnection timestamp behind the grace period starts late
            # and a reconnection can show as disconnected for minutes.
            del state
            self._schedule_connectivity_refresh()

        self.cloud.set_callback(LandroidEvent.DATA_RECEIVED, _on_data_received)
        self.cloud.set_callback(LandroidEvent.API, _on_api_update)
        self.cloud.set_callback(LandroidEvent.MQTT_CONNECTION, _on_mqtt_connection)

        self._unsub_periodic_refresh = async_track_time_interval(
            self.hass, self._async_periodic_device_refresh, LIVE_REFRESH_INTERVAL
        )

    async def async_shutdown(self) -> None:
        """Detach callbacks and persist statistics."""
        if self._shutdown_complete:
            return
        self._shutdown_complete = True
        self.cloud.set_callback(LandroidEvent.DATA_RECEIVED, lambda **_: None)
        self.cloud.set_callback(LandroidEvent.API, lambda **_: None)
        self.cloud.set_callback(LandroidEvent.MQTT_CONNECTION, lambda **_: None)
        if self._unsub_periodic_refresh is not None:
            self._unsub_periodic_refresh()
            self._unsub_periodic_refresh = None
        for unsub in self._connectivity_recheck_unsubs.values():
            unsub()
        self._connectivity_recheck_unsubs.clear()
        self._statistics_save_pending = False
        self._rtk_trail_save_pending = False
        try:
            await self._statistics_store.async_save(self._statistics.as_dict())
            await self._rtk_trail_store.async_save(self._rtk_trail_store_data())
            await self._rtk_map_id_store.async_save(dict(self._rtk_map_ids))
            await self._state_duration_store.async_save(
                self._state_duration_data()
            )
        finally:
            await super().async_shutdown()

    async def _async_periodic_device_refresh(self, _now: datetime) -> None:
        """Ask each mower for a fresh update on a fixed cadence.

        Some pyworxcloud data (e.g. work-time statistics used by the daily
        progress/area sensors) is only included in the mower's MQTT payload
        when it responds to an explicit update request, not on every routine
        push. Relying solely on push events or the sporadic LandroidEvent.API
        callback can leave those figures stale for hours during active
        mowing, so ask every known device to report in on this interval.
        """
        for serial_number in list((self.data or {}).keys()):
            # A mower disabled in the device registry (e.g. an old mower
            # still registered on the Worx cloud account) would time out on
            # every ping and flood the log: its entities are disabled, so
            # nothing consumes the refresh anyway. Checked live each pass,
            # so re-enabling the device resumes refreshes within a cycle.
            if self._is_registry_disabled(serial_number):
                _LOGGER.debug(
                    "Skipping periodic refresh for disabled device %s",
                    serial_number,
                )
                continue
            try:
                await self.async_request_device_update(serial_number)
            except Exception:  # noqa: BLE001
                _LOGGER.debug(
                    "Periodic refresh failed for device %s",
                    serial_number,
                    exc_info=True,
                )

    def _is_registry_disabled(self, serial_number: str) -> bool:
        """Return whether the mower's device registry entry is disabled."""
        device_entry = dr.async_get(self.hass).async_get_device(
            identifiers={(DOMAIN, serial_number)}
        )
        return device_entry is not None and bool(device_entry.disabled)

    def _disconnect_grace_minutes(self) -> int:
        """Return the configured connectivity grace period in minutes."""
        try:
            return int(
                self.config_entry.options.get(
                    CONF_DISCONNECT_GRACE, DEFAULT_DISCONNECT_GRACE
                )
            )
        except (TypeError, ValueError):
            return DEFAULT_DISCONNECT_GRACE

    def blade_service_threshold_minutes(self) -> int:
        """Return the configured blade service threshold in minutes."""
        try:
            hours = float(
                self.config_entry.options.get(
                    CONF_BLADE_SERVICE_HOURS, DEFAULT_BLADE_SERVICE_HOURS
                )
            )
        except (TypeError, ValueError):
            hours = DEFAULT_BLADE_SERVICE_HOURS
        return max(60, round(hours * 60))

    def battery_service_threshold_cycles(self) -> int:
        """Return the configured battery service threshold in charge cycles."""
        try:
            return max(
                50,
                int(
                    self.config_entry.options.get(
                        CONF_BATTERY_SERVICE_CYCLES, DEFAULT_BATTERY_SERVICE_CYCLES
                    )
                ),
            )
        except (TypeError, ValueError):
            return DEFAULT_BATTERY_SERVICE_CYCLES

    @staticmethod
    def _live_connectivity(device: DeviceHandler, kind: str) -> bool | None:
        """Return the raw connectivity flag for one kind ("online"/"mqtt")."""
        if kind == "mqtt":
            raw = getattr(device, "mqtt_connected", None)
            return None if raw is None else bool(raw)
        return bool(getattr(device, "online", False))

    def _note_connectivity(self, serial_number: str, device: DeviceHandler) -> None:
        """Track when a disconnection started, per connectivity kind."""
        now = datetime.now(UTC)
        for kind in ("online", "mqtt"):
            key = (serial_number, kind)
            if self._live_connectivity(device, kind) is False:
                self._disconnected_since.setdefault(key, now)
                self._schedule_connectivity_recheck(key)
            else:
                self._disconnected_since.pop(key, None)
                unsub = self._connectivity_recheck_unsubs.pop(key, None)
                if unsub is not None:
                    unsub()

    @staticmethod
    def _is_docked(device: DeviceHandler) -> bool:
        """Return whether the mower currently sits on its base."""
        status = getattr(device, "status", None)
        status_id = get_dict_value(status, "id") if isinstance(status, dict) else None
        return status_id in DOCKED_STATUS_IDS

    @staticmethod
    def _is_in_error(device: DeviceHandler) -> bool:
        """Return whether the mower reports a real error.

        Rain delay is surfaced as an error by some models but is a normal
        waiting state, not a fault, so it does not count here.
        """
        error = getattr(device, "error", None)
        if not isinstance(error, dict):
            return False
        error_id = get_dict_value(error, "id")
        if error_id in (None, 0, -1):
            return False
        description = str(get_dict_value(error, "description") or "").strip().lower()
        return description.replace("_", " ") != "rain delay"

    def _note_state_durations(self, serial_number: str, device: DeviceHandler) -> None:
        """Track when the current docked / error stretch started."""
        now = datetime.now(UTC)
        changed = False
        for tracker, active in (
            (self._docked_since, self._is_docked(device)),
            (self._error_since, self._is_in_error(device)),
        ):
            if active:
                if serial_number not in tracker:
                    tracker[serial_number] = now
                    changed = True
            elif tracker.pop(serial_number, None) is not None:
                changed = True

        if changed:
            # Only written when a stretch actually starts or ends, so this
            # stays a rare fire-and-forget write rather than a per-update one.
            self.hass.async_create_task(
                self._state_duration_store.async_save(self._state_duration_data())
            )

    def _state_duration_data(self) -> dict[str, Any]:
        """Return the state timers in a JSON-serializable shape."""
        return {
            "docked_since": {
                serial: value.isoformat()
                for serial, value in self._docked_since.items()
            },
            "error_since": {
                serial: value.isoformat()
                for serial, value in self._error_since.items()
            },
        }

    async def _load_state_durations(self) -> None:
        """Restore the docked / error timers from storage.

        A Home Assistant restart is not a mower state change, so the timers
        should survive it instead of restarting from zero. The restored
        timestamps are only kept for mowers still in that state: the first
        refresh runs _note_state_durations, which drops any entry whose state
        no longer holds. If the mower left and came back while Home Assistant
        was down we cannot tell, which is the known trade-off of trusting the
        stored start.
        """
        stored = await self._state_duration_store.async_load()
        if not isinstance(stored, dict):
            return

        for key, tracker in (
            ("docked_since", self._docked_since),
            ("error_since", self._error_since),
        ):
            entries = stored.get(key)
            if not isinstance(entries, dict):
                continue
            for serial, value in entries.items():
                try:
                    tracker[str(serial)] = datetime.fromisoformat(str(value))
                except (TypeError, ValueError):
                    continue

    def docked_minutes(self, serial_number: str) -> float:
        """Return minutes spent on the base in the current stretch."""
        since = self._docked_since.get(serial_number)
        if since is None:
            return 0.0
        return round((datetime.now(UTC) - since).total_seconds() / 60, 2)

    def error_minutes(self, serial_number: str) -> float:
        """Return minutes spent in the current error state."""
        since = self._error_since.get(serial_number)
        if since is None:
            return 0.0
        return round((datetime.now(UTC) - since).total_seconds() / 60, 2)

    def state_duration_details(self, serial_number: str) -> dict[str, Any]:
        """Return diagnostics for the computed state timers."""
        docked = self._docked_since.get(serial_number)
        errored = self._error_since.get(serial_number)
        return {
            "docked_since": docked.isoformat() if docked else None,
            "error_since": errored.isoformat() if errored else None,
        }

    def _schedule_connectivity_recheck(self, key: tuple[str, str]) -> None:
        """Re-render entities right when an ongoing drop outlives the grace.

        Without this the masked sensor would only flip on the next push or
        periodic refresh, up to several minutes after the grace expired.
        """
        grace = self._disconnect_grace_minutes()
        since = self._disconnected_since.get(key)
        if grace <= 0 or since is None or key in self._connectivity_recheck_unsubs:
            return

        remaining = grace * 60 - (datetime.now(UTC) - since).total_seconds()
        if remaining <= 0:
            return

        # @callback is required: async_call_later runs undecorated sync
        # callables in the executor thread pool, and async_set_updated_data
        # must run in the event loop (issue #2).
        @callback
        def _recheck(_now: datetime) -> None:
            self._connectivity_recheck_unsubs.pop(key, None)
            self.async_set_updated_data(self.data or {})

        self._connectivity_recheck_unsubs[key] = async_call_later(
            self.hass, remaining + 1, _recheck
        )

    def reported_connectivity(self, serial_number: str, kind: str) -> bool | None:
        """Return the connectivity state to expose, hiding short drops."""
        device = (self.data or {}).get(serial_number)
        if device is None:
            return None
        return masked_connectivity(
            self._live_connectivity(device, kind),
            self._disconnected_since.get((serial_number, kind)),
            self._disconnect_grace_minutes(),
            datetime.now(UTC),
        )

    def connectivity_attributes(self, serial_number: str, kind: str) -> dict[str, Any]:
        """Return live-state attributes backing a masked connectivity sensor."""
        device = (self.data or {}).get(serial_number)
        since = self._disconnected_since.get((serial_number, kind))
        return {
            "live_connected": (
                None if device is None else self._live_connectivity(device, kind)
            ),
            "disconnected_since": None if since is None else since.isoformat(),
            "grace_minutes": self._disconnect_grace_minutes(),
        }

    async def _handle_push_update(self, device: DeviceHandler) -> None:
        """Merge one pushed device update."""
        serial = getattr(device, "serial_number", None)
        if serial is None:
            return

        async with self._event_lock:
            self._preserve_enriched_attributes(str(serial), device)
            self._remember_rtk_map_id(str(serial), device)
            self._remember_rtk_position(str(serial), device)
            self._update_daily_statistics(str(serial), device)
            self._sync_repair_issues(str(serial), device)
            self._note_connectivity(str(serial), device)
            self._note_state_durations(str(serial), device)
            data = dict(self.data or {})
            data[str(serial)] = device
            self.async_set_updated_data(data)

    async def _refresh_from_cloud_cache(self) -> dict[str, DeviceHandler]:
        """Return current cloud cache."""
        devices = _device_map(self.cloud)
        results = await asyncio.gather(
            *(self._enrich_device(serial, device) for serial, device in devices.items()),
            return_exceptions=True,
        )
        for serial, result in zip(devices, results):
            if isinstance(result, Exception):
                _LOGGER.warning(
                    "Failed to enrich device %s with REST API data (area mowed, "
                    "firmware, RTK map may be stale): %s",
                    serial,
                    result,
                )
        return devices

    async def _async_update_data(self) -> dict[str, DeviceHandler]:
        """Return current cloud cache for DataUpdateCoordinator."""
        try:
            return await self._refresh_from_cloud_cache()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err

    async def async_request_device_update(self, serial_number: str) -> None:
        """Ask one mower for a fresh MQTT state update, then refresh coordinator data."""
        try:
            await self.cloud.update(serial_number)
        finally:
            await self.async_request_refresh()

    async def _async_ensure_mqtt_connected(self) -> None:
        """Reconnect MQTT before sending mower commands when the cloud session is stale."""
        if getattr(self.cloud, "mqtt_connected", False):
            return

        _LOGGER.warning(
            "Worx MQTT connection is not ready; reconnecting before command"
        )
        await self.cloud.connect()
        if not getattr(self.cloud, "mqtt_connected", False):
            raise HomeAssistantError("Worx MQTT connection is not ready")

    async def _async_publish_command(
        self, serial_number: str, topic: str, message: dict[str, Any], protocol: int
    ) -> None:
        """Publish a mower command, reconnecting MQTT once if needed."""
        await self._async_ensure_mqtt_connected()
        mqtt = getattr(self.cloud, "mqtt", None)
        if mqtt is None:
            raise HomeAssistantError("Worx MQTT connection is not available")

        try:
            await mqtt.apublish(serial_number, topic, message, protocol)
        except NoConnectionError:
            _LOGGER.warning(
                "Worx MQTT command failed because connection was stale; retrying once"
            )
            await self.cloud.connect()
            mqtt = getattr(self.cloud, "mqtt", None)
            if mqtt is None:
                raise HomeAssistantError("Worx MQTT connection is not available")
            await mqtt.apublish(serial_number, topic, message, protocol)

    async def _async_request_device_update_best_effort(
        self, serial_number: str
    ) -> None:
        """Refresh device state after a command without failing an accepted command."""
        try:
            await asyncio.wait_for(
                self.async_request_device_update(serial_number), timeout=10
            )
        except (NoConnectionError, TimeoutException, TimeoutError) as err:
            _LOGGER.warning(
                "Worx command was sent, but state refresh did not finish: %s", err
            )
        except Exception:  # noqa: BLE001 - command already succeeded
            _LOGGER.debug(
                "Worx command was sent, but best-effort state refresh failed",
                exc_info=True,
            )

    async def async_start_edge_cut(self, serial_number: str) -> None:
        """Start an on-demand edge cutting task."""
        mower = self.cloud.get_mower(serial_number)
        if not mower.get("online"):
            raise HomeAssistantError(
                "The device is currently offline, no action was sent"
            )

        protocol = mower.get("protocol")
        command_topic = (mower.get("mqtt_topics") or {}).get("command_in")
        if command_topic is None:
            raise HomeAssistantError("Worx command topic is not available")

        # On Vision Cloud firmware 3.46.x cmd 101 is the reliable edge-only
        # command. Full one-time mowing uses cmd 10 instead.
        if protocol == 0:
            await self._async_publish_command(
                serial_number,
                command_topic,
                {"sc": {"ots": {"bc": 1, "wtm": 0}}},
                protocol,
            )
        elif protocol == 1:
            await self.async_start_one_time_mowing(serial_number, 0, True, [])
            return
        else:
            raise HomeAssistantError(
                "Edge cutting is not supported for this mower protocol"
            )

        await self._async_request_device_update_best_effort(serial_number)

    async def async_start_one_time_mowing(
        self,
        serial_number: str,
        runtime_minutes: int,
        edge_cut: bool = False,
        zones: list[int] | None = None,
    ) -> None:
        """Start a one-time mowing task, optionally limited to RTK zones."""
        mower = self.cloud.get_mower(serial_number)
        if not mower.get("online"):
            raise HomeAssistantError(
                "The device is currently offline, no action was sent"
            )

        protocol = mower.get("protocol")
        runtime = int(runtime_minutes)
        zone_ids = _normalize_zone_ids(zones)
        if protocol == 0:
            command_topic = (mower.get("mqtt_topics") or {}).get("command_in")
            if command_topic is None:
                raise HomeAssistantError("Worx command topic is not available")

            if len(zone_ids) > 1:
                raise HomeAssistantError(
                    "Legacy Worx protocol supports only one selected zone per one-time mowing command"
                )

            setzone = getattr(self.cloud, "setzone", None)
            if zone_ids and setzone is not None:
                await setzone(serial_number, zone_ids[0])

            await self._async_publish_command(
                serial_number,
                command_topic,
                {"sc": {"ots": {"bc": int(edge_cut), "wtm": runtime}}},
                protocol,
            )
        elif protocol == 1:
            command_topic = (mower.get("mqtt_topics") or {}).get("command_in")
            if command_topic is None:
                raise HomeAssistantError("Worx command topic is not available")

            uuid = mower.get("uuid")
            if uuid is None:
                raise HomeAssistantError("Worx mower UUID is not available")

            if edge_cut and runtime == 0 and not zone_ids:
                await self._async_publish_command(
                    uuid, command_topic, {"cmd": 101}, protocol
                )
            else:
                await self._async_publish_command(
                    uuid,
                    command_topic,
                    {
                        "cmd": 10,
                        "sc": {
                            "once": {
                                "time": runtime,
                                "cfg": {"cut": {"b": int(edge_cut), "z": zone_ids}},
                            }
                        },
                    },
                    protocol,
                )
        else:
            raise HomeAssistantError(
                "One-time mowing is not supported for this mower protocol"
            )

        await self._async_request_device_update_best_effort(serial_number)

    def _one_time_options(self, serial_number: str) -> dict[str, Any]:
        """Return local one-time mowing options for a mower."""
        return self._one_time_mowing_options.setdefault(
            serial_number,
            {
                "runtime": DEFAULT_ONE_TIME_MOWING_RUNTIME,
                "edge_cut": DEFAULT_ONE_TIME_MOWING_EDGE_CUT,
                "zones": [],
            },
        )

    def one_time_mowing_runtime(self, serial_number: str) -> int:
        """Return configured one-time mowing runtime."""
        return int(
            self._one_time_options(serial_number).get(
                "runtime", DEFAULT_ONE_TIME_MOWING_RUNTIME
            )
        )

    def one_time_mowing_edge_cut(self, serial_number: str) -> bool:
        """Return whether configured one-time mowing starts with edge cutting."""
        return bool(
            self._one_time_options(serial_number).get(
                "edge_cut", DEFAULT_ONE_TIME_MOWING_EDGE_CUT
            )
        )

    def one_time_mowing_zones(self, serial_number: str) -> list[int]:
        """Return configured one-time mowing RTK zones."""
        return list(self._one_time_options(serial_number).get("zones", []))

    async def async_set_one_time_mowing_runtime(
        self, serial_number: str, runtime_minutes: int
    ) -> None:
        """Set local one-time mowing runtime."""
        runtime = max(10, min(120, int(runtime_minutes)))
        self._one_time_options(serial_number)["runtime"] = runtime
        self.async_set_updated_data(self.data or {})

    async def async_set_one_time_mowing_edge_cut(
        self, serial_number: str, enabled: bool
    ) -> None:
        """Set whether local one-time mowing starts with edge cutting."""
        self._one_time_options(serial_number)["edge_cut"] = bool(enabled)
        self.async_set_updated_data(self.data or {})

    async def async_set_one_time_mowing_zones(
        self, serial_number: str, zones: list[int]
    ) -> None:
        """Set local one-time mowing RTK zones."""
        self._one_time_options(serial_number)["zones"] = _normalize_zone_ids(zones)
        self.async_set_updated_data(self.data or {})

    async def async_start_configured_one_time_mowing(self, serial_number: str) -> None:
        """Start one-time mowing using local UI options."""
        await self.async_start_one_time_mowing(
            serial_number,
            self.one_time_mowing_runtime(serial_number),
            self.one_time_mowing_edge_cut(serial_number),
            self.one_time_mowing_zones(serial_number),
        )

    async def async_set_rain_delay(self, serial_number: str, minutes: int) -> None:
        """Set rain delay in minutes."""
        raindelay = getattr(self.cloud, "raindelay", None)
        if raindelay is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support rain delay updates"
            )

        await raindelay(serial_number, str(int(minutes)))
        self._update_cached_rain_delay(serial_number, int(minutes))
        await self.async_request_device_update(serial_number)

    async def async_set_time_extension(
        self, serial_number: str, time_extension: int
    ) -> None:
        """Set schedule time extension in percent."""
        set_time_extension = getattr(self.cloud, "set_time_extension", None)
        if set_time_extension is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support time extension updates"
            )

        await set_time_extension(serial_number, int(time_extension))
        await self.async_request_device_update(serial_number)

    async def async_set_lawn_size(self, serial_number: str, size_m2: int) -> None:
        """Set top-level lawn size in square meters."""
        set_lawn_size = getattr(self.cloud, "set_lawn_size", None)
        if set_lawn_size is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support lawn size updates"
            )

        await set_lawn_size(serial_number, int(size_m2))
        self._update_cached_product_item(serial_number, lawn_size=int(size_m2))
        await self.async_request_device_update(serial_number)

    async def async_set_lawn_perimeter(
        self, serial_number: str, perimeter_m: int
    ) -> None:
        """Set top-level lawn perimeter in meters."""
        set_lawn_perimeter = getattr(self.cloud, "set_lawn_perimeter", None)
        if set_lawn_perimeter is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support lawn perimeter updates"
            )

        await set_lawn_perimeter(serial_number, int(perimeter_m))
        self._update_cached_product_item(
            serial_number, lawn_perimeter=int(perimeter_m)
        )
        await self.async_request_device_update(serial_number)

    async def async_set_firmware_auto_upgrade(
        self, serial_number: str, enabled: bool
    ) -> None:
        """Toggle vendor firmware auto-upgrades."""
        set_firmware_auto_upgrade = getattr(
            self.cloud, "set_firmware_auto_upgrade", None
        )
        if set_firmware_auto_upgrade is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support firmware auto-upgrade"
            )

        await set_firmware_auto_upgrade(serial_number, enabled)
        self._update_cached_product_item(serial_number, firmware_auto_upgrade=enabled)
        await self.async_request_device_update(serial_number)

    async def async_set_lock(self, serial_number: str, enabled: bool) -> None:
        """Lock or unlock the mower."""
        set_lock = getattr(self.cloud, "set_lock", None)
        if set_lock is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support lock updates"
            )

        await set_lock(serial_number, state=enabled)
        self._update_cached_product_item(serial_number, locked=enabled)
        await self.async_request_device_update(serial_number)

    async def async_set_party_mode(self, serial_number: str, enabled: bool) -> None:
        """Turn party mode on or off."""
        set_party_mode = getattr(self.cloud, "set_party_mode", None)
        if set_party_mode is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support party mode"
            )

        try:
            await set_party_mode(serial_number, enabled)
        except NoPartymodeError as err:
            raise HomeAssistantError(
                "This mower does not support party mode"
            ) from err

        await self.async_request_device_update(serial_number)

    async def async_set_off_limits(self, serial_number: str, enabled: bool) -> None:
        """Turn the off-limits module on or off."""
        set_offlimits = getattr(self.cloud, "set_offlimits", None)
        if set_offlimits is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support off limits"
            )

        try:
            await set_offlimits(serial_number, enabled)
        except NoOfflimitsError as err:
            raise HomeAssistantError(
                "This mower does not support off limits"
            ) from err

        await self.async_request_device_update(serial_number)

    async def async_set_cutting_height(self, serial_number: str, height_mm: int) -> None:
        """Set the cutting height in millimeters."""
        set_cutting_height = getattr(self.cloud, "set_cutting_height", None)
        if set_cutting_height is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support cutting height"
            )

        try:
            await set_cutting_height(serial_number, int(height_mm))
        except NoCuttingHeightError as err:
            raise HomeAssistantError(
                "This mower does not support cutting height"
            ) from err

        await self.async_request_device_update(serial_number)

    async def async_set_acs(self, serial_number: str, enabled: bool) -> None:
        """Turn the ACS (Automatic Cutting System) module on or off."""
        set_acs = getattr(self.cloud, "set_acs", None)
        if set_acs is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support ACS"
            )

        try:
            await set_acs(serial_number, enabled)
        except NoACSModuleError as err:
            raise HomeAssistantError(
                "This mower does not have an ACS module installed"
            ) from err

        await self.async_request_device_update(serial_number)

    async def async_set_torque(self, serial_number: str, torque: int) -> None:
        """Set wheel torque percentage."""
        set_torque = getattr(self.cloud, "set_torque", None)
        if set_torque is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support torque updates"
            )

        await set_torque(serial_number, int(torque))
        await self.async_request_device_update(serial_number)

    def border_distance(self, serial_number: str) -> int | None:
        """Return the last border distance sent to the mower, if any.

        The Worx API accepts writing this setting but never reports it back,
        so the value is remembered locally (persisted across restarts) and
        unknown until set once through Home Assistant.
        """
        value = self._local_options.get(serial_number, {}).get("border_distance")
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    async def async_set_border_distance(
        self, serial_number: str, distance_mm: int
    ) -> None:
        """Set the Vision border cutting distance in millimeters."""
        set_border_distance = getattr(self.cloud, "set_border_distance", None)
        if set_border_distance is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support border distance"
            )
        distance = int(distance_mm)
        if distance not in BORDER_DISTANCE_OPTIONS_MM:
            raise HomeAssistantError(
                "Border distance must be one of "
                + ", ".join(f"{value} mm" for value in BORDER_DISTANCE_OPTIONS_MM)
            )

        await set_border_distance(serial_number, distance)
        self._local_options.setdefault(serial_number, {})[
            "border_distance"
        ] = distance
        await self._local_options_store.async_save(self._local_options)
        self._update_cached_border_distance(serial_number, distance)
        self.async_set_updated_data(self.data or {})

    async def async_restart_mower(self, serial_number: str) -> None:
        """Reboot the mower baseboard."""
        restart = getattr(self.cloud, "restart", None)
        if restart is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support restarting"
            )

        await restart(serial_number)
        await self.async_request_device_update(serial_number)

    async def async_toggle_schedule(self, serial_number: str, enabled: bool) -> None:
        """Enable or disable the mower's native schedule."""
        toggle_schedule = getattr(self.cloud, "toggle_schedule", None)
        if toggle_schedule is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support schedule toggling"
            )

        await toggle_schedule(serial_number, enable=enabled)
        await self.async_request_device_update(serial_number)

    async def async_start_firmware_upgrade(self, serial_number: str) -> None:
        """Queue the latest firmware update for a mower."""
        start_firmware_upgrade = getattr(self.cloud, "start_firmware_upgrade", None)
        if start_firmware_upgrade is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support firmware installs"
            )

        await start_firmware_upgrade(serial_number)
        await self.async_get_firmware_upgrade_info(serial_number, force=True)
        await self.async_request_device_update(serial_number)

    async def async_reset_charge_cycle_counter(self, serial_number: str) -> None:
        """Reset battery charge cycle counter after battery maintenance."""
        reset_charge_cycle_counter = getattr(
            self.cloud, "reset_charge_cycle_counter", None
        )
        if reset_charge_cycle_counter is None:
            raise HomeAssistantError(
                "The installed pyworxcloud version does not support battery cycle reset"
            )

        await reset_charge_cycle_counter(serial_number)
        await self.async_request_device_update(serial_number)

    async def async_set_cut_over_border(
        self, serial_number: str, enabled: bool
    ) -> None:
        """Persist whether Vision border cutting may cross the lawn border."""
        set_cut_over_border = getattr(self.cloud, "set_cut_over_border", None)
        if set_cut_over_border is not None:
            await set_cut_over_border(serial_number, enabled)
        else:
            await self._async_send_cut_over_border(serial_number, enabled)

        self._update_cached_cut_over_border(serial_number, enabled)
        await self.async_request_device_update(serial_number)

    async def _async_send_cut_over_border(
        self, serial_number: str, enabled: bool
    ) -> None:
        """Send the observed Vision Cloud border-cut payload for pyworxcloud 6.3.x."""
        mower = self.cloud.get_mower(serial_number)
        if mower.get("protocol") != 1:
            raise ValueError(
                "Intelligent edge cutting is only supported for protocol 1 devices"
            )

        payload = {
            "mz": {
                "s": [
                    {
                        "id": 1,
                        "c": 1,
                        "cfg": {"cut": {"ob": 1 if enabled else 0}},
                    }
                ],
                "p": [],
            }
        }
        await self.cloud.send(serial_number, json.dumps(payload))

    def _update_cached_cut_over_border(
        self, serial_number: str, enabled: bool
    ) -> None:
        """Update local cached raw config so the switch state changes immediately."""
        device = (self.data or {}).get(serial_number)
        if device is None:
            return

        raw_cfg = getattr(device, "raw_cfg", None)
        if isinstance(raw_cfg, dict):
            cut = raw_cfg.setdefault("cut", {})
            if isinstance(cut, dict):
                cut["ob"] = 1 if enabled else 0
            for zone_cut in self._raw_zone_cutting_dicts(raw_cfg):
                zone_cut["ob"] = 1 if enabled else 0

    def _update_cached_border_distance(
        self, serial_number: str, distance_mm: int
    ) -> None:
        """Update cached raw config so the border distance changes immediately."""
        device = (self.data or {}).get(serial_number)
        if device is None:
            return

        raw_cfg = getattr(device, "raw_cfg", None)
        if isinstance(raw_cfg, dict):
            cut = raw_cfg.setdefault("cut", {})
            if isinstance(cut, dict):
                cut["bd"] = distance_mm
                cut["co"] = distance_mm
            for zone_cut in self._raw_zone_cutting_dicts(raw_cfg):
                zone_cut["bd"] = distance_mm
                zone_cut["co"] = distance_mm

    @staticmethod
    def _raw_zone_cutting_dicts(raw_cfg: dict[str, Any]) -> list[dict[str, Any]]:
        """Return mutable zone cutting dictionaries from known protocol 1 paths."""
        result: list[dict[str, Any]] = []
        for zone_container in (("rtk", "zs"), ("mz", "s")):
            current: Any = raw_cfg
            for key in zone_container:
                if not isinstance(current, dict):
                    current = None
                    break
                current = current.get(key)
            if not isinstance(current, list | tuple):
                continue
            for zone in current:
                if not isinstance(zone, dict):
                    continue
                cfg = zone.setdefault("cfg", {})
                if not isinstance(cfg, dict):
                    continue
                cut = cfg.setdefault("cut", {})
                if isinstance(cut, dict):
                    result.append(cut)
        return result

    async def async_get_rtk_map(
        self, map_id: str | None, *, force: bool = False
    ) -> dict[str, Any] | None:
        """Fetch RTK map geometry from the private Worx maps endpoint."""
        if not map_id:
            return None

        now = datetime.now(UTC)
        cached = self._rtk_map_cache.get(map_id)
        if (
            cached is not None
            and not force
            and now - cached[0] < RTK_MAP_CACHE_TTL
        ):
            return cached[1]

        api = getattr(self.cloud, "_api", None)
        if api is None:
            _LOGGER.debug("Cannot fetch RTK map: pyworxcloud API object missing")
            return None

        try:
            await api.check_token()
            endpoint = getattr(getattr(api, "cloud", None), "ENDPOINT", None)
            if endpoint is None:
                endpoint = getattr(getattr(self.cloud, "_cloud", None), "ENDPOINT", None)
            if endpoint is None:
                _LOGGER.debug("Cannot fetch RTK map: Worx API endpoint missing")
                return None

            map_data = await AGET(
                f"https://{endpoint}/api/v2/maps/{quote(str(map_id), safe='')}",
                HEADERS(api.access_token),
                session=await api._ensure_session(),
            )
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not fetch RTK map %s", map_id, exc_info=True)
            return cached[1] if cached is not None else None

        if isinstance(map_data, dict):
            self._rtk_map_cache[map_id] = (now, map_data)
            return map_data

        return None

    async def async_get_product_item(
        self, serial_number: str | None, *, force: bool = False
    ) -> dict[str, Any] | None:
        """Fetch product item details from the private Worx endpoint."""
        if not serial_number:
            return None

        now = datetime.now(UTC)
        cached = self._product_item_cache.get(serial_number)
        if (
            cached is not None
            and not force
            and now - cached[0] < PRODUCT_ITEM_CACHE_TTL
        ):
            return cached[1]

        product_item = await self._api_get(f"/api/v2/product-items/{serial_number}")
        if isinstance(product_item, dict):
            if cached is None or cached[1] != product_item:
                self._product_item_changed_at[serial_number] = now
            self._product_item_cache[serial_number] = (now, product_item)
            return product_item

        return cached[1] if cached is not None else None

    async def async_get_firmware_upgrade_info(
        self, serial_number: str | None, *, force: bool = False
    ) -> dict[str, Any] | None:
        """Fetch firmware upgrade metadata from pyworxcloud/private API."""
        if not serial_number:
            return None

        now = datetime.now(UTC)
        cached = self._firmware_upgrade_cache.get(serial_number)
        if (
            cached is not None
            and not force
            and now - cached[0] < FIRMWARE_UPGRADE_CACHE_TTL
        ):
            return cached[1]

        firmware_info: dict[str, Any] | None = None
        get_firmware_upgrade_info = getattr(
            self.cloud, "get_firmware_upgrade_info", None
        )
        if get_firmware_upgrade_info is not None:
            try:
                value = await get_firmware_upgrade_info(serial_number)
                if isinstance(value, dict):
                    firmware_info = value
            except Exception:  # noqa: BLE001
                _LOGGER.debug(
                    "Could not fetch firmware upgrade info for %s",
                    serial_number,
                    exc_info=True,
                )

        if firmware_info is None:
            product_item = await self.async_get_product_item(serial_number)
            firmware_info = self._fallback_firmware_upgrade_info(product_item)

        if firmware_info is not None:
            self._firmware_upgrade_cache[serial_number] = (now, firmware_info)
            device = (self.data or {}).get(serial_number)
            if device is not None:
                setattr(device, "_worx_vision_firmware_upgrade", firmware_info)
            return firmware_info

        return cached[1] if cached is not None else None

    def product_item_data(self, serial_number: str) -> dict[str, Any] | None:
        """Return cached product item details."""
        cached = self._product_item_cache.get(serial_number)
        return None if cached is None else cached[1]

    def firmware_upgrade_data(self, serial_number: str) -> dict[str, Any] | None:
        """Return cached firmware upgrade details."""
        cached = self._firmware_upgrade_cache.get(serial_number)
        return None if cached is None else cached[1]

    def rtk_map_data(self, map_id: str | None) -> dict[str, Any] | None:
        """Return cached RTK map details."""
        if not map_id:
            return None
        cached = self._rtk_map_cache.get(map_id)
        return None if cached is None else cached[1]

    def rtk_position_trail(
        self, serial_number: str, max_points: int | None = None
    ) -> list[tuple[float, float]]:
        """Return the day's RTK positions for map rendering."""
        trail = self._rtk_position_trails.get(serial_number)
        if trail is None:
            return []
        points = list(trail)
        if max_points is not None:
            points = points[-max_points:]
        return [(lat, lon) for _, lat, lon in points]

    def rtk_position_timed_trail(
        self, serial_number: str, max_points: int | None = None
    ) -> list[tuple[datetime, float, float]]:
        """Return the day's RTK positions with timestamps for map rendering.

        Defaults to the whole day's trail: the deque is already reset at
        local midnight and capped per day, so slicing further here would
        turn the full-day trail back into a rolling window (the camera
        used to render only the last 120 points because of exactly that).
        """
        trail = self._rtk_position_trails.get(serial_number)
        if trail is None:
            return []
        points = list(trail)
        if max_points is not None:
            points = points[-max_points:]
        return points

    async def async_reverse_geocode_rtk_position(
        self, position: tuple[float, float] | None, *, force: bool = False
    ) -> dict[str, Any] | None:
        """Return a cached reverse-geocoded address for an RTK position."""
        if position is None:
            return None

        cache_key = self.rtk_address_cache_key(position)
        now = datetime.now(UTC)
        cached = self._rtk_address_cache.get(cache_key)
        if (
            cached is not None
            and not force
            and now - cached[0] < RTK_ADDRESS_CACHE_TTL
        ):
            return cached[1]

        async with self._rtk_address_lock:
            cached = self._rtk_address_cache.get(cache_key)
            if (
                cached is not None
                and not force
                and now - cached[0] < RTK_ADDRESS_CACHE_TTL
            ):
                return cached[1]

            lookup_latitude, lookup_longitude = self.rtk_address_lookup_position(position)
            await self._throttle_rtk_address_lookup()

            session = async_get_clientsession(self.hass)
            params = {
                "format": "jsonv2",
                "lat": f"{lookup_latitude:.{RTK_ADDRESS_COORD_PRECISION}f}",
                "lon": f"{lookup_longitude:.{RTK_ADDRESS_COORD_PRECISION}f}",
                "zoom": "18",
                "addressdetails": "1",
                "accept-language": self.hass.config.language or "en",
            }
            headers = {
                "User-Agent": RTK_ADDRESS_USER_AGENT,
                "Accept": "application/json",
            }

            try:
                async with session.get(
                    RTK_ADDRESS_ENDPOINT,
                    params=params,
                    headers=headers,
                    timeout=ClientTimeout(total=10),
                ) as response:
                    if response.status == 429 and cached is not None:
                        _LOGGER.debug(
                            "Nominatim rate-limited address lookup; using cache"
                        )
                        return cached[1]
                    response.raise_for_status()
                    address_data = await response.json()
            except (ClientError, TimeoutError, ValueError):
                _LOGGER.debug("Could not reverse-geocode RTK position", exc_info=True)
                return cached[1] if cached is not None else None

        if isinstance(address_data, dict):
            self._rtk_address_cache[cache_key] = (now, address_data)
            return address_data

        return cached[1] if cached is not None else None

    @staticmethod
    def rtk_address_cache_key(position: tuple[float, float]) -> str:
        """Return a privacy-friendlier cache key for RTK address lookups."""
        latitude, longitude = WorxVisionCoordinator.rtk_address_lookup_position(position)
        return (
            f"{latitude:.{RTK_ADDRESS_COORD_PRECISION}f},"
            f"{longitude:.{RTK_ADDRESS_COORD_PRECISION}f}"
        )

    @staticmethod
    def rtk_address_lookup_position(position: tuple[float, float]) -> tuple[float, float]:
        """Return rounded coordinates used for reverse-geocoding."""
        return (
            round(position[0], RTK_ADDRESS_COORD_PRECISION),
            round(position[1], RTK_ADDRESS_COORD_PRECISION),
        )

    async def _throttle_rtk_address_lookup(self) -> None:
        """Keep public reverse-geocoding requests below one request per second."""
        if self._last_rtk_address_lookup is not None:
            elapsed = datetime.now(UTC) - self._last_rtk_address_lookup
            remaining = 1 - elapsed.total_seconds()
            if remaining > 0:
                await asyncio.sleep(remaining)
        self._last_rtk_address_lookup = datetime.now(UTC)

    def _schedule_push_update(self, device: DeviceHandler) -> None:
        """Schedule a pushed device update on HA loop."""
        try:
            self.hass.loop.call_soon_threadsafe(self._create_push_update_task, device)
        except RuntimeError:
            _LOGGER.debug("Ignoring push update after HA loop shutdown")

    def _schedule_api_refresh(self) -> None:
        """Schedule API cache refresh on HA loop."""
        try:
            self.hass.loop.call_soon_threadsafe(self._create_api_refresh_task)
        except RuntimeError:
            _LOGGER.debug("Ignoring API update after HA loop shutdown")

    def _schedule_connectivity_refresh(self) -> None:
        """Schedule a connectivity re-render on the HA loop.

        Fired from pyworxcloud's MQTT thread, so it must hop onto the
        event loop before touching entity state (see issue #2).
        """
        try:
            self.hass.loop.call_soon_threadsafe(self._refresh_connectivity_state)
        except RuntimeError:
            _LOGGER.debug("Ignoring MQTT connection event after HA loop shutdown")

    @callback
    def _refresh_connectivity_state(self) -> None:
        """Re-evaluate connectivity for all mowers and re-render entities."""
        for serial_number, device in (self.data or {}).items():
            self._note_connectivity(serial_number, device)
            self._note_state_durations(serial_number, device)
        self.async_set_updated_data(self.data or {})

    def _create_push_update_task(self, device: DeviceHandler) -> None:
        """Create task for a pushed update."""
        self.hass.async_create_task(self._handle_push_update(device))

    def _create_api_refresh_task(self) -> None:
        """Create task for API cache refresh."""
        self.hass.async_create_task(self.async_request_refresh())

    async def _enrich_device(self, serial_number: str, device: DeviceHandler) -> None:
        """Attach private API details to the cached device object."""
        product_item = await self.async_get_product_item(serial_number)
        if product_item is not None:
            setattr(device, "_worx_vision_product_item", product_item)
            changed_at = self._product_item_changed_at.get(serial_number)
            if changed_at is not None:
                setattr(
                    device,
                    "_worx_vision_product_item_updated_at",
                    changed_at,
                )
            _LOGGER.debug(
                "Enriched device %s: area_mowed=%s",
                serial_number,
                product_item.get("area_mowed"),
            )
        else:
            _LOGGER.debug(
                "No product item data returned for device %s", serial_number
            )

        firmware_info = await self.async_get_firmware_upgrade_info(serial_number)
        if firmware_info is not None:
            setattr(device, "_worx_vision_firmware_upgrade", firmware_info)

        map_id = self._remember_rtk_map_id(serial_number, device)
        map_data = await self.async_get_rtk_map(map_id)
        if map_data is not None:
            setattr(device, "_worx_vision_rtk_map", map_data)

        self._remember_rtk_position(serial_number, device)
        self._update_daily_statistics(serial_number, device)
        self._sync_repair_issues(serial_number, device)
        self._note_connectivity(serial_number, device)
        self._note_state_durations(serial_number, device)

    async def _api_get(self, path: str) -> Any:
        """Fetch a private Worx API path using pyworxcloud's session/token."""
        api = getattr(self.cloud, "_api", None)
        if api is None:
            _LOGGER.debug("Cannot fetch Worx API path %s: API object missing", path)
            return None

        try:
            await api.check_token()
            endpoint = getattr(getattr(api, "cloud", None), "ENDPOINT", None)
            if endpoint is None:
                endpoint = getattr(getattr(self.cloud, "_cloud", None), "ENDPOINT", None)
            if endpoint is None:
                _LOGGER.debug("Cannot fetch Worx API path %s: endpoint missing", path)
                return None

            return await AGET(
                f"https://{endpoint}{path}",
                HEADERS(api.access_token),
                session=await api._ensure_session(),
            )
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not fetch Worx API path %s", path, exc_info=True)
            return None

    def _remember_rtk_map_id(
        self, serial_number: str, device: DeviceHandler
    ) -> str | None:
        """Return the RTK map id, caching the last known value independently.

        pyworxcloud reuses and mutates a single DeviceHandler instance per
        mower in place, so `raw_cfg` on that object is the SAME dict before
        and after a push: there is no "previous" snapshot to compare against
        once pyworxcloud has already overwritten it with a partial cfg that
        omits the rtk block. The only reliable fix is a cache that lives
        outside that object entirely, updated whenever a real value is seen
        and used as a fallback whenever it briefly isn't.

        Also persisted to storage (only when it actually changes, so this
        stays a fire-and-forget write, not something callers need to await)
        since a mower can sit docked for a while after a restart without
        Worx ever sending a payload containing the rtk block again, which
        would otherwise leave the camera without a map id to work with
        until the next mow.
        """
        live_value = rtk_map_id(device)
        if live_value is not None and self._rtk_map_ids.get(serial_number) != str(
            live_value
        ):
            self._rtk_map_ids[serial_number] = str(live_value)
            self.hass.async_create_task(
                self._rtk_map_id_store.async_save(dict(self._rtk_map_ids))
            )
        return self._rtk_map_ids.get(serial_number)

    @staticmethod
    def _fallback_firmware_upgrade_info(
        product_item: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Build basic firmware metadata when the OTA endpoint is unavailable."""
        if not isinstance(product_item, dict):
            return None

        current_version = product_item.get("firmware_version")
        capabilities = product_item.get("capabilities") or []
        ota_supported = (
            isinstance(capabilities, list | tuple) and "ota_upgrade" in capabilities
        )
        return {
            "current_version": current_version,
            "latest_version": current_version,
            "update_available": False,
            "ota_supported": ota_supported,
            "auto_upgrade": product_item.get("firmware_auto_upgrade"),
        }

    def _remember_rtk_position(
        self, serial_number: str, device: DeviceHandler
    ) -> None:
        """Keep the RTK trail for the current local day.

        Matches the Worx app, which keeps the full day's trail rather than a
        fixed rolling window: reset at local midnight instead of evicting by
        point count, and persisted so an HA restart mid-day doesn't lose it.
        """
        position = rtk_position(device)
        if position is None:
            return

        today = dt_util.now().date().isoformat()
        if self._rtk_trail_day.get(serial_number) != today:
            self._rtk_position_trails[serial_number] = deque(
                maxlen=RTK_TRAIL_MAX_POINTS_PER_DAY
            )
            self._rtk_trail_day[serial_number] = today

        latitude, longitude = position
        trail = self._rtk_position_trails.setdefault(
            serial_number, deque(maxlen=RTK_TRAIL_MAX_POINTS_PER_DAY)
        )
        if trail:
            _, previous_latitude, previous_longitude = trail[-1]
            if (
                round(previous_latitude, 7) == round(latitude, 7)
                and round(previous_longitude, 7) == round(longitude, 7)
            ):
                return

        trail.append((datetime.now(UTC), latitude, longitude))
        setattr(device, "_worx_vision_rtk_trail", list(trail))
        self._schedule_rtk_trail_save()

    def _schedule_rtk_trail_save(self) -> None:
        """Debounce persisting the RTK trail to storage."""
        if self._rtk_trail_save_pending:
            return
        self._rtk_trail_save_pending = True
        self._rtk_trail_store.async_delay_save(
            self._rtk_trail_store_data_and_clear_pending,
            RTK_TRAIL_SAVE_DELAY,
        )

    def _rtk_trail_store_data_and_clear_pending(self) -> dict[str, Any]:
        """Return current RTK trails and allow scheduling the next save."""
        self._rtk_trail_save_pending = False
        return self._rtk_trail_store_data()

    def _rtk_trail_store_data(self) -> dict[str, Any]:
        """Return the RTK trails in a JSON-serializable shape."""
        return {
            serial: {
                "day": self._rtk_trail_day.get(serial),
                "points": [
                    {"t": timestamp.isoformat(), "lat": latitude, "lon": longitude}
                    for timestamp, latitude, longitude in trail
                ],
            }
            for serial, trail in self._rtk_position_trails.items()
        }

    async def _load_rtk_trail(self) -> None:
        """Restore today's RTK trail from storage, if any."""
        stored = await self._rtk_trail_store.async_load()
        if not isinstance(stored, dict):
            return

        today = dt_util.now().date().isoformat()
        for serial, entry in stored.items():
            if not isinstance(entry, dict) or entry.get("day") != today:
                continue
            trail: deque[tuple[datetime, float, float]] = deque(
                maxlen=RTK_TRAIL_MAX_POINTS_PER_DAY
            )
            for point in entry.get("points") or []:
                try:
                    timestamp = datetime.fromisoformat(point["t"])
                    latitude = float(point["lat"])
                    longitude = float(point["lon"])
                except (KeyError, TypeError, ValueError):
                    continue
                trail.append((timestamp, latitude, longitude))
            if trail:
                self._rtk_position_trails[str(serial)] = trail
                self._rtk_trail_day[str(serial)] = today

    def _preserve_enriched_attributes(
        self, serial_number: str, device: DeviceHandler
    ) -> None:
        """Keep cached API enrichment on MQTT-only push updates."""
        previous = (self.data or {}).get(serial_number)
        if previous is None:
            return

        for attr in (
            "_worx_vision_product_item",
            "_worx_vision_product_item_updated_at",
            "_worx_vision_firmware_upgrade",
            "_worx_vision_rtk_map",
        ):
            if hasattr(device, attr) or not hasattr(previous, attr):
                continue
            setattr(device, attr, getattr(previous, attr))

    def rtk_map_id(self, serial_number: str) -> str | None:
        """Return the last known RTK map id for a mower.

        Backed by an independent cache (see _remember_rtk_map_id) rather
        than reading pyworxcloud's live device object directly, so a
        momentary partial cfg push that omits the rtk block doesn't make
        the map camera or dependent sensors flicker unavailable/unknown.
        """
        return self._rtk_map_ids.get(serial_number)

    async def async_set_rtk_map_id(self, serial_number: str, map_id: str) -> None:
        """Manually seed or correct the cached RTK map id for a mower.

        Worx doesn't always resend `cfg.rtk.map` promptly (observed live:
        it can go quiet for a long stretch even during active mowing with a
        good GPS fix, apparently tied to a server-side trigger this
        integration has no visibility into). When that happens, the map id
        can still be recovered from Home Assistant's own state history
        (this sensor's past values) and set here to unblock the map camera
        and lawn-area-dependent sensors immediately, without waiting for
        Worx's cloud to cooperate. Persisted the same way as a live value.
        """
        value = str(map_id).strip()
        if not value:
            raise HomeAssistantError("map_id must not be empty")
        self._rtk_map_ids[serial_number] = value
        await self._rtk_map_id_store.async_save(dict(self._rtk_map_ids))
        await self.async_request_refresh()

    def _update_daily_statistics(
        self, serial_number: str, device: DeviceHandler
    ) -> None:
        """Update persisted daily counters from one device snapshot."""
        product_item = getattr(device, "_worx_vision_product_item", {}) or {}
        status_id = get_dict_value(getattr(device, "status", {}) or {}, "id")
        try:
            mowing_active = (
                int(status_id) in MOWING_STATUS_IDS
                or int(status_id) in STARTING_STATUS_IDS
            )
        except (TypeError, ValueError):
            mowing_active = False

        now_utc = datetime.now(UTC)
        local_now = dt_util.as_local(now_utc)
        local_midnight_utc = datetime.combine(
            local_now.date(),
            time.min,
            tzinfo=local_now.tzinfo,
        ).astimezone(UTC)
        changed = self._statistics.update(
            serial_number,
            area_total=get_dict_value(product_item, "area_mowed"),
            mowing_active=mowing_active,
            now_utc=now_utc,
            local_day=local_now.date(),
            local_midnight_utc=local_midnight_utc,
        )
        if changed:
            if self._statistics_save_pending:
                return
            self._statistics_save_pending = True
            self._statistics_store.async_delay_save(
                self._statistics_store_data,
                STATISTICS_SAVE_DELAY,
            )

    def _statistics_store_data(self) -> dict[str, Any]:
        """Return current statistics and allow scheduling the next save."""
        self._statistics_save_pending = False
        return self._statistics.as_dict()

    def _counter_since_reset(
        self, product_item: dict[str, Any], total_key: str, reset_key: str
    ) -> int | None:
        """Return a cumulative counter minus its optional reset marker."""
        try:
            total = int(float(product_item.get(total_key)))
        except (TypeError, ValueError):
            return None
        try:
            reset = int(float(product_item.get(reset_key)))
        except (TypeError, ValueError):
            return total
        return max(0, total - reset)

    def _sync_repair_issues(
        self, serial_number: str, device: DeviceHandler
    ) -> None:
        """Raise or clear HA repair issues from maintenance counters.

        Mirrors the maintenance sensor's thresholds, so the sensor and the
        Repairs panel always agree on what needs attention.
        """
        product_item = getattr(device, "_worx_vision_product_item", {}) or {}
        if not product_item:
            return

        blade_threshold_minutes = self.blade_service_threshold_minutes()
        battery_threshold_cycles = self.battery_service_threshold_cycles()
        # Stash the configured thresholds on the device so the maintenance
        # sensor (whose value_fn only receives the device) uses the same
        # values as the Repairs panel.
        setattr(
            device,
            "_worx_vision_service_thresholds",
            {
                "blade_minutes": blade_threshold_minutes,
                "battery_cycles": battery_threshold_cycles,
            },
        )

        blade_issue_id = f"blade_service_due_{serial_number}"
        battery_issue_id = f"battery_service_due_{serial_number}"

        # No repairs for mowers the user disabled in the device registry
        # (e.g. an old mower still registered on the Worx account).
        if self._is_registry_disabled(serial_number):
            ir.async_delete_issue(self.hass, DOMAIN, blade_issue_id)
            ir.async_delete_issue(self.hass, DOMAIN, battery_issue_id)
            return

        mower_name = device_display_name(device)

        blade_minutes = self._counter_since_reset(
            product_item, "blade_work_time", "blade_work_time_reset"
        )
        blade_due = (
            blade_minutes is not None
            and blade_minutes >= blade_threshold_minutes
        )
        if blade_due:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                blade_issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="blade_service_due",
                translation_placeholders={
                    "mower_name": mower_name,
                    "hours": str(round(blade_minutes / 60, 1)),
                    "threshold_hours": str(
                        round(blade_threshold_minutes / 60)
                    ),
                },
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, blade_issue_id)

        battery_cycles = self._counter_since_reset(
            product_item, "battery_charge_cycles", "battery_charge_cycles_reset"
        )
        battery_due = (
            battery_cycles is not None
            and battery_cycles >= battery_threshold_cycles
        )
        if battery_due:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                battery_issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="battery_service_due",
                translation_placeholders={
                    "mower_name": mower_name,
                    "cycles": str(battery_cycles),
                    "threshold_cycles": str(battery_threshold_cycles),
                },
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, battery_issue_id)

    def area_mowed_today(self, serial_number: str) -> float | None:
        """Return the cloud counter increase since local midnight."""
        return self._statistics.area_mowed_today(
            serial_number,
            dt_util.now().date(),
        )

    def daily_area_details(self, serial_number: str) -> dict[str, Any]:
        """Return diagnostics for the cloud daily-area calculation."""
        return self._statistics.area_details(serial_number)

    def mowing_minutes_today(self, serial_number: str) -> float:
        """Return locally observed mowing minutes since local midnight."""
        return self._statistics.mowing_minutes_today(
            serial_number,
            datetime.now(UTC),
            dt_util.now().date(),
        )

    def _update_cached_product_item(self, serial_number: str, **fields: Any) -> None:
        """Patch cached product item fields after a successful write."""
        cached = self._product_item_cache.get(serial_number)
        if cached is not None:
            cached[1].update(fields)

        device = (self.data or {}).get(serial_number)
        if device is not None:
            product_item = getattr(device, "_worx_vision_product_item", None)
            if isinstance(product_item, dict):
                product_item.update(fields)

    def _update_cached_rain_delay(self, serial_number: str, minutes: int) -> None:
        """Patch cached rain delay after a successful write."""
        device = (self.data or {}).get(serial_number)
        if device is None:
            return

        rainsensor = getattr(device, "rainsensor", None)
        if isinstance(rainsensor, dict):
            rainsensor["delay"] = minutes
        elif rainsensor is not None and hasattr(rainsensor, "delay"):
            try:
                setattr(rainsensor, "delay", minutes)
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Could not update cached rain delay", exc_info=True)
