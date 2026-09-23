"""Tests for RTK current-zone detection."""

from __future__ import annotations

import datetime as dt

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
    "worx_helpers_rtk_under_test", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)


def _device(position: list[float]) -> SimpleNamespace:
    """Return a mower-like object with RTK position and map geometry."""
    return SimpleNamespace(
        raw_dat={"rtk": {"pos": position}},
        _worx_vision_rtk_map={
            "layers": {
                "boundaries": [
                    {
                        "zones": [
                            {
                                "id": 1,
                                "name": "Front lawn",
                                "contours": [
                                    {
                                        "points": [
                                            [52.0000, 20.0000],
                                            [52.0000, 20.0100],
                                            [52.0100, 20.0100],
                                            [52.0100, 20.0000],
                                        ],
                                        "children": [
                                            {
                                                "points": [
                                                    [52.0040, 20.0040],
                                                    [52.0040, 20.0060],
                                                    [52.0060, 20.0060],
                                                    [52.0060, 20.0040],
                                                ],
                                            }
                                        ],
                                    }
                                ],
                            },
                            {
                                "id": 2,
                                "contours": [
                                    {
                                        "points": [
                                            [52.0200, 20.0200],
                                            [52.0200, 20.0300],
                                            [52.0300, 20.0300],
                                            [52.0300, 20.0200],
                                        ],
                                    }
                                ],
                            },
                        ]
                    }
                ]
            }
        },
    )


class RtkCurrentZoneTests(unittest.TestCase):
    """Exercise current-zone geometry lookup."""

    def test_current_zone_name_uses_zone_containing_position(self) -> None:
        self.assertEqual(
            HELPERS.rtk_current_zone_name(_device([52.002, 20.002])),
            "Front lawn",
        )

    def test_current_zone_ignores_hole_children(self) -> None:
        self.assertIsNone(HELPERS.rtk_current_zone_name(_device([52.005, 20.005])))

    def test_current_zone_falls_back_to_zone_id_when_name_missing(self) -> None:
        self.assertEqual(
            HELPERS.rtk_current_zone_name(_device([52.022, 20.022])), "Zone 2"
        )

    def test_current_zone_returns_none_without_map_or_position(self) -> None:
        self.assertIsNone(
            HELPERS.rtk_current_zone_name(
                SimpleNamespace(raw_dat={}, _worx_vision_rtk_map={})
            )
        )


if __name__ == "__main__":
    unittest.main()


class ZoneSmoothingTests(unittest.TestCase):
    """Short gaps in the RTK position keep the last known zone."""

    NOW = dt.datetime(2026, 9, 22, 8, 4, tzinfo=dt.UTC)

    def test_a_live_zone_passes_through(self) -> None:
        self.assertEqual(
            HELPERS.smoothed_zone_name("Back lawn", "Front lawn", self.NOW, self.NOW),
            "Back lawn",
        )

    def test_a_short_gap_holds_the_last_zone(self) -> None:
        since = self.NOW - dt.timedelta(seconds=20)
        self.assertEqual(
            HELPERS.smoothed_zone_name(None, "Back lawn", since, self.NOW), "Back lawn"
        )

    def test_a_long_gap_gives_up(self) -> None:
        since = self.NOW - dt.timedelta(seconds=31)
        self.assertIsNone(
            HELPERS.smoothed_zone_name(None, "Back lawn", since, self.NOW)
        )

    def test_the_grace_boundary_is_not_held(self) -> None:
        since = self.NOW - dt.timedelta(seconds=HELPERS.ZONE_SMOOTHING_SECONDS)
        self.assertIsNone(
            HELPERS.smoothed_zone_name(None, "Back lawn", since, self.NOW)
        )

    def test_the_grace_is_thirty_seconds(self) -> None:
        # A trip between two areas lasts minutes, so the hold stays short.
        self.assertEqual(HELPERS.ZONE_SMOOTHING_SECONDS, 30)

    def test_nothing_known_stays_unknown(self) -> None:
        self.assertIsNone(HELPERS.smoothed_zone_name(None, None, self.NOW, self.NOW))
        self.assertIsNone(
            HELPERS.smoothed_zone_name(None, "Back lawn", None, self.NOW)
        )
