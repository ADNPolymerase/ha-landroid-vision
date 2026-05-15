"""Camera platform for Worx Vision Cloud Plus."""
from __future__ import annotations

from collections.abc import Iterable
from html import escape
from math import cos, radians
from typing import Any

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import WorxVisionEntity
from .helpers import get_dict_value, get_nested_value, rtk_map_id, rtk_position

SVG_WIDTH = 900
SVG_HEIGHT = 620
SVG_PADDING = 48


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up RTK map cameras."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime.coordinator

    async_add_entities(
        WorxVisionMapCamera(coordinator, entry, serial_number)
        for serial_number in coordinator.data
    )


class WorxVisionMapCamera(WorxVisionEntity, Camera):
    """RTK map rendered from Worx map geometry."""

    _attr_icon = "mdi:map"
    _attr_name = "Mapa RTK"

    def __init__(self, coordinator, entry, serial_number: str) -> None:
        """Initialize RTK map camera."""
        Camera.__init__(self)
        WorxVisionEntity.__init__(self, coordinator, entry, serial_number, "rtk_map_camera")
        self.content_type = "image/svg+xml"
        self._last_map_data: dict[str, Any] | None = None

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return super().available and rtk_map_id(self.device) is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return RTK map metadata."""
        map_data = self._last_map_data or {}
        zone = _first_zone(map_data)
        exclusion_count = len(get_nested_value(map_data, "layers", "exclusions", default=[]) or [])
        marker_count = len(get_nested_value(map_data, "layers", "markers", default=[]) or [])

        attrs: dict[str, Any] = {
            "map_id": rtk_map_id(self.device),
            "map_status": get_dict_value(map_data, "status"),
            "map_type": get_dict_value(map_data, "type"),
            "active": get_dict_value(map_data, "active"),
            "rtk_provider": get_dict_value(map_data, "rtk_provider"),
            "zone_name": get_dict_value(zone, "name"),
            "zone_area_m2": _scaled_area(get_dict_value(zone, "area")),
            "zone_perimeter_m": _scaled_length(get_dict_value(zone, "perimeter")),
            "exclusion_count": exclusion_count,
            "marker_count": marker_count,
        }
        return {key: value for key, value in attrs.items() if value is not None}

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return an SVG map rendered from Worx map geometry."""
        del width, height

        map_data = await self.coordinator.async_get_rtk_map(str(rtk_map_id(self.device)))
        if map_data is not None:
            self._last_map_data = map_data

        return _render_svg_map(map_data, rtk_position(self.device)).encode()


def _scaled_area(value: Any) -> float | None:
    """Return area in square meters from Worx square-millimeter values."""
    try:
        return round(float(value) / 1_000_000, 2)
    except (TypeError, ValueError):
        return None


def _scaled_length(value: Any) -> float | None:
    """Return length in meters from Worx millimeter values."""
    try:
        return round(float(value) / 1000, 2)
    except (TypeError, ValueError):
        return None


def _first_zone(map_data: dict[str, Any]) -> dict[str, Any]:
    """Return the first boundary zone from map data."""
    boundaries = get_nested_value(map_data, "layers", "boundaries", default=[]) or []
    for boundary in boundaries:
        zones = get_dict_value(boundary, "zones", []) or []
        for zone in zones:
            if isinstance(zone, dict):
                return zone
    return {}


def _point_pair(point: Any) -> tuple[float, float] | None:
    """Return latitude/longitude from a Worx point array."""
    if not isinstance(point, (list, tuple)) or len(point) < 2:
        return None
    try:
        return float(point[0]), float(point[1])
    except (TypeError, ValueError):
        return None


def _contour_points(contour: dict[str, Any]) -> list[tuple[float, float]]:
    """Return normalized points from one contour."""
    return [
        pair
        for pair in (_point_pair(point) for point in get_dict_value(contour, "points", []) or [])
        if pair is not None
    ]


def _iter_contours(map_data: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    """Yield map contours with semantic layer names."""
    boundaries = get_nested_value(map_data, "layers", "boundaries", default=[]) or []
    for boundary in boundaries:
        for zone in get_dict_value(boundary, "zones", []) or []:
            for contour in get_dict_value(zone, "contours", []) or []:
                if isinstance(contour, dict):
                    yield "zone", contour

    exclusions = get_nested_value(map_data, "layers", "exclusions", default=[]) or []
    for exclusion in exclusions:
        for contour in get_dict_value(exclusion, "contours", []) or []:
            if isinstance(contour, dict):
                yield "exclusion", contour


def _iter_bounds_points(
    map_data: dict[str, Any], robot_position: tuple[float, float] | None
) -> list[tuple[float, float]]:
    """Return all points that should influence map bounds."""
    points: list[tuple[float, float]] = []
    for _, contour in _iter_contours(map_data):
        points.extend(_contour_points(contour))
        for child in get_dict_value(contour, "children", []) or []:
            if isinstance(child, dict):
                points.extend(_contour_points(child))

    markers = get_nested_value(map_data, "layers", "markers", default=[]) or []
    for marker in markers:
        pair = _point_pair([
            get_nested_value(marker, "record", "latitude"),
            get_nested_value(marker, "record", "longitude"),
        ])
        if pair is not None:
            points.append(pair)

    if robot_position is not None:
        points.append(robot_position)

    return points


def _projector(points: list[tuple[float, float]]):
    """Build a lat/lon to SVG coordinate projector."""
    lats = [point[0] for point in points]
    lons = [point[1] for point in points]
    min_lat = min(lats)
    max_lat = max(lats)
    min_lon = min(lons)
    max_lon = max(lons)
    mean_lat = (min_lat + max_lat) / 2
    lon_scale = max(cos(radians(mean_lat)), 0.1)

    width_m = max((max_lon - min_lon) * 111_320 * lon_scale, 1)
    height_m = max((max_lat - min_lat) * 110_540, 1)
    scale = min(
        (SVG_WIDTH - SVG_PADDING * 2) / width_m,
        (SVG_HEIGHT - SVG_PADDING * 2) / height_m,
    )
    drawn_width = width_m * scale
    drawn_height = height_m * scale
    offset_x = (SVG_WIDTH - drawn_width) / 2
    offset_y = (SVG_HEIGHT - drawn_height) / 2

    def project(point: tuple[float, float]) -> tuple[float, float]:
        lat, lon = point
        x_m = (lon - min_lon) * 111_320 * lon_scale
        y_m = (max_lat - lat) * 110_540
        return offset_x + x_m * scale, offset_y + y_m * scale

    return project


def _path(points: list[tuple[float, float]], project) -> str:
    """Return SVG path data for one polygon/line."""
    if not points:
        return ""
    projected = [project(point) for point in points]
    first_x, first_y = projected[0]
    parts = [f"M {first_x:.2f} {first_y:.2f}"]
    parts.extend(f"L {x:.2f} {y:.2f}" for x, y in projected[1:])
    parts.append("Z")
    return " ".join(parts)


def _polyline(points: list[tuple[float, float]], project) -> str:
    """Return SVG polyline points."""
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in (project(point) for point in points))


def _render_svg_map(
    map_data: dict[str, Any] | None, robot_position: tuple[float, float] | None
) -> str:
    """Render map data to SVG."""
    if not isinstance(map_data, dict):
        return _placeholder_svg("Brak mapy RTK z API")

    points = _iter_bounds_points(map_data, robot_position)
    if not points:
        return _placeholder_svg("Mapa RTK nie zawiera punktow")

    project = _projector(points)
    body: list[str] = []

    for layer, contour in _iter_contours(map_data):
        outer = _contour_points(contour)
        if not outer:
            continue

        if layer == "zone":
            body.append(
                f'<path class="zone" d="{_path(outer, project)}" />'
            )
            for child in get_dict_value(contour, "children", []) or []:
                if not isinstance(child, dict):
                    continue
                child_points = _contour_points(child)
                if child_points:
                    body.append(
                        f'<path class="hole" d="{_path(child_points, project)}" />'
                    )
        else:
            body.append(
                f'<path class="exclusion" d="{_path(outer, project)}" />'
            )

    markers = get_nested_value(map_data, "layers", "markers", default=[]) or []
    for marker in markers:
        guide_points = [
            pair
            for pair in (_point_pair(point) for point in get_dict_value(marker, "guide", []) or [])
            if pair is not None
        ]
        if len(guide_points) > 1:
            body.append(
                f'<polyline class="guide" points="{_polyline(guide_points, project)}" />'
            )

    for marker in markers:
        pair = _point_pair([
            get_nested_value(marker, "record", "latitude"),
            get_nested_value(marker, "record", "longitude"),
        ])
        if pair is None:
            continue
        x, y = project(pair)
        label = escape(str(get_dict_value(marker, "name", "Stacja")))
        body.append(
            f'<g class="station" transform="translate({x:.2f} {y:.2f})">'
            '<circle r="17" />'
            '<path d="M 3 -13 L -8 2 H 0 L -4 14 L 10 -4 H 2 Z" />'
            f'<text x="0" y="32">{label}</text>'
            '</g>'
        )

    if robot_position is not None:
        x, y = project(robot_position)
        body.append(
            f'<g class="robot" transform="translate({x:.2f} {y:.2f})">'
            '<circle r="13" />'
            '<path d="M -8 5 H 8 V -5 H -8 Z M -5 -5 L -2 -11 H 2 L 5 -5" />'
            '</g>'
        )

    zone = _first_zone(map_data)
    area = _scaled_area(get_dict_value(zone, "area"))
    perimeter = _scaled_length(get_dict_value(zone, "perimeter"))
    title = escape(str(get_dict_value(zone, "name", "") or "Trawnik"))
    subtitle_parts = []
    if area is not None:
        subtitle_parts.append(f"{area:g} m2")
    if perimeter is not None:
        subtitle_parts.append(f"{perimeter:g} m")
    subtitle = escape(" | ".join(subtitle_parts))

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" '
        f'height="{SVG_HEIGHT}" viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" role="img">'
        "<style>"
        "svg{background:#101412;font-family:Inter,Segoe UI,Arial,sans-serif}"
        ".grid{stroke:#253027;stroke-width:1;opacity:.45}"
        ".zone{fill:#078a39;stroke:#ff604b;stroke-width:8;stroke-linejoin:round;stroke-linecap:round}"
        ".hole{fill:#dde1e7;stroke:#ff604b;stroke-width:6;stroke-linejoin:round;stroke-linecap:round}"
        ".exclusion{fill:#b56b3b;stroke:#c96d3f;stroke-width:4;opacity:.95}"
        ".guide{fill:none;stroke:#d48a3d;stroke-width:4;stroke-dasharray:8 10;opacity:.95}"
        ".station circle{fill:#6b350e}.station path{fill:#fff}.station text{fill:#f7efe8;font-size:16px;text-anchor:middle;font-weight:800}"
        ".robot circle{fill:#f47b20;stroke:#111;stroke-width:3}.robot path{fill:#212121;stroke:#fff;stroke-width:2;stroke-linejoin:round}"
        ".title{fill:#f8faf4;font-size:28px;font-weight:900}.subtitle{fill:#bec8bc;font-size:17px;font-weight:700}"
        "</style>"
        '<defs><pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">'
        '<path class="grid" d="M 48 0 L 0 0 0 48" /></pattern></defs>'
        f'<rect width="{SVG_WIDTH}" height="{SVG_HEIGHT}" fill="url(#grid)" />'
        f'<text class="title" x="34" y="44">{title}</text>'
        f'<text class="subtitle" x="34" y="72">{subtitle}</text>'
        f'{"".join(body)}'
        "</svg>"
    )


def _placeholder_svg(message: str) -> str:
    """Return SVG placeholder."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" '
        f'height="{SVG_HEIGHT}" viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">'
        "<rect width='100%' height='100%' fill='#101412'/>"
        f"<text x='50%' y='50%' fill='#f8faf4' font-size='28' "
        f"font-family='Inter,Segoe UI,Arial,sans-serif' text-anchor='middle'>{escape(message)}</text>"
        "</svg>"
    )
