"""Tests for the stopped-away-from-base detection and transit zones."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import unittest


HOMEASSISTANT = ModuleType("homeassistant")
HOMEASSISTANT_UTIL = ModuleType("homeassistant.util")
HOMEASSISTANT_UTIL.slugify = lambda value: str(value).lower().replace(" ", "_")
HOMEASSISTANT.util = HOMEASSISTANT_UTIL
sys.modules.setdefault("homeassistant", HOMEASSISTANT)
sys.modules.setdefault("homeassistant.util", HOMEASSISTANT_UTIL)

MODULE_PATH = (
    Path(__file__).parents[1] / "custom_components" / "worx_vision_cloud" / "helpers.py"
)
SPEC = importlib.util.spec_from_file_location(
    "worx_helpers_stopped_under_test", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)

STATION = (10.0, 20.0)
METRE_IN_DEGREES = 1 / 110_540


def _mower(
    *,
    status_id: int | None = 0,
    charging: bool | None = False,
    metres_from_station: float | None = 5.0,
    error: str = "no error",
) -> SimpleNamespace:
    """Return a mower-like object for the stopped detection."""
    raw_dat: dict = {}
    map_data: dict = {}
    if metres_from_station is not None:
        raw_dat = {
            "rtk": {
                "pos": [
                    STATION[0] + metres_from_station * METRE_IN_DEGREES,
                    STATION[1],
                ]
            }
        }
        map_data = {
            "layers": {
                "markers": [
                    {"record": {"latitude": STATION[0], "longitude": STATION[1]}}
                ]
            }
        }
    return SimpleNamespace(
        status={"id": status_id},
        battery={"charging": charging},
        error={"description": error},
        raw_dat=raw_dat,
        _worx_vision_rtk_map=map_data,
    )


class StoppedAwayFromBaseTests(unittest.TestCase):
    """Exercise the conditions behind the stopped repair issue."""

    def test_stopped_in_the_field_not_charging(self) -> None:
        self.assertTrue(HELPERS.is_stopped_away_from_base(_mower()))

    def test_stuck_close_to_the_station_still_counts(self) -> None:
        # A mower wedged under a shelter 2.1 m from the station passed the
        # 2.5 m rtk_at_station check, so the alert must not rely on it.
        self.assertTrue(
            HELPERS.is_stopped_away_from_base(_mower(metres_from_station=2.1))
        )

    def test_on_the_base_does_not_count(self) -> None:
        self.assertFalse(
            HELPERS.is_stopped_away_from_base(_mower(metres_from_station=0.5))
        )

    def test_charging_does_not_count(self) -> None:
        self.assertFalse(HELPERS.is_stopped_away_from_base(_mower(charging=True)))

    def test_other_statuses_do_not_count(self) -> None:
        for status_id in (1, 7, 30, 33, 34, None):
            with self.subTest(status_id=status_id):
                self.assertFalse(
                    HELPERS.is_stopped_away_from_base(_mower(status_id=status_id))
                )

    def test_rain_delay_does_not_count(self) -> None:
        self.assertFalse(
            HELPERS.is_stopped_away_from_base(_mower(error="rain_delay"))
        )

    def test_unknown_position_still_counts(self) -> None:
        self.assertTrue(
            HELPERS.is_stopped_away_from_base(_mower(metres_from_station=None))
        )

    def test_status_zero_is_paused(self) -> None:
        self.assertIn(0, HELPERS.PAUSED_STATUS_IDS)
        self.assertIn(0, HELPERS.STOPPED_STATUS_IDS)


class TransitZoneTests(unittest.TestCase):
    """Corridors between mowing areas are not reported as the current zone."""

    def _device(self, zones: list[dict]) -> SimpleNamespace:
        return SimpleNamespace(
            raw_dat={"rtk": {"pos": [10.005, 20.005]}},
            _worx_vision_rtk_map={"layers": {"boundaries": [{"zones": zones}]}},
        )

    @staticmethod
    def _square(name: str, metadata: dict | None) -> dict:
        zone = {
            "name": name,
            "contours": [
                {
                    "points": [
                        [10.0, 20.0],
                        [10.0, 20.01],
                        [10.01, 20.01],
                        [10.01, 20.0],
                    ]
                }
            ],
        }
        if metadata is not None:
            zone["metadata"] = metadata
        return zone

    def test_corridor_with_empty_metadata_is_skipped(self) -> None:
        device = self._device([self._square("1", {})])
        self.assertIsNone(HELPERS.rtk_current_zone_name(device))

    def test_mowing_zone_with_cut_metadata_is_kept(self) -> None:
        device = self._device(
            [self._square("Back lawn", {"cut_type": 1, "cut_direction": 90})]
        )
        self.assertEqual(HELPERS.rtk_current_zone_name(device), "Back lawn")

    def test_zone_without_metadata_key_is_kept(self) -> None:
        device = self._device([self._square("Back lawn", None)])
        self.assertEqual(HELPERS.rtk_current_zone_name(device), "Back lawn")

    def test_mowing_zone_wins_over_overlapping_corridor(self) -> None:
        device = self._device(
            [
                self._square("1", {}),
                self._square("Back lawn", {"cut_type": 1}),
            ]
        )
        self.assertEqual(HELPERS.rtk_current_zone_name(device), "Back lawn")


if __name__ == "__main__":
    unittest.main()
