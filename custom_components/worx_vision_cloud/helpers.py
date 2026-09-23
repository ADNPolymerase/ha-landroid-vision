"""Helper functions for Worx Vision Cloud Plus."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from enum import Enum
import json
from math import cos, hypot, radians
from typing import Any

from homeassistant.util import slugify

# Shared with lawn_mower.py, sensor.py and coordinator.py so all agree on what
# each mower status means (used e.g. to track today's actual mowing time
# independent of Worx's own, sometimes-stale work-time statistics).
MOWING_STATUS_IDS = {7, 8, 12, 32, 110, 111}
RETURNING_STATUS_IDS = {4, 5, 6, 30, 104}
STARTING_STATUS_IDS = {2, 3, 33, 103}
# Status 0 ("idle") is what a Vision mower reports when its STOP button is
# pressed in the field, including by an obstacle holding it down. It is a
# stop, not an unknown state, so it counts as paused.
PAUSED_STATUS_IDS = {0, 34}
DOCKED_STATUS_IDS = {1}
ERROR_STATUS_IDS = {9, 10, 13}
# Observed live on a Vision Cloud400 during a firmware update started from the
# Worx app: the mower reported status 102 from the moment the download began
# until it had rebooted on the new firmware, then went back to 1. pyworxcloud
# has no description for it, so every status readout showed "unknown".
UPDATING_STATUS_IDS = {102}
# A mower stopped this long away from its base, without charging, raises a
# repair issue: it will not go back to charge on its own and eventually runs
# flat where it stands.
STOPPED_STATUS_IDS = {0}
STOPPED_ALERT_MINUTES = 10
# Docked positions read about 0.5 m from the station marker. The looser
# rtk_at_station threshold (2.5 m) also matched a mower stuck under a shelter
# 2.1 m away, so the alert uses a tighter radius of its own.
STOPPED_DOCK_RADIUS_M = 1.0


def device_entry_by_identifier(
    device_registry: Any, identifier: tuple[str, str], config_entry_id: str
) -> Any:
    """Look up a device by identifier, preferring the non-deprecated API.

    Home Assistant deprecated async_get_device(identifiers=...) because device
    identifiers are no longer unique across config entries, and it stops
    working in 2027.8. The older call stays as a fallback so the integration
    keeps running on the Home Assistant versions it still supports.
    """
    lookup = getattr(device_registry, "async_get_device_by_identifier", None)
    if lookup is not None:
        return lookup(identifier, config_entry_id)
    return device_registry.async_get_device(identifiers={identifier})


def is_firmware_updating(device: Any) -> bool:
    """Return whether the mower is busy applying a firmware update.

    The Worx OTA payload never sets an in-progress flag, so the mower status
    is the only reliable signal that an update is running.
    """
    status = getattr(device, "status", None)
    if not isinstance(status, dict):
        return False
    try:
        return int(status.get("id")) in UPDATING_STATUS_IDS
    except (TypeError, ValueError):
        return False

RAW_SOURCE_ATTRS = (
    "raw_dat",
    "raw_cfg",
    "module_status",
    "module_config",
    "battery",
    "blades",
    "rainsensor",
    "status",
    "error",
    "orientation",
    "zone",
    "schedules",
    "statistics",
    "firmware",
    "warranty",
    "lawn",
)

MAX_LIST_ITEMS = 80
MAX_STRING_STATE_LENGTH = 240

SENSITIVE_RAW_PATHS = {
    "cfg.rtk.ck",
}

NOISY_RAW_PATH_PREFIXES = (
    "cfg.log.",
    "cfg.dk.id.",
    "cfg.sc.slots[",
    "schedules.slots[",
)

NOISY_RAW_PATHS = {
    "cfg.sc.slots.count",
    "schedules.slots.count",
}

SCHEDULE_DEFAULT_LANGUAGE = "en"

# Schedule text is free-form sensor state that Home Assistant cannot translate
# through translations/*.json, so it is localized here from the UI language.
SCHEDULE_DAY_LABELS = {
    "en": {
        "monday": "Mon", "tuesday": "Tue", "wednesday": "Wed", "thursday": "Thu",
        "friday": "Fri", "saturday": "Sat", "sunday": "Sun",
    },
    "de": {
        "monday": "Mo", "tuesday": "Di", "wednesday": "Mi", "thursday": "Do",
        "friday": "Fr", "saturday": "Sa", "sunday": "So",
    },
    "fr": {
        "monday": "lun", "tuesday": "mar", "wednesday": "mer", "thursday": "jeu",
        "friday": "ven", "saturday": "sam", "sunday": "dim",
    },
    "pl": {
        "monday": "pon", "tuesday": "wt", "wednesday": "śr", "thursday": "czw",
        "friday": "pt", "saturday": "sob", "sunday": "niedz",
    },
    "nl": {
        "monday": "ma", "tuesday": "di", "wednesday": "wo", "thursday": "do",
        "friday": "vr", "saturday": "za", "sunday": "zo",
    },
    "es": {
        "monday": "lun", "tuesday": "mar", "wednesday": "mié", "thursday": "jue",
        "friday": "vie", "saturday": "sáb", "sunday": "dom",
    },
    "it": {
        "monday": "lun", "tuesday": "mar", "wednesday": "mer", "thursday": "gio",
        "friday": "ven", "saturday": "sab", "sunday": "dom",
    },
    "sv": {
        "monday": "mån", "tuesday": "tis", "wednesday": "ons", "thursday": "tor",
        "friday": "fre", "saturday": "lör", "sunday": "sön",
    },
    "no": {
        "monday": "man", "tuesday": "tir", "wednesday": "ons", "thursday": "tor",
        "friday": "fre", "saturday": "lør", "sunday": "søn",
    },
    "da": {
        "monday": "man", "tuesday": "tir", "wednesday": "ons", "thursday": "tor",
        "friday": "fre", "saturday": "lør", "sunday": "søn",
    },
    "ru": {
        "monday": "пн", "tuesday": "вт", "wednesday": "ср", "thursday": "чт",
        "friday": "пт", "saturday": "сб", "sunday": "вс",
    },
}

SCHEDULE_TEXT_LABELS = {
    "en": {"none": "no active slots", "count": "{count} active slots", "edge": "+ edge"},
    "de": {"none": "keine aktiven Zeitfenster", "count": "{count} aktive Zeitfenster", "edge": "+ Kante"},
    "fr": {"none": "aucun créneau actif", "count": "{count} créneaux actifs", "edge": "+ bordure"},
    "pl": {"none": "brak aktywnych slotów", "count": "{count} aktywnych slotów", "edge": "+ krawędź"},
    "nl": {"none": "geen actieve tijdvakken", "count": "{count} actieve tijdvakken", "edge": "+ rand"},
    "es": {"none": "ninguna franja activa", "count": "{count} franjas activas", "edge": "+ borde"},
    "it": {"none": "nessuna fascia attiva", "count": "{count} fasce attive", "edge": "+ bordo"},
    "sv": {"none": "inga aktiva tidsfönster", "count": "{count} aktiva tidsfönster", "edge": "+ kant"},
    "no": {"none": "ingen aktive tidsrom", "count": "{count} aktive tidsrom", "edge": "+ kant"},
    "da": {"none": "ingen aktive tidsrum", "count": "{count} aktive tidsrum", "edge": "+ kant"},
    "ru": {"none": "нет активных интервалов", "count": "активных интервалов: {count}", "edge": "+ кромка"},
}


# The day label is written once, then its time ranges. The two levels need
# clearly different separators or the line blurs back into one long list.
SCHEDULE_SLOT_SEPARATOR = ", "
SCHEDULE_DAY_SEPARATOR = " · "


def schedule_language(language: Any) -> str:
    """Return a supported schedule language code (falls back to English)."""
    code = str(language or "").lower().split("-")[0]
    return code if code in SCHEDULE_DAY_LABELS else SCHEDULE_DEFAULT_LANGUAGE

SCHEDULE_DAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def get_dict_value(obj: Any, key: str, default: Any = None) -> Any:
    """Read a key from dict-like or object-like values."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def device_display_name(device: Any) -> str:
    """Return a mower name without an account e-mail prefix."""
    value = str(getattr(device, "name", "") or "").strip()
    first_part, separator, mower_name = value.partition(" ")
    if separator and "@" in first_part and mower_name.strip():
        return mower_name.strip()
    return value or "Worx Landroid Vision"


def get_nested_value(obj: Any, *keys: str, default: Any = None) -> Any:
    """Read a nested key path from dict-like or object-like values."""
    value = obj
    for key in keys:
        value = get_dict_value(value, key, None)
        if value is None:
            return default
    return value


def normalize_scalar(value: Any) -> Any | None:
    """Normalize a value so it is safe as a Home Assistant state."""
    if value is None:
        return None
    if isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, str):
        if len(value) > MAX_STRING_STATE_LENGTH:
            return value[:MAX_STRING_STATE_LENGTH]
        return value
    return None


def stable_json(value: Any) -> str:
    """Return a deterministic compact JSON string."""
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        return str(value)


def raw_path_is_sensitive(path: str) -> bool:
    """Return true when a raw path should never be exposed as an entity."""
    return path in SENSITIVE_RAW_PATHS


def raw_path_enabled_default(path: str) -> bool:
    """Return default enabled state for raw diagnostic entities."""
    if raw_path_is_sensitive(path) or path in NOISY_RAW_PATHS:
        return False
    return not any(path.startswith(prefix) for prefix in NOISY_RAW_PATH_PREFIXES)


def safe_key(path: str) -> str:
    """Return a stable slug key for entity unique IDs."""
    cleaned = (
        path.replace("[", "_")
        .replace("]", "")
        .replace(".", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
    )
    return slugify(cleaned)


def iter_flatten(value: Any, prefix: str) -> Iterable[tuple[str, Any]]:
    """Flatten nested dict/list structures into scalar leaves."""
    if value is None:
        return

    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            next_prefix = f"{prefix}.{key_text}" if prefix else key_text
            yield from iter_flatten(item, next_prefix)
        return

    if isinstance(value, list | tuple):
        yield f"{prefix}.count", len(value)
        for index, item in enumerate(value[:MAX_LIST_ITEMS]):
            yield from iter_flatten(item, f"{prefix}[{index}]")
        return

    scalar = normalize_scalar(value)
    if scalar is not None:
        yield prefix, scalar


def raw_entity_values(device: Any) -> dict[str, Any]:
    """Return all scalar raw/dynamic values for a mower."""
    values: dict[str, Any] = {}

    for attr in RAW_SOURCE_ATTRS:
        source_value = getattr(device, attr, None)
        if source_value is None:
            continue
        source_name = attr.removeprefix("raw_")
        for path, value in iter_flatten(source_value, source_name):
            if raw_path_is_sensitive(path):
                continue
            key = safe_key(path)
            if key:
                values[key] = value

    # A few useful top-level object attributes that pyworxcloud maps from the API.
    for attr in (
        "online",
        "locked",
        "mac_address",
        "model",
        "name",
        "protocol",
        "rssi",
        "time_zone",
        "updated",
        "updated_origin",
        "uuid",
    ):
        if hasattr(device, attr):
            scalar = normalize_scalar(getattr(device, attr))
            if scalar is not None:
                values[safe_key(attr)] = scalar

    return values


def raw_entity_path_map(device: Any) -> dict[str, str]:
    """Return entity key -> readable raw path map."""
    result: dict[str, str] = {}

    for attr in RAW_SOURCE_ATTRS:
        source_value = getattr(device, attr, None)
        if source_value is None:
            continue
        source_name = attr.removeprefix("raw_")
        for path, value in iter_flatten(source_value, source_name):
            if raw_path_is_sensitive(path):
                continue
            key = safe_key(path)
            if key:
                result[key] = path

    for attr in (
        "online",
        "locked",
        "mac_address",
        "model",
        "name",
        "protocol",
        "rssi",
        "time_zone",
        "updated",
        "updated_origin",
        "uuid",
    ):
        if hasattr(device, attr):
            key = safe_key(attr)
            result[key] = attr

    return result


def _raw_cfg(device: Any) -> Any:
    """Return raw cfg payload from pyworxcloud."""
    return getattr(device, "raw_cfg", {}) or {}


def _raw_dat(device: Any) -> Any:
    """Return raw dat payload from pyworxcloud."""
    return getattr(device, "raw_dat", {}) or {}


# Starting a one-time job the way the Worx app does, watched live on Vision
# firmware 3.46.0+47: `cmd` 1 with a top-level `cut` block. The mower then
# creates a new task on those zones, replacing whatever task it had on hold.
ZONE_JOB_COMMAND = 1


def zone_job_command(
    zone_ids: Any, edge_cut: Any, fixed_order: Any, all_zone_ids: Any = ()
) -> dict[str, Any]:
    """Return the command starting a one-time job, as the Worx app sends it.

    `b` asks for the edge routine, `z` lists the zones and `zo` says whether
    they are mowed in the order given (1, the app's "Special") or in the order
    the mower picks (0, "Auto"). No duration travels with it: the mower mows
    the zones through, then goes home.

    Without a selection every known zone is sent, since the app always sends
    a real list; an order only means something for a selection, so that case
    is always sent as "Auto".
    """
    zones = [int(zone) for zone in (zone_ids or [])]
    fixed = bool(fixed_order) and bool(zones)
    if not zones:
        zones = [int(zone) for zone in (all_zone_ids or [])]
    return {
        "cmd": ZONE_JOB_COMMAND,
        "cut": {"b": int(bool(edge_cut)), "z": zones, "zo": int(fixed)},
    }


# The mower stamps a task with its own clock, so allow for drift.
ZONE_JOB_CLOCK_SLACK = timedelta(minutes=1)


def zone_job_task_started(
    device: Any, command: dict[str, Any], sent_at: datetime
) -> bool:
    """Return whether the mower created a task for a zone job sent at `sent_at`.

    An unanswered command is not always a lost one: seen live, the mower
    created the task two seconds after the command, but its first report only
    came a minute later, under an unrelated message id. The task list is what
    tells the two apart: a manual task (`tr` 1) stamped after the command, on
    zones that were asked for.
    """
    requested = {int(zone) for zone in get_nested_value(command, "cut", "z", default=[]) or []}
    tasks = get_nested_value(_raw_dat(device), "cut", "tsk", default=[]) or []
    if not isinstance(tasks, list):
        return False
    for task in tasks:
        if not isinstance(task, dict) or task.get("tr") != 1:
            continue
        try:
            created = datetime.fromisoformat(str(task.get("tm")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if created.tzinfo is None or created < sent_at - ZONE_JOB_CLOCK_SLACK:
            continue
        zones = {
            int(zone["id"])
            for zone in task.get("z") or []
            if isinstance(zone, dict) and isinstance(zone.get("id"), int)
        }
        if zones and zones <= requested:
            return True
    return False


# Mowing pattern codes, as cut_type in the Worx map and `t` in the mower's
# per-zone config. Observed in the Worx app and pyworxcloud issue #398.
ZONE_CUT_PATTERNS = {0: "natural", 1: "parallel", 4: "diamond", 5: "checker"}
ZONE_CUT_PATTERN_OPTIONS = [*ZONE_CUT_PATTERNS.values(), "other"]


def rtk_zone_cuts(device: Any) -> dict[int, dict[str, Any]]:
    """Return each RTK zone's mowing pattern and angle, keyed by zone id.

    Read from the mower's own per-zone config (`cfg.rtk.zs[].cfg.cut`), which
    the mower updates once a change made in the Worx app is activated, so it
    shows what the mower will actually mow. `t` is the pattern, `d` the angle
    in degrees.
    """
    names = rtk_zone_names(device)
    cuts: dict[int, dict[str, Any]] = {}
    for zone in rtk_map_attributes(device).get("zones", []) or []:
        try:
            zone_id = int(get_dict_value(zone, "id"))
        except (TypeError, ValueError):
            continue
        if zone_id <= 0:
            continue
        cutting = get_dict_value(zone, "cutting", {}) or {}
        if not isinstance(cutting, dict):
            cutting = {}
        code = cutting.get("t")
        try:
            code = int(code) if code is not None else None
        except (TypeError, ValueError):
            code = None
        try:
            direction = int(cutting["d"]) % 360 if cutting.get("d") is not None else None
        except (TypeError, ValueError):
            direction = None
        cuts[zone_id] = {
            "name": names.get(zone_id),
            "pattern": None if code is None else ZONE_CUT_PATTERNS.get(code, "other"),
            "pattern_code": code,
            "direction": direction,
        }
    return cuts


_LOCATION_KEY_PARTS = ("lat", "lon", "lng", "coord", "pos", "point", "center", "centre", "geo")


def safe_shape(value: Any, depth: int = 2) -> Any:
    """Describe a payload's structure without any location data.

    Scalars are kept, except under keys that name a position. A list of
    plain values (a contour, a coordinate pair) is reduced to its length,
    and anything below `depth` to its keys or length, so a map dump shows
    how zones are identified without a single point of their geometry.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        if depth <= 0:
            return f"<dict keys={sorted(str(key) for key in value)}>"
        shaped: dict[str, Any] = {}
        for key, item in value.items():
            name = str(key)
            if any(part in name.lower() for part in _LOCATION_KEY_PARTS):
                shaped[name] = "**REDACTED**"
            else:
                shaped[name] = safe_shape(item, depth - 1)
        return shaped
    if isinstance(value, (list, tuple)):
        if depth > 0 and value and all(isinstance(item, dict) for item in value):
            return [safe_shape(item, depth - 1) for item in value[:5]]
        return f"<list len={len(value)}>"
    return f"<{type(value).__name__}>"


def raw_schedule_config(device: Any) -> dict[str, Any]:
    """Return the raw `cfg.sc` schedule block exactly as the mower publishes it.

    pyworxcloud normalizes schedules down to day, start, duration and border
    cut, and drops every field it does not model. On RTK mowers that includes
    the zone list each weekly slot carries, and the one-time job block, so
    neither is reachable from the parsed schedule. The raw block is the only
    place they survive, which is why diagnostics expose it verbatim.
    """
    schedule = get_dict_value(_raw_cfg(device), "sc", {})
    return schedule if isinstance(schedule, dict) else {}


def rtk_map_id(device: Any) -> Any:
    """Return RTK map identifier when the mower reports one."""
    return get_nested_value(_raw_cfg(device), "rtk", "map")


def rtk_map_attributes(device: Any) -> dict[str, Any]:
    """Return RTK map metadata that is available without map geometry."""
    rtk = get_dict_value(_raw_cfg(device), "rtk", {}) or {}
    zones = get_dict_value(rtk, "zs", []) or []
    if not isinstance(zones, list | tuple):
        zones = []

    return {
        "map_id": get_dict_value(rtk, "map"),
        "status": get_dict_value(rtk, "st"),
        "zones": [
            {
                "id": get_dict_value(zone, "id"),
                "cutting": get_nested_value(zone, "cfg", "cut", default={}),
                "schedule": get_nested_value(zone, "cfg", "sc", default={}),
            }
            for zone in zones
            if isinstance(zone, dict)
        ],
    }


def rtk_zone_ids(device: Any) -> list[int]:
    """Return the RTK zone ids of the mower's map, sorted."""
    zones = rtk_map_attributes(device).get("zones", []) or []
    zone_ids: list[int] = []
    for zone in zones:
        zone_id = get_dict_value(zone, "id")
        try:
            zone_id = int(zone_id)
        except (TypeError, ValueError):
            continue
        if zone_id > 0 and zone_id not in zone_ids:
            zone_ids.append(zone_id)
    return sorted(zone_ids)


def rtk_position(device: Any) -> tuple[float, float] | None:
    """Return current RTK latitude/longitude position."""
    position = get_nested_value(_raw_dat(device), "rtk", "pos", default=[])
    if not isinstance(position, list | tuple) or len(position) < 2:
        return None

    try:
        latitude = float(position[0])
        longitude = float(position[1])
    except (TypeError, ValueError):
        return None

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def rtk_station_position(device: Any) -> tuple[float, float] | None:
    """Return the RTK station marker position from cached map geometry."""
    map_data = getattr(device, "_worx_vision_rtk_map", None)
    if not isinstance(map_data, dict):
        return None

    markers = get_nested_value(map_data, "layers", "markers", default=[]) or []
    if not isinstance(markers, list | tuple):
        return None

    for marker in markers:
        if not isinstance(marker, dict):
            continue
        pair = (
            get_nested_value(marker, "record", "latitude"),
            get_nested_value(marker, "record", "longitude"),
        )
        try:
            latitude = float(pair[0])
            longitude = float(pair[1])
        except (TypeError, ValueError):
            continue
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return latitude, longitude

    return None


def distance_meters(
    first: tuple[float, float], second: tuple[float, float]
) -> float:
    """Return an approximate distance between two latitude/longitude pairs."""
    mean_latitude = radians((first[0] + second[0]) / 2)
    latitude_m = (first[0] - second[0]) * 110_540
    longitude_m = (first[1] - second[1]) * 111_320 * cos(mean_latitude)
    return hypot(latitude_m, longitude_m)


def rtk_distance_to_station_m(device: Any) -> float | None:
    """Return distance from current RTK position to the station marker."""
    position = rtk_position(device)
    station = rtk_station_position(device)
    if position is None or station is None:
        return None
    return distance_meters(position, station)


def rtk_at_station(device: Any, threshold_m: float = 2.5) -> bool:
    """Return true when RTK position is close enough to the station marker."""
    distance = rtk_distance_to_station_m(device)
    return distance is not None and distance <= threshold_m


def _zone_point_pair(point: Any) -> tuple[float, float] | None:
    """Return a latitude/longitude pair from a Worx RTK map point."""
    if not isinstance(point, list | tuple) or len(point) < 2:
        return None
    try:
        latitude = float(point[0])
        longitude = float(point[1])
    except (TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def _zone_contour_points(contour: Any) -> list[tuple[float, float]]:
    """Return normalized latitude/longitude points from one RTK map contour."""
    if not isinstance(contour, dict):
        return []
    return [
        pair
        for pair in (
            _zone_point_pair(point)
            for point in get_dict_value(contour, "points", []) or []
        )
        if pair is not None
    ]


def _point_in_ring(
    point: tuple[float, float], ring: list[tuple[float, float]]
) -> bool:
    """Return whether a latitude/longitude point is inside a polygon ring."""
    if len(ring) < 3:
        return False

    x, y = point[1], point[0]
    inside = False
    x1, y1 = ring[-1][1], ring[-1][0]
    for latitude, longitude in ring:
        x2, y2 = longitude, latitude
        if (y1 > y) != (y2 > y):
            x_intersect = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_intersect:
                inside = not inside
        x1, y1 = x2, y2
    return inside


def _point_in_contour(point: tuple[float, float], contour: Any) -> bool:
    """Return whether point is inside a contour and outside its hole children."""
    if not _point_in_ring(point, _zone_contour_points(contour)):
        return False

    for child in get_dict_value(contour, "children", []) or []:
        if isinstance(child, dict) and _point_in_ring(
            point, _zone_contour_points(child)
        ):
            return False
    return True


def rtk_current_zone(device: Any) -> dict[str, Any] | None:
    """Return the RTK map zone containing the mower's current position."""
    position = rtk_position(device)
    if position is None:
        return None

    map_data = getattr(device, "_worx_vision_rtk_map", None)
    if not isinstance(map_data, dict):
        return None

    boundaries = get_nested_value(map_data, "layers", "boundaries", default=[]) or []
    if not isinstance(boundaries, list | tuple):
        return None

    for boundary in boundaries:
        for zone in get_dict_value(boundary, "zones", []) or []:
            if not isinstance(zone, dict) or is_transit_zone(zone):
                continue
            for contour in get_dict_value(zone, "contours", []) or []:
                if _point_in_contour(position, contour):
                    return zone
    return None


def is_transit_zone(zone: Any) -> bool:
    """Return true for a map zone the mower only drives through.

    Corridors linking two mowing areas come with an empty metadata block,
    while mowing zones carry their cutting settings. Zones without any
    metadata key at all are not treated as corridors, so older or partial
    map payloads keep resolving as before.
    """
    if not isinstance(zone, dict) or "metadata" not in zone:
        return False
    metadata = zone.get("metadata")
    if not isinstance(metadata, dict):
        return False
    return not any(key in metadata for key in ("cut_type", "cut_direction"))


def is_stopped_away_from_base(device: Any) -> bool:
    """Return whether the mower is stopped in the field and not charging."""
    status_id = get_dict_value(getattr(device, "status", {}), "id")
    try:
        if int(status_id) not in STOPPED_STATUS_IDS:
            return False
    except (TypeError, ValueError):
        return False

    if get_dict_value(getattr(device, "battery", {}), "charging") is True:
        return False

    error_description = str(
        get_dict_value(getattr(device, "error", {}), "description") or ""
    ).strip().lower().replace("_", " ")
    if error_description == "rain delay":
        return False

    distance = rtk_distance_to_station_m(device)
    return distance is None or distance > STOPPED_DOCK_RADIUS_M


def rtk_current_zone_name(device: Any) -> str | None:
    """Return the configured RTK zone name containing the current position."""
    zone = rtk_current_zone(device)
    if zone is None:
        return None

    name = get_dict_value(zone, "name")
    if name not in (None, ""):
        return str(name)

    zone_id = get_dict_value(zone, "id")
    return f"Zone {zone_id}" if zone_id not in (None, "") else None


# An RTK position drifts out of its zone for a few seconds when the mower
# hugs a contour, and crossing the corridor between two areas takes a few
# tens of seconds. Both used to read unknown, which made the history
# unreadable. Kept short on purpose: a real trip between two areas can last
# minutes, and inventing a zone for that long would be worse than saying
# nothing.
ZONE_SMOOTHING_SECONDS = 30


def smoothed_zone_name(
    current: str | None,
    last_known: str | None,
    unknown_since: datetime | None,
    now: datetime,
    grace_seconds: int = ZONE_SMOOTHING_SECONDS,
) -> str | None:
    """Return the zone to show, holding the last one through a short gap.

    A position outside every mowing zone is only honest for so long: past
    the grace period the sensor says unknown again, so a mower genuinely
    parked or off the map is never reported as still mowing somewhere.
    """
    if current is not None:
        return current
    if last_known is None or unknown_since is None:
        return None
    if (now - unknown_since).total_seconds() < grace_seconds:
        return last_known
    return None


def masked_connectivity(
    live_connected: bool | None,
    disconnected_since: datetime | None,
    grace_minutes: int,
    now: datetime,
) -> bool | None:
    """Return the connectivity state to report, hiding short drops.

    Short cloud/MQTT drops are routine (AWS IoT reconnects, wifi blips,
    mower sleep) and would otherwise spam the recorder and logbook with
    connected/disconnected churn. A drop only becomes reportable once it
    has lasted longer than the grace period; reconnection always shows
    immediately. grace_minutes <= 0 reports the live state unchanged.
    """
    if live_connected or live_connected is None:
        return live_connected
    if grace_minutes <= 0 or disconnected_since is None:
        return False
    return now - disconnected_since < timedelta(minutes=grace_minutes)


def rtk_location_attributes(device: Any) -> dict[str, Any]:
    """Return RTK location diagnostic attributes."""
    dat_rtk = get_nested_value(_raw_dat(device), "rtk", default={}) or {}
    return {
        "map_id": rtk_map_id(device),
        "provider": get_dict_value(dat_rtk, "provider"),
        "gps": get_dict_value(dat_rtk, "gps"),
        "imu": get_dict_value(dat_rtk, "imu"),
        "network": get_dict_value(dat_rtk, "network"),
    }


def schedule_slots(device: Any) -> list[Any]:
    """Return normalized schedule slot objects from pyworxcloud."""
    schedules = getattr(device, "schedules", {}) or {}
    slots = get_dict_value(schedules, "slots", []) or []
    if not isinstance(slots, list | tuple):
        return []
    return [slot for slot in slots if get_dict_value(slot, "day") is not None]


def schedule_day_index(day: Any) -> int | None:
    """Return Python weekday index for a pyworxcloud schedule day."""
    if day is None:
        return None
    return SCHEDULE_DAY_INDEX.get(str(day).lower())


def parse_schedule_time(value: Any) -> time | None:
    """Parse an HH:MM schedule time from pyworxcloud data."""
    if not isinstance(value, str) or ":" not in value:
        return None
    hour, minute, *_ = value.split(":")
    try:
        return time(hour=int(hour), minute=int(minute))
    except ValueError:
        return None


def _library_next_schedule_start(device: Any, now: datetime) -> datetime | None:
    """Return the next start computed by pyworxcloud, if available.

    pyworxcloud exposes ``schedules["next_schedule_start"]`` either as a
    datetime or as a wall-clock string; observed formats include both naive
    ("2026-07-06 10:00:00") and offset-aware ("2026-07-08 08:00:00+02:00")
    values. Naive values are the local schedule time, so ``now``'s timezone is
    attached to make them comparable.
    """
    schedules = getattr(device, "schedules", {}) or {}
    raw = get_dict_value(schedules, "next_schedule_start")
    if isinstance(raw, datetime):
        parsed = raw
    elif isinstance(raw, str) and raw.strip():
        try:
            parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=now.tzinfo)
    return parsed.astimezone(now.tzinfo)


def next_schedule_start(device: Any, now: datetime) -> datetime | None:
    """Return the next scheduled mowing start at or after ``now``.

    Prefers the value already computed by pyworxcloud
    (``schedules["next_schedule_start"]``) when it is still in the future, and
    falls back to deriving it from the weekly slots ourselves. Returns None
    when the native schedule is disabled or party mode suspends it. Returns a
    timezone-aware datetime (matching ``now``'s tzinfo) otherwise.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    schedules = getattr(device, "schedules", {}) or {}
    if get_dict_value(schedules, "party_mode_enabled") is True:
        return None

    from_library = _library_next_schedule_start(device, now)
    if from_library is not None and from_library >= now:
        return from_library

    # `schedules["active"]` is unreliable on Vision protocol 1 mowers:
    # observed False while the weekly schedule was genuinely running and
    # pyworxcloud itself still computed next_schedule_start. Only treat it
    # as "schedule disabled" when the library offers no future start either.
    if get_dict_value(schedules, "active") is False:
        return None

    slots = schedule_slots(device)
    if not slots:
        return None

    candidates: list[datetime] = []
    for offset in range(0, 14):
        day = (now + timedelta(days=offset)).date()
        for slot in slots:
            if schedule_day_index(get_dict_value(slot, "day")) != day.weekday():
                continue
            start_time = parse_schedule_time(get_dict_value(slot, "start"))
            if start_time is None:
                continue
            start = datetime.combine(day, start_time, tzinfo=now.tzinfo)
            if start >= now:
                candidates.append(start)

    return min(candidates) if candidates else None


def rtk_zone_names(device: Any) -> dict[int, str]:
    """Map RTK zone ids to the names configured in the Worx app.

    The schedule config (cfg.rtk.zs) carries the zone ids the mower accepts
    for one-time mowing but no names, while the map holds the names without
    those ids. Both sides expose the cutting direction, so zones are paired
    on it when every direction is distinct, and by order otherwise. Transit
    zones are skipped: they have no cutting metadata and no schedule entry.
    """
    cfg_zones = rtk_map_attributes(device).get("zones", []) or []
    pairs: list[tuple[int, Any]] = []
    for zone in cfg_zones:
        try:
            zone_id = int(get_dict_value(zone, "id"))
        except (TypeError, ValueError):
            continue
        if zone_id > 0:
            pairs.append(
                (zone_id, get_nested_value(zone, "cutting", "d", default=None))
            )

    map_data = getattr(device, "_worx_vision_rtk_map", None)
    map_zones: list[tuple[str, Any]] = []
    if isinstance(map_data, dict):
        boundaries = (
            get_nested_value(map_data, "layers", "boundaries", default=[]) or []
        )
        for boundary in boundaries:
            for zone in get_dict_value(boundary, "zones", []) or []:
                if not isinstance(zone, dict):
                    continue
                metadata = get_dict_value(zone, "metadata", {}) or {}
                if not isinstance(metadata, dict) or not any(
                    key in metadata for key in ("cut_type", "cut_direction")
                ):
                    continue
                name = get_dict_value(zone, "name")
                if name in (None, ""):
                    continue
                map_zones.append(
                    (str(name), get_dict_value(metadata, "cut_direction"))
                )

    if not pairs or not map_zones:
        return {}

    names: dict[int, str] = {}
    cfg_dirs = [d for _, d in pairs if d is not None]
    map_dirs = [d for _, d in map_zones if d is not None]
    if (
        len(cfg_dirs) == len(pairs)
        and len(map_dirs) == len(map_zones)
        and len(set(cfg_dirs)) == len(cfg_dirs)
        and len(set(map_dirs)) == len(map_dirs)
    ):
        by_direction = {direction: name for name, direction in map_zones}
        for zone_id, direction in pairs:
            name = by_direction.get(direction)
            if name is not None:
                names[zone_id] = name

    if len(names) != len(pairs):
        # Directions were ambiguous or missing: fall back to map order.
        names = {}
        for (zone_id, _), (name, _) in zip(sorted(pairs), map_zones):
            names[zone_id] = name

    # Keep labels unambiguous if the app reuses a name across zones.
    seen: dict[str, int] = {}
    for zone_id, name in list(names.items()):
        seen[name] = seen.get(name, 0) + 1
    for zone_id, name in list(names.items()):
        if seen[name] > 1:
            names[zone_id] = f"{name} ({zone_id})"
    return names


# Raw protocol 1 slots number the week from Sunday (0) while pyworxcloud names
# the days, so a parsed slot is matched to its raw twin on day and start.
RAW_SCHEDULE_DAY = {name: (index + 1) % 7 for name, index in SCHEDULE_DAY_INDEX.items()}


def _schedule_minutes(value: Any) -> int | None:
    """Return minutes since midnight for an HH:MM schedule time."""
    parsed = parse_schedule_time(value)
    if parsed is None:
        return None
    return parsed.hour * 60 + parsed.minute


def raw_schedule_slot_cut(device: Any, slot: Any) -> dict[str, Any] | None:
    """Return the raw cut block of the weekly slot matching a parsed slot.

    pyworxcloud keeps day, start and duration but drops the cut block, which
    on protocol 1 carries the zones the slot is limited to (`z`) and whether
    their order was imposed in the Worx app (`zo`). Only protocol 1 slots
    carry it; None when the slot has no raw twin.
    """
    raw_slots = raw_schedule_config(device).get("slots")
    if not isinstance(raw_slots, list):
        return None
    day = RAW_SCHEDULE_DAY.get(str(get_dict_value(slot, "day") or "").lower())
    start = _schedule_minutes(get_dict_value(slot, "start"))
    if day is None or start is None:
        return None
    for raw in raw_slots:
        if not isinstance(raw, dict):
            continue
        if raw.get("d") != day or raw.get("s") != start:
            continue
        cut = get_nested_value(raw, "cfg", "cut", default=None)
        return cut if isinstance(cut, dict) else None
    return None


def schedule_slot_zones(device: Any, slot: Any) -> dict[str, Any]:
    """Return the zones a weekly slot mows, as set in the Worx app.

    Verified on Vision firmware 3.46.0+47: the mower honours these zones,
    in order when `zone_order` is "ordered" (the app's Special mode). In
    "auto" mode it picks the order itself among the listed zones. All
    values are None when the slot carries no zone information.
    """
    cut = raw_schedule_slot_cut(device, slot)
    zones = cut.get("z") if cut else None
    if not isinstance(zones, list):
        return {"zones": None, "zone_names": None, "zone_order": None}
    names = rtk_zone_names(device)
    zone_ids: list[Any] = []
    for zone in zones:
        try:
            zone_ids.append(int(zone))
        except (TypeError, ValueError):
            zone_ids.append(zone)
    return {
        "zones": zone_ids,
        "zone_names": [names.get(zone, f"Zone {zone}") for zone in zone_ids],
        "zone_order": "ordered" if cut.get("zo") else "auto",
    }


def schedule_day_label(day: Any, language: str = SCHEDULE_DEFAULT_LANGUAGE) -> str:
    """Return a short, localized human label for a schedule day."""
    if day is None:
        return ""
    labels = SCHEDULE_DAY_LABELS[schedule_language(language)]
    return labels.get(str(day).lower(), str(day))


def schedule_slot_time(slot: Any, language: str = SCHEDULE_DEFAULT_LANGUAGE) -> str:
    """Return one slot's time range, without the day label."""
    lang = schedule_language(language)
    start = get_dict_value(slot, "start")
    end = get_dict_value(slot, "end")
    duration = get_dict_value(slot, "duration_extended")
    if duration is None:
        duration = get_dict_value(slot, "duration")

    if start and end:
        text = f"{start}-{end}"
    elif start and duration is not None:
        text = f"{start} ({duration} min)"
    else:
        return ""

    if get_dict_value(slot, "boundary"):
        text = f"{text} {SCHEDULE_TEXT_LABELS[lang]['edge']}"
    return text


def schedule_slot_summary(slot: Any, language: str = SCHEDULE_DEFAULT_LANGUAGE) -> str:
    """Return one compact, localized schedule slot line, day label included."""
    lang = schedule_language(language)
    day = schedule_day_label(get_dict_value(slot, "day"), lang)
    time_text = schedule_slot_time(slot, lang)
    if not time_text:
        return day or "slot"
    return f"{day} {time_text}".strip()


def schedule_slots_by_day(slots: Any) -> list[tuple[Any, list[Any]]]:
    """Group slots by day, keeping the order the mower reports them in.

    A day appears once even when its slots are not contiguous in the raw
    list, so the summary never repeats a day label.
    """
    days: dict[str, Any] = {}
    grouped: dict[str, list[Any]] = {}
    for slot in slots or []:
        day = get_dict_value(slot, "day")
        key = str(day).lower()
        if key not in grouped:
            days[key] = day
            grouped[key] = []
        grouped[key].append(slot)
    return [(days[key], day_slots) for key, day_slots in grouped.items()]


def schedule_day_summary(
    day: Any, slots: Any, language: str = SCHEDULE_DEFAULT_LANGUAGE
) -> str:
    """Return one day of the schedule: its label, then its time ranges.

    When every slot of the day cuts the edge, the marker is written once
    at the end instead of after each range. The Worx app sets the edge
    per slot but sends the same value to all of them, so in practice this
    is what the mower reports and it keeps the line inside the 255
    characters a Home Assistant state allows. A mixed day keeps the
    marker on each range that carries it, which reads like a factored day
    when only the last range is edged; the mower never reports that.
    """
    lang = schedule_language(language)
    label = schedule_day_label(day, lang)
    times = [
        text
        for text in (schedule_slot_time(slot, lang) for slot in slots or [])
        if text
    ]
    if not times:
        return label or "slot"

    edge = SCHEDULE_TEXT_LABELS[lang]["edge"]
    suffix = f" {edge}"
    if len(times) > 1 and all(text.endswith(suffix) for text in times):
        times = [text[: -len(suffix)] for text in times]
        ranges = f"{SCHEDULE_SLOT_SEPARATOR.join(times)}{suffix}"
    else:
        ranges = SCHEDULE_SLOT_SEPARATOR.join(times)
    return f"{label} {ranges}".strip()


def schedule_summary_text(
    device: Any, language: str = SCHEDULE_DEFAULT_LANGUAGE
) -> str:
    """Return the whole week, one block per day, whatever its length."""
    lang = schedule_language(language)
    return SCHEDULE_DAY_SEPARATOR.join(
        schedule_day_summary(day, day_slots, lang)
        for day, day_slots in schedule_slots_by_day(schedule_slots(device))
    )


def schedule_summary(device: Any, language: str = SCHEDULE_DEFAULT_LANGUAGE) -> str | None:
    """Return a compact, localized schedule summary for Home Assistant state."""
    lang = schedule_language(language)
    slots = schedule_slots(device)
    if not slots:
        return SCHEDULE_TEXT_LABELS[lang]["none"]

    summary = schedule_summary_text(device, lang)
    if len(summary) <= MAX_STRING_STATE_LENGTH:
        return summary
    return SCHEDULE_TEXT_LABELS[lang]["count"].format(count=len(slots))


def schedule_slot_attributes(
    device: Any, slot: Any, language: str = SCHEDULE_DEFAULT_LANGUAGE
) -> dict[str, Any]:
    """Return one slot as cards and templates consume it."""
    return {
        "day": get_dict_value(slot, "day"),
        "day_label": schedule_day_label(get_dict_value(slot, "day"), language),
        "start": get_dict_value(slot, "start"),
        "end": get_dict_value(slot, "end"),
        "duration": get_dict_value(slot, "duration"),
        "duration_extended": get_dict_value(slot, "duration_extended"),
        "boundary": get_dict_value(slot, "boundary"),
        "source": get_dict_value(slot, "source"),
        **schedule_slot_zones(device, slot),
    }


def schedule_attributes(
    device: Any, language: str = SCHEDULE_DEFAULT_LANGUAGE
) -> dict[str, Any]:
    """Return structured schedule data for cards and templates."""
    schedules = getattr(device, "schedules", {}) or {}
    slots = schedule_slots(device)
    auto_schedule = get_dict_value(schedules, "auto_schedule", {}) or {}
    lang = schedule_language(language)

    return {
        "active_slots": len(slots),
        # The state is capped at 255 characters and falls back to a count
        # when the week is too long to fit; this one never is.
        "text": schedule_summary_text(device, lang),
        "slots": [schedule_slot_attributes(device, slot, lang) for slot in slots],
        "by_day": [
            {
                "day": day,
                "day_label": schedule_day_label(day, lang),
                "text": schedule_day_summary(day, day_slots, lang),
                "slots": [
                    schedule_slot_attributes(device, slot, lang)
                    for slot in day_slots
                ],
            }
            for day, day_slots in schedule_slots_by_day(slots)
        ],
        "auto_schedule_enabled": get_dict_value(auto_schedule, "enabled"),
        "one_time_schedule": get_dict_value(schedules, "one_time_schedule"),
        "party_mode_enabled": get_dict_value(schedules, "party_mode_enabled"),
        "time_extension": get_dict_value(schedules, "time_extension"),
        "next_schedule_start": get_dict_value(schedules, "next_schedule_start"),
    }
