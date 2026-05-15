"""Button platform for Worx Vision Cloud Plus."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Awaitable, Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import WorxVisionEntity


@dataclass(frozen=True, kw_only=True)
class WorxButtonDescription(ButtonEntityDescription):
    """Button description."""

    press_fn: Callable[[Any, str], Awaitable[None]]


async def _refresh(coordinator, serial_number: str) -> None:
    await coordinator.async_request_device_update(serial_number)


BUTTONS: tuple[WorxButtonDescription, ...] = (
    WorxButtonDescription(
        key="refresh",
        translation_key="refresh",
        icon="mdi:refresh",
        entity_category=EntityCategory.CONFIG,
        press_fn=_refresh,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WorxVisionButton(runtime.coordinator, entry, serial_number, description)
            for serial_number in runtime.coordinator.data
            for description in BUTTONS
        ]
    )


class WorxVisionButton(WorxVisionEntity, ButtonEntity):
    """Worx button."""

    entity_description: WorxButtonDescription

    def __init__(self, coordinator, entry, serial_number: str, description) -> None:
        """Initialize button."""
        self.entity_description = description
        super().__init__(coordinator, entry, serial_number, description.key)

    async def async_press(self) -> None:
        """Handle press."""
        await self.entity_description.press_fn(self.coordinator, self._serial_number)
