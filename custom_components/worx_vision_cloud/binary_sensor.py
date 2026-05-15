"""Binary sensor platform for Worx Vision Cloud Plus."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ATTR_RAW_PATH,
    ATTR_RAW_SOURCE,
    CONF_EXPOSE_RAW,
    DEFAULT_EXPOSE_RAW,
    DOMAIN,
)
from .entity import WorxVisionEntity
from .helpers import (
    get_dict_value,
    raw_entity_path_map,
    raw_entity_values,
    raw_path_enabled_default,
)


@dataclass(frozen=True, kw_only=True)
class WorxBinarySensorDescription(BinarySensorEntityDescription):
    """Binary sensor description."""

    value_fn: Callable[[Any], bool | None]


def _battery(device, key, default=None):
    return get_dict_value(getattr(device, "battery", {}), key, default)


def _rain(device, key, default=None):
    return get_dict_value(getattr(device, "rainsensor", {}), key, default)


BINARY_SENSORS: tuple[WorxBinarySensorDescription, ...] = (
    WorxBinarySensorDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: bool(getattr(d, "online", False)),
    ),
    WorxBinarySensorDescription(
        key="locked",
        translation_key="locked",
        device_class=BinarySensorDeviceClass.LOCK,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: getattr(d, "locked", None),
    ),
    WorxBinarySensorDescription(
        key="battery_charging",
        translation_key="battery_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda d: _battery(d, "charging")
        if isinstance(_battery(d, "charging"), bool)
        else None,
    ),
    WorxBinarySensorDescription(
        key="rain_triggered",
        translation_key="rain_triggered",
        device_class=BinarySensorDeviceClass.MOISTURE,
        value_fn=lambda d: _rain(d, "triggered"),
    ),
    WorxBinarySensorDescription(
        key="party_mode_enabled",
        translation_key="party_mode_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: getattr(d, "partymode_enabled", None),
    ),
    WorxBinarySensorDescription(
        key="pause_mode_enabled",
        translation_key="pause_mode_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: getattr(d, "pause_mode_enabled", None),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime.coordinator

    entities: list[BinarySensorEntity] = []
    known_raw: set[str] = set()

    for serial_number in coordinator.data:
        entities.extend(
            WorxVisionBinarySensor(coordinator, entry, serial_number, description)
            for description in BINARY_SENSORS
        )

    def add_raw_entities() -> None:
        raw_entities: list[BinarySensorEntity] = []
        if not entry.data.get(CONF_EXPOSE_RAW, DEFAULT_EXPOSE_RAW):
            return

        for serial_number, device in (coordinator.data or {}).items():
            paths = raw_entity_path_map(device)
            for key, value in raw_entity_values(device).items():
                if not isinstance(value, bool):
                    continue
                unique = f"{serial_number}_raw_binary_{key}"
                if unique in known_raw:
                    continue
                known_raw.add(unique)
                raw_entities.append(
                    WorxVisionRawBinarySensor(
                        coordinator,
                        entry,
                        serial_number,
                        key,
                        paths.get(key, key),
                    )
                )

        if raw_entities:
            async_add_entities(raw_entities)

    add_raw_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_raw_entities))
    async_add_entities(entities)


class WorxVisionBinarySensor(WorxVisionEntity, BinarySensorEntity):
    """Regular binary sensor."""

    entity_description: WorxBinarySensorDescription

    def __init__(
        self,
        coordinator,
        entry,
        serial_number: str,
        description: WorxBinarySensorDescription,
    ) -> None:
        """Initialize binary sensor."""
        self.entity_description = description
        super().__init__(coordinator, entry, serial_number, description.key)

    @property
    def is_on(self) -> bool | None:
        """Return current state."""
        value = self.entity_description.value_fn(self.device)
        return value if isinstance(value, bool) else None


class WorxVisionRawBinarySensor(WorxVisionEntity, BinarySensorEntity):
    """Dynamic raw bool sensor."""

    _attr_icon = "mdi:code-json"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
        entry,
        serial_number: str,
        key: str,
        raw_path: str,
    ) -> None:
        """Initialize raw bool sensor."""
        super().__init__(coordinator, entry, serial_number, f"raw_binary_{key}")
        self._raw_key = key
        self._raw_path = raw_path
        self._attr_name = f"Raw {raw_path}"
        self._attr_entity_registry_enabled_default = raw_path_enabled_default(raw_path)

    @property
    def is_on(self) -> bool | None:
        """Return current raw bool."""
        value = raw_entity_values(self.device).get(self._raw_key)
        return value if isinstance(value, bool) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return raw path metadata."""
        return {
            ATTR_RAW_PATH: self._raw_path,
            ATTR_RAW_SOURCE: self._raw_path.split(".", 1)[0],
        }
