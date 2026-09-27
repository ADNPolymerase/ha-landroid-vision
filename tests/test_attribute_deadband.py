"""Tests for the deadband that stops readings wobbling at rest from being stored.

Docked, the mower's RTK position and distance to the station, and the radio
RSSI, change by a few centimetres or dBm on every report. Each change used to
store a new row. The coordinates below are made up.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest

HOMEASSISTANT = ModuleType("homeassistant")
HOMEASSISTANT_UTIL = ModuleType("homeassistant.util")
HOMEASSISTANT_UTIL.slugify = lambda value: str(value).lower().replace(" ", "_")
HOMEASSISTANT.util = HOMEASSISTANT_UTIL
sys.modules.setdefault("homeassistant", HOMEASSISTANT)
sys.modules.setdefault("homeassistant.util", HOMEASSISTANT_UTIL)

COMPONENT = Path(__file__).parents[1] / "custom_components" / "worx_vision_cloud"
SPEC = importlib.util.spec_from_file_location(
    "worx_helpers_deadband_under_test", COMPONENT / "helpers.py"
)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)

hold = HELPERS.hold_small_attribute_changes
DISTANCE = {"rtk_station_distance_m": HELPERS.STATION_DISTANCE_DEADBAND_M}
RSSI = {"_rssi": HELPERS.RSSI_DEADBAND_DB}
BASE_LAT = 47.1
BASE_LON = 3.2


def _docked(distance: float, dlat: float = 0.0, dlon: float = 0.0) -> dict:
    return {
        "status_id": 1,
        "error_id": 0,
        "rtk_at_station": True,
        "battery_percent": 100,
        "rtk_station_distance_m": distance,
        "latitude": BASE_LAT + dlat,
        "longitude": BASE_LON + dlon,
    }


def _publish(reports: list[dict], **kwargs) -> list[dict]:
    published = None
    out = []
    for report in reports:
        published = hold(published, report, **kwargs)
        out.append(published)
    return out


def _changes(published: list[dict]) -> int:
    return sum(1 for a, b in zip(published, published[1:]) if a != b)


class DockedWobbleTest(unittest.TestCase):
    def test_docked_wobble_is_not_published(self) -> None:
        # The spread seen at rest: 0.29 to 0.57 m, and about 1e-6 degree.
        distances = [0.54, 0.55, 0.54, 0.52, 0.56, 0.57, 0.44, 0.29, 0.38, 0.57]
        reports = [
            _docked(d, dlat=(i % 3 - 1) * 1.2e-6, dlon=(i % 2) * 1.5e-6)
            for i, d in enumerate(distances)
        ]
        published = _publish(
            reports,
            deadbands=DISTANCE,
            position_deadband_m=HELPERS.POSITION_DEADBAND_M,
            refresh_keys=("status_id", "error_id", "rtk_at_station"),
        )
        self.assertEqual(_changes(published), 0)
        self.assertEqual(published[-1], reports[0])

    def test_a_real_move_is_published(self) -> None:
        # About 2 m north, well beyond the deadband.
        reports = [_docked(0.5), _docked(2.5, dlat=2e-5)]
        published = _publish(
            reports,
            deadbands=DISTANCE,
            position_deadband_m=HELPERS.POSITION_DEADBAND_M,
        )
        self.assertEqual(published[1], reports[1])

    def test_small_steps_add_up_against_the_published_value(self) -> None:
        # Four 0.2 m steps: held until 0.5 m from what was last published.
        reports = [_docked(d) for d in (1.0, 1.2, 1.4, 1.6, 1.8)]
        published = _publish(reports, deadbands=DISTANCE)
        values = [p["rtk_station_distance_m"] for p in published]
        self.assertEqual(values, [1.0, 1.0, 1.0, 1.6, 1.6])

    def test_other_attributes_still_change(self) -> None:
        first = _docked(0.54)
        second = {**_docked(0.55), "battery_percent": 99}
        result = hold(hold(None, first, DISTANCE), second, DISTANCE)
        self.assertEqual(result["battery_percent"], 99)
        self.assertEqual(result["rtk_station_distance_m"], 0.54)


class RefreshKeysTest(unittest.TestCase):
    def test_a_status_change_publishes_fresh_values(self) -> None:
        first = _docked(0.54)
        leaving = {**_docked(0.60, dlat=1e-6), "status_id": 3}
        result = hold(
            hold(None, first, DISTANCE),
            leaving,
            DISTANCE,
            position_deadband_m=0.5,
            refresh_keys=("status_id",),
        )
        self.assertEqual(result, leaving)

    def test_leaving_the_station_is_never_shown_with_a_held_distance(self) -> None:
        near = {**_docked(2.3), "rtk_at_station": True}
        out = {**_docked(2.6), "rtk_at_station": False}
        result = hold(
            hold(None, near, DISTANCE),
            out,
            DISTANCE,
            refresh_keys=("rtk_at_station",),
        )
        self.assertEqual(result["rtk_station_distance_m"], 2.6)


class RssiTest(unittest.TestCase):
    def test_rssi_suffixes_are_held_within_3_db(self) -> None:
        first = {"robot_wifi_rssi": -53, "connection_1_rssi": -34, "connection_1_wifi_rssi": -48}
        second = {"robot_wifi_rssi": -55, "connection_1_rssi": -32, "connection_1_wifi_rssi": -47}
        third = {"robot_wifi_rssi": -57, "connection_1_rssi": -32, "connection_1_wifi_rssi": -47}
        published = _publish([first, second, third], deadbands=RSSI)
        self.assertEqual(published[1], first)
        self.assertEqual(published[2]["robot_wifi_rssi"], -57)
        self.assertEqual(published[2]["connection_1_rssi"], -34)


class EdgeCasesTest(unittest.TestCase):
    def test_first_report_is_published_as_is(self) -> None:
        report = _docked(0.5)
        self.assertEqual(hold(None, report, DISTANCE), report)
        self.assertIsNot(hold(None, report, DISTANCE), report)

    def test_non_numbers_and_booleans_are_never_held(self) -> None:
        first = {"a_rssi": True, "b_rssi": "weak", "c_rssi": None}
        second = {"a_rssi": False, "b_rssi": "good", "c_rssi": -40}
        self.assertEqual(hold(first, second, RSSI), second)

    def test_a_vanished_position_is_not_brought_back(self) -> None:
        first = _docked(0.5)
        second = {k: v for k, v in _docked(0.5).items() if k not in ("latitude", "longitude")}
        result = hold(first, second, DISTANCE, position_deadband_m=0.5)
        self.assertNotIn("latitude", result)
        self.assertNotIn("longitude", result)


if __name__ == "__main__":
    unittest.main()
