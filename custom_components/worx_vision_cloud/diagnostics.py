"""Diagnostics support for Worx Vision Cloud Plus.

Powers the "Download diagnostics" button on the integration page so users
can attach a useful, pre-redacted dump to GitHub issues instead of hand
sanitizing logs. Location data (RTK coordinates, map geometry, addresses)
and account/device identifiers are removed before the dump leaves
Home Assistant.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .helpers import get_dict_value, get_nested_value

TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    "access_token",
    "address",
    "city",
    "coordinates",
    "gps",
    "lat",
    "latitude",
    "lon",
    "longitude",
    "mac",
    "mac_address",
    "mqtt_endpoint",
    "mqtt_topics",
    "position",
    "postcode",
    "road",
    "serial",
    "serial_number",
    "sim",
    "sn",
    "token",
    "uid",
    "user_id",
    "uuid",
}

DEVICE_SECTIONS = (
    "battery",
    "blades",
    "capabilities",
    "error",
    "firmware",
    "lawn",
    "module_config",
    "module_status",
    "online",
    "orientation",
    "protocol",
    "rainsensor",
    "schedules",
    "statistics",
    "status",
    "zone",
)


def _serializable(value: Any) -> Any:
    """Return a JSON-friendly representation of pyworxcloud values."""
    if isinstance(value, dict):
        return {str(key): _serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serializable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)



def _rtk_map_zone_summary(device: Any) -> list[dict[str, Any]] | None:
    """Summarize RTK map zones without leaking any coordinates.

    Only identity and measurements are included (no contour points), so the
    dump stays safe to attach to an issue while still showing how many zones
    the map holds and what each one measures. Useful because the map can
    contain zones that are not mowed (transit corridors between mowing
    zones), which have no counterpart in the cfg.rtk.zs schedule config.
    """
    map_data = getattr(device, "_worx_vision_rtk_map", None)
    if not isinstance(map_data, dict):
        return None

    zones: list[dict[str, Any]] = []
    boundaries = get_nested_value(map_data, "layers", "boundaries", default=[]) or []
    for boundary in boundaries:
        for zone in get_dict_value(boundary, "zones", []) or []:
            if not isinstance(zone, dict):
                continue
            contours = get_dict_value(zone, "contours", []) or []
            zones.append(
                {
                    "id": get_dict_value(zone, "id"),
                    "name": get_dict_value(zone, "name"),
                    "area": get_dict_value(zone, "area"),
                    "perimeter": get_dict_value(zone, "perimeter"),
                    "metadata": get_dict_value(zone, "metadata"),
                    "keys": sorted(zone.keys()),
                    "contour_count": len(contours) if isinstance(contours, list) else 0,
                }
            )
    return zones


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime.coordinator

    devices: dict[str, Any] = {}
    for index, (serial_number, device) in enumerate(
        (coordinator.data or {}).items()
    ):
        sections = {
            section: _serializable(getattr(device, section, None))
            for section in DEVICE_SECTIONS
        }
        sections["model"] = _serializable(getattr(device, "model", None))
        sections["product_item"] = _serializable(
            getattr(device, "_worx_vision_product_item", None)
        )
        sections["firmware_upgrade"] = _serializable(
            getattr(device, "_worx_vision_firmware_upgrade", None)
        )
        sections["rtk_map_zones"] = _rtk_map_zone_summary(device)
        sections["daily_statistics"] = {
            "area_mowed_today": coordinator.area_mowed_today(serial_number),
            "area_details": coordinator.daily_area_details(serial_number),
            "mowing_minutes_today": coordinator.mowing_minutes_today(
                serial_number
            ),
        }
        # Key by position, not serial number, so the identifier never leaks.
        devices[f"mower_{index + 1}"] = sections

    return async_redact_data(
        {
            "entry": dict(entry.data),
            "devices": devices,
        },
        TO_REDACT,
    )
