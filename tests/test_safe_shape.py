"""Tests for the geometry-free map shape used in diagnostics."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
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
SPEC = importlib.util.spec_from_file_location("worx_helpers_safe_shape", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)

# Fictional map: one boundary, one mowing zone, with made-up coordinates.
MAP = {
    "id": "map-id",
    "type": "shared",
    "center": [10.5, 20.5],
    "layers": {
        "boundaries": [
            {
                "id": 7,
                "type": "boundary",
                "zones": [
                    {
                        "name": "Front",
                        "summary": {"id": 1, "zone_type": 2, "latitude": 10.5},
                        "contours": [[[10.5, 20.5], [10.6, 20.6]]],
                    }
                ],
            }
        ],
        "markers": [{"position": [10.5, 20.5], "kind": "station"}],
    },
}


class SafeShapeTests(unittest.TestCase):
    def test_identifiers_are_kept(self) -> None:
        shape = HELPERS.safe_shape(MAP, depth=8)
        boundary = shape["layers"]["boundaries"][0]
        self.assertEqual(boundary["id"], 7)
        self.assertEqual(boundary["type"], "boundary")
        self.assertEqual(boundary["zones"][0]["summary"]["zone_type"], 2)
        self.assertEqual(shape["layers"]["markers"][0]["kind"], "station")

    def test_no_coordinate_survives(self) -> None:
        text = repr(HELPERS.safe_shape(MAP, depth=10))
        self.assertNotIn("10.5", text)
        self.assertNotIn("20.5", text)
        self.assertNotIn("10.6", text)

    def test_location_keys_are_redacted(self) -> None:
        shape = HELPERS.safe_shape(MAP, depth=8)
        self.assertEqual(shape["center"], "**REDACTED**")
        zone = shape["layers"]["boundaries"][0]["zones"][0]
        self.assertEqual(zone["summary"]["latitude"], "**REDACTED**")
        self.assertEqual(shape["layers"]["markers"][0]["position"], "**REDACTED**")

    def test_value_lists_become_lengths(self) -> None:
        zone = HELPERS.safe_shape(MAP, depth=8)["layers"]["boundaries"][0]["zones"][0]
        self.assertEqual(zone["contours"], "<list len=1>")

    def test_depth_limit_keeps_only_keys(self) -> None:
        self.assertEqual(
            HELPERS.safe_shape({"a": {"b": 1, "c": 2}}, depth=1),
            {"a": "<dict keys=['b', 'c']>"},
        )


if __name__ == "__main__":
    unittest.main()
