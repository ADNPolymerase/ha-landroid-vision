"""Tests for the mower heading drawn on the RTK map."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

COMPONENT = Path(__file__).parents[1] / "custom_components" / "worx_vision_cloud"

HOMEASSISTANT = ModuleType("homeassistant")
HOMEASSISTANT_UTIL = ModuleType("homeassistant.util")
HOMEASSISTANT_UTIL.slugify = lambda value: str(value).lower().replace(" ", "_")
HOMEASSISTANT.util = HOMEASSISTANT_UTIL
sys.modules.setdefault("homeassistant", HOMEASSISTANT)
sys.modules.setdefault("homeassistant.util", HOMEASSISTANT_UTIL)

SPEC = importlib.util.spec_from_file_location(
    "worx_helpers_heading", COMPONENT / "helpers.py"
)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)

CAMERA_SOURCE = (COMPONENT / "camera.py").read_text(encoding="utf-8")
CAMERA_TREE = ast.parse(CAMERA_SOURCE)


def _camera_function(name: str):
    for node in CAMERA_TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            namespace: dict = {}
            exec(compile(ast.Module(body=[node], type_ignores=[]), "camera.py", "exec"), namespace)
            return namespace[name]
    raise AssertionError(f"{name} not found in camera.py")


ROBOT_SVG = _camera_function("_robot_svg")


def _device(yaw):
    return SimpleNamespace(orientation={"pitch": 1.0, "roll": 2.0, "yaw": yaw})


class HeadingTests(unittest.TestCase):
    # Yaw values read on a live Vision Cloud mowing parallel lanes, and the
    # bearing of the same lanes measured on its north-up RTK map.
    def test_front_lanes(self):
        self.assertEqual(HELPERS.rtk_heading(_device(73.0)), 17.0)

    def test_front_lanes_way_back(self):
        self.assertEqual(HELPERS.rtk_heading(_device(-107.0)), 197.0)

    def test_back_lanes(self):
        self.assertEqual(HELPERS.rtk_heading(_device(45.0)), 45.0)

    def test_back_lanes_way_back(self):
        self.assertEqual(HELPERS.rtk_heading(_device(-135.0)), 225.0)

    def test_stays_within_a_turn(self):
        # A yaw past 90 degrees would give a negative bearing without wrapping.
        self.assertEqual(HELPERS.rtk_heading(_device(169.6)), 280.4)

    def test_east_is_ninety(self):
        self.assertEqual(HELPERS.rtk_heading(_device(0)), 90.0)

    def test_text_value(self):
        self.assertEqual(HELPERS.rtk_heading(_device("-18.7")), 108.7)

    def test_unusable_values(self):
        for value in (None, "", "abc", True, float("nan"), float("inf"), 720):
            with self.subTest(value=value):
                self.assertIsNone(HELPERS.rtk_heading(_device(value)))

    def test_no_orientation(self):
        self.assertIsNone(HELPERS.rtk_heading(SimpleNamespace()))
        self.assertIsNone(HELPERS.rtk_heading(SimpleNamespace(orientation=None)))


class RobotMarkerTests(unittest.TestCase):
    def test_rotated_to_the_heading(self):
        svg = ROBOT_SVG(100.0, 200.0, 17.0)
        self.assertIn('translate(100.00 200.00)', svg)
        self.assertIn('rotate(17.0)', svg)
        self.assertIn('class="nose"', svg)

    def test_nose_points_north_before_rotation(self):
        # SVG y grows downwards: the nose must sit at negative y, so that
        # rotate(heading) turns it clockwise from north.
        svg = ROBOT_SVG(0.0, 0.0, 0.0)
        nose = svg.split('class="nose" d="', 1)[1].split('"', 1)[0]
        ys = [float(v) for v in nose.replace("M", " ").replace("L", " ").replace("Z", " ").split()[1::2]]
        self.assertLess(max(ys), 0)

    def test_shadow_does_not_turn(self):
        svg = ROBOT_SVG(0.0, 0.0, 90.0)
        self.assertLess(svg.index("robot-shadow"), svg.index("rotate("))

    def test_without_heading_the_marker_is_unchanged(self):
        svg = ROBOT_SVG(1.0, 2.0, None)
        self.assertNotIn("rotate(", svg)
        self.assertNotIn('class="nose"', svg)
        self.assertTrue(svg.startswith('<g class="robot" transform="translate(1.00 2.00) scale(0.68)">'))

    def test_heading_reaches_the_map(self):
        self.assertIn("body.append(_robot_svg(x, y, heading))", CAMERA_SOURCE)
        self.assertIn("rtk_heading(self.device),", CAMERA_SOURCE)


if __name__ == "__main__":
    unittest.main()
