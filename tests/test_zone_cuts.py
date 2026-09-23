"""Tests for each RTK zone's mowing pattern and angle, read only."""

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
SPEC = importlib.util.spec_from_file_location("worx_helpers_zone_cuts", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)


def _map_zone(name: str, direction: int | None) -> dict:
    metadata = {} if direction is None else {"cut_type": 1, "cut_direction": direction}
    return {"name": name, "metadata": metadata}


def _device(zones: list[dict], map_zones: list[dict]) -> SimpleNamespace:
    """Fictional mower: zone configs in cfg.rtk.zs, names on the map."""
    return SimpleNamespace(
        raw_cfg={"rtk": {"map": "map-id", "zs": zones}},
        _worx_vision_rtk_map={"layers": {"boundaries": [{"zones": map_zones}]}},
    )


DEVICE = _device(
    [
        {"id": 1, "cfg": {"cut": {"t": 1, "d": 120}}},
        {"id": 2, "cfg": {"cut": {"t": 4, "d": 45}}},
        {"id": 3, "cfg": {"cut": {"t": 0}}},
    ],
    [
        _map_zone("Front lawn", 120),
        _map_zone("Corridor", None),
        _map_zone("Back lawn", 45),
        _map_zone("Side lawn", 0),
    ],
)


class ZoneCutsTests(unittest.TestCase):
    def test_pattern_and_angle_per_zone(self) -> None:
        cuts = HELPERS.rtk_zone_cuts(DEVICE)
        self.assertEqual(cuts[1]["pattern"], "parallel")
        self.assertEqual(cuts[1]["direction"], 120)
        self.assertEqual(cuts[2]["pattern"], "diamond")
        self.assertEqual(cuts[2]["direction"], 45)
        self.assertEqual(cuts[3]["pattern"], "natural")
        self.assertIsNone(cuts[3]["direction"])

    def test_zones_are_named_from_the_map(self) -> None:
        cuts = HELPERS.rtk_zone_cuts(DEVICE)
        self.assertEqual(cuts[1]["name"], "Front lawn")
        self.assertEqual(cuts[2]["name"], "Back lawn")

    def test_every_known_code_is_named(self) -> None:
        for code, name in ((0, "natural"), (1, "parallel"), (4, "diamond"), (5, "checker")):
            device = _device([{"id": 1, "cfg": {"cut": {"t": code, "d": 10}}}], [])
            self.assertEqual(HELPERS.rtk_zone_cuts(device)[1]["pattern"], name)

    def test_unknown_code_reads_other_and_keeps_the_code(self) -> None:
        device = _device([{"id": 1, "cfg": {"cut": {"t": 7, "d": 10}}}], [])
        cut = HELPERS.rtk_zone_cuts(device)[1]
        self.assertEqual(cut["pattern"], "other")
        self.assertEqual(cut["pattern_code"], 7)
        self.assertIn("other", HELPERS.ZONE_CUT_PATTERN_OPTIONS)

    def test_angle_is_kept_within_a_turn(self) -> None:
        device = _device([{"id": 1, "cfg": {"cut": {"t": 1, "d": 360}}}], [])
        self.assertEqual(HELPERS.rtk_zone_cuts(device)[1]["direction"], 0)

    def test_missing_or_bad_values_are_none(self) -> None:
        device = _device(
            [{"id": 1, "cfg": {"cut": {"t": "x", "d": "y"}}}, {"id": 2}, {"id": 0}], []
        )
        cuts = HELPERS.rtk_zone_cuts(device)
        self.assertEqual(sorted(cuts), [1, 2])
        self.assertIsNone(cuts[1]["pattern"])
        self.assertIsNone(cuts[1]["direction"])
        self.assertIsNone(cuts[2]["pattern"])


if __name__ == "__main__":
    unittest.main()
