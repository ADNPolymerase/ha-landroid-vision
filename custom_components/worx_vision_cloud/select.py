"""Select platform for Worx Vision Cloud Plus."""
from __future__ import annotations

from itertools import combinations
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import BORDER_DISTANCE_OPTIONS_MM, DOMAIN
from .entity import WorxVisionEntity
from .helpers import get_dict_value, get_nested_value, rtk_map_attributes

DEFAULT_LANGUAGE = "en"
MAX_COMBINATION_ZONES = 5

# The select options are built from dynamic RTK zone combinations, so they cannot be
# declared in translations/*.json. They are localized here from the HA UI language;
# unknown languages fall back to English. Polish wording is preserved.
ALL_ZONES_LABELS = {
    "en": "All zones",
    "fr": "Toutes les zones",
    "de": "Alle Zonen",
    "pl": "Wszystkie strefy",
    "nl": "Alle zones",
    "es": "Todas las zonas",
    "it": "Tutte le zone",
    "sv": "Alla zoner",
    "no": "Alle soner",
    "da": "Alle zoner",
    "ru": "Все зоны",
}
ZONE_SINGULAR_LABELS = {
    "en": "Zone",
    "fr": "Zone",
    "de": "Zone",
    "pl": "Strefa",
    "nl": "Zone",
    "es": "Zona",
    "it": "Zona",
    "sv": "Zon",
    "no": "Sone",
    "da": "Zone",
    "ru": "Зона",
}
ZONE_PLURAL_LABELS = {
    "en": "Zones",
    "fr": "Zones",
    "de": "Zonen",
    "pl": "Strefy",
    "nl": "Zones",
    "es": "Zonas",
    "it": "Zone",
    "sv": "Zoner",
    "no": "Soner",
    "da": "Zoner",
    "ru": "Зоны",
}


def _all_zones_label(language: str) -> str:
    """Return the localized 'all zones' option label."""
    return ALL_ZONES_LABELS.get(language, ALL_ZONES_LABELS[DEFAULT_LANGUAGE])


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up select entities."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = [
        OneTimeMowingZonesSelect(runtime.coordinator, entry, serial_number)
        for serial_number in runtime.coordinator.data
    ]
    entities.extend(
        WorxBorderDistanceSelect(runtime.coordinator, entry, serial_number)
        for serial_number in runtime.coordinator.data
    )
    async_add_entities(entities)


def _zone_ids(device: Any) -> list[int]:
    """Return available RTK zone IDs from the current mower payload."""
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


def _zone_names(device: Any) -> dict[int, str]:
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


def _option_label(
    zone_ids: list[int],
    language: str = DEFAULT_LANGUAGE,
    names: dict[int, str] | None = None,
) -> str:
    """Return a user-facing label for one zone selection.

    Uses the zone names configured in the Worx app when they can be
    resolved, so the picker reads like the app instead of "Zone 1".
    """
    names = names or {}
    if not zone_ids:
        return _all_zones_label(language)
    if len(zone_ids) == 1:
        named = names.get(zone_ids[0])
        if named:
            return named
        singular = ZONE_SINGULAR_LABELS.get(language, ZONE_SINGULAR_LABELS[DEFAULT_LANGUAGE])
        return f"{singular} {zone_ids[0]}"
    if all(zone_id in names for zone_id in zone_ids):
        return " + ".join(names[zone_id] for zone_id in zone_ids)
    plural = ZONE_PLURAL_LABELS.get(language, ZONE_PLURAL_LABELS[DEFAULT_LANGUAGE])
    return plural + " " + ", ".join(str(zone_id) for zone_id in zone_ids)


def _option_map(
    zone_ids: list[int],
    language: str = DEFAULT_LANGUAGE,
    names: dict[int, str] | None = None,
) -> dict[str, list[int]]:
    """Return select option label to zone ID list mapping."""
    result: dict[str, list[int]] = {_all_zones_label(language): []}
    if len(zone_ids) <= MAX_COMBINATION_ZONES:
        for count in range(1, len(zone_ids) + 1):
            for combo in combinations(zone_ids, count):
                selected = list(combo)
                result[_option_label(selected, language, names)] = selected
    else:
        for zone_id in zone_ids:
            result[_option_label([zone_id], language, names)] = [zone_id]
    return result


class OneTimeMowingZonesSelect(WorxVisionEntity, SelectEntity):
    """Local RTK zone selection for one-time mowing."""

    _attr_translation_key = "one_time_mowing_zones"
    _attr_icon = "mdi:map-marker-path"

    def __init__(self, coordinator, entry, serial_number: str) -> None:
        """Initialize one-time mowing zones select."""
        super().__init__(coordinator, entry, serial_number, "one_time_mowing_zones")

    @property
    def _language(self) -> str:
        """Return the active Home Assistant UI language."""
        hass = getattr(self, "hass", None)
        config = getattr(hass, "config", None)
        return getattr(config, "language", None) or DEFAULT_LANGUAGE

    @property
    def options(self) -> list[str]:
        """Return available zone choices."""
        language = self._language
        options = _option_map(
            _zone_ids(self.device), language, _zone_names(self.device)
        )
        current_label = _option_label(
            self.coordinator.one_time_mowing_zones(self._serial_number),
            language,
            _zone_names(self.device),
        )
        if current_label not in options:
            options[current_label] = self.coordinator.one_time_mowing_zones(
                self._serial_number
            )
        return list(options.keys())

    @property
    def current_option(self) -> str | None:
        """Return selected zone choice."""
        return _option_label(
            self.coordinator.one_time_mowing_zones(self._serial_number),
            self._language,
            _zone_names(self.device),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return selected and available zone IDs."""
        return {
            "selected_zone_ids": self.coordinator.one_time_mowing_zones(
                self._serial_number
            ),
            "available_zone_ids": _zone_ids(self.device),
        }

    async def async_select_option(self, option: str) -> None:
        """Select one zone choice."""
        language = self._language
        options = _option_map(
            _zone_ids(self.device), language, _zone_names(self.device)
        )
        current_zones = self.coordinator.one_time_mowing_zones(self._serial_number)
        current_label = _option_label(
            current_zones, language, _zone_names(self.device)
        )
        if current_label not in options:
            options[current_label] = current_zones
        if option not in options:
            raise HomeAssistantError(f"Unknown one-time mowing zone option: {option}")
        await self.coordinator.async_set_one_time_mowing_zones(
            self._serial_number, options[option]
        )


def _raw_cfg(device) -> dict[str, Any]:
    """Return the latest raw mower config payload."""
    value = getattr(device, "raw_cfg", {}) or {}
    return value if isinstance(value, dict) else {}


def _first_raw_zone_cutting(device) -> dict[str, Any]:
    """Return the first zone cutting config from known protocol 1 locations."""
    raw_cfg = _raw_cfg(device)
    for zone_path in (("rtk", "zs"), ("mz", "s")):
        zones = get_nested_value(raw_cfg, *zone_path, default=[]) or []
        if not isinstance(zones, list | tuple):
            continue
        for zone in zones:
            cutting = get_nested_value(zone, "cfg", "cut", default={}) or {}
            if isinstance(cutting, dict) and cutting:
                return cutting
    return {}


def _live_border_distance(device) -> int | None:
    """Return the border distance reported by the mower config, if any."""
    zone_cutting = _first_raw_zone_cutting(device)
    candidates = (
        get_nested_value(_raw_cfg(device), "cut", "bd"),
        get_nested_value(_raw_cfg(device), "cut", "co"),
        get_dict_value(zone_cutting, "bd"),
        get_dict_value(zone_cutting, "co"),
    )
    for candidate in candidates:
        try:
            value = int(candidate)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return None


class WorxBorderDistanceSelect(WorxVisionEntity, SelectEntity):
    """Vision border cutting distance.

    Newer Vision firmwares report the configured value back in the raw
    config (cfg.cut.bd/co, or per-zone cutting configs on protocol 1), so
    the live value is preferred when present. When the mower doesn't
    report it, the entity falls back to the last value set through Home
    Assistant (persisted across restarts) and stays unknown until set
    here once.
    """

    _attr_translation_key = "border_distance"
    _attr_icon = "mdi:ruler"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_assumed_state = True
    _attr_options = [str(value) for value in BORDER_DISTANCE_OPTIONS_MM]

    def __init__(self, coordinator, entry, serial_number: str) -> None:
        """Initialize border distance select."""
        super().__init__(coordinator, entry, serial_number, "border_distance")

    @property
    def available(self) -> bool:
        """Only Vision protocol 1 mowers accept this setting."""
        return (
            super().available
            and getattr(self.device, "protocol", 0) == 1
            and bool(getattr(self.device, "online", False))
        )

    @property
    def current_option(self) -> str | None:
        """Return the live border distance, falling back to the last one set."""
        live_value = _live_border_distance(self.device)
        if live_value is not None and live_value in BORDER_DISTANCE_OPTIONS_MM:
            return str(live_value)
        value = self.coordinator.border_distance(self._serial_number)
        return None if value is None else str(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the raw values behind the live/optimistic state."""
        zone_cutting = _first_raw_zone_cutting(self.device)
        return {
            "api_method": "pyworxcloud.set_border_distance",
            "source": (
                "live"
                if _live_border_distance(self.device) is not None
                else "last_set_from_home_assistant"
            ),
            "raw_top_level_border_distance": get_nested_value(
                _raw_cfg(self.device), "cut", "bd"
            ),
            "raw_top_level_cut_offset": get_nested_value(
                _raw_cfg(self.device), "cut", "co"
            ),
            "raw_zone_border_distance": get_dict_value(zone_cutting, "bd"),
            "raw_zone_cut_offset": get_dict_value(zone_cutting, "co"),
        }

    async def async_select_option(self, option: str) -> None:
        """Send a new border distance to the mower."""
        await self.coordinator.async_set_border_distance(
            self._serial_number, int(option)
        )
