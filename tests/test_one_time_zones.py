"""Tests for the one-time mowing cut config and the mower status mapping."""

from __future__ import annotations

import ast
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

COMPONENT = Path(__file__).parents[1] / "custom_components" / "worx_vision_cloud"
SPEC = importlib.util.spec_from_file_location(
    "worx_helpers_onetime_under_test", COMPONENT / "helpers.py"
)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)


class OneTimeCutConfigTests(unittest.TestCase):
    """The cut block has to look like the one the Worx app writes."""

    def test_a_zone_selection_is_marked_as_deliberate(self) -> None:
        # zo=1 is the app's "Special" mode. Without it the firmware reads the
        # job as "Auto" and mows the whole lawn whatever z says.
        self.assertEqual(
            HELPERS.one_time_cut_config(False, [2]),
            {"b": 0, "ob": 0, "z": [2], "zo": 1},
        )

    def test_no_zone_selection_is_marked_as_auto(self) -> None:
        self.assertEqual(
            HELPERS.one_time_cut_config(False, []),
            {"b": 0, "ob": 0, "z": [], "zo": 0},
        )

    def test_missing_zone_list_is_marked_as_auto(self) -> None:
        self.assertEqual(
            HELPERS.one_time_cut_config(False, None),
            {"b": 0, "ob": 0, "z": [], "zo": 0},
        )

    def test_the_over_border_field_follows_the_edge_cut_flag(self) -> None:
        # Observed on three dumps of the same mower: a slot with b=1 never
        # carries ob, a slot with b=0 always carries ob=0. A block with b=0
        # and no ob is a shape the Worx app never writes.
        self.assertEqual(HELPERS.one_time_cut_config(False, [2])["ob"], 0)
        self.assertNotIn("ob", HELPERS.one_time_cut_config(True, [2]))

    def test_the_block_matches_the_shape_the_app_writes(self) -> None:
        # Key order included, so a diff against a captured slot reads clean.
        self.assertEqual(
            list(HELPERS.one_time_cut_config(False, [2]).items()),
            [("b", 0), ("ob", 0), ("z", [2]), ("zo", 1)],
        )
        self.assertEqual(
            list(HELPERS.one_time_cut_config(True, [1, 2]).items()),
            [("b", 1), ("z", [1, 2]), ("zo", 1)],
        )

    def test_edge_cut_is_an_integer_flag(self) -> None:
        self.assertEqual(HELPERS.one_time_cut_config(True, [])["b"], 1)
        self.assertEqual(HELPERS.one_time_cut_config(False, [])["b"], 0)

    def test_the_zone_order_is_preserved(self) -> None:
        # z is an ordered list in the app's Special mode, so the caller's
        # order has to survive untouched.
        self.assertEqual(HELPERS.one_time_cut_config(False, [2, 1])["z"], [2, 1])
        self.assertEqual(HELPERS.one_time_cut_config(False, [1, 2])["z"], [1, 2])

    def test_the_caller_list_is_not_aliased(self) -> None:
        zones = [1, 2]
        config = HELPERS.one_time_cut_config(False, zones)
        config["z"].append(3)
        self.assertEqual(zones, [1, 2])


def _sensor_mapping(name: str) -> dict[str, str] | list[str]:
    """Return a literal mapping or list declared at the top of sensor.py."""
    tree = ast.parse((COMPONENT / "sensor.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            continue
        return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in sensor.py")


class StatusMappingTests(unittest.TestCase):
    """Statuses a Vision mower reports must not fall through to unknown."""

    def setUp(self) -> None:
        self.keys = _sensor_mapping("STATUS_STATE_KEYS")
        self.options = _sensor_mapping("STATUS_STATE_OPTIONS")

    def test_rtk_statuses_are_mapped(self) -> None:
        # Descriptions come from pyworxcloud: 103 searching zone, 5 and 104
        # searching home, 31 zoning, 110 border crossing, 111 exploring lawn.
        for description in (
            "searching zone",
            "searching home",
            "zoning",
            "border crossing",
            "exploring lawn",
        ):
            with self.subTest(description=description):
                self.assertIn(description, self.keys)

    def test_every_mapped_state_is_an_exposed_option(self) -> None:
        # An enum sensor writing a state outside its options list is dropped
        # by Home Assistant, so the two have to stay in step.
        for state in set(self.keys.values()):
            with self.subTest(state=state):
                self.assertIn(state, self.options)

    def test_options_have_no_duplicates(self) -> None:
        self.assertEqual(len(self.options), len(set(self.options)))


class StatusTranslationTests(unittest.TestCase):
    """Every exposed status option needs a label in every language."""

    def test_all_languages_cover_all_options(self) -> None:
        import json

        options = set(_sensor_mapping("STATUS_STATE_OPTIONS"))
        for path in sorted((COMPONENT / "translations").glob("*.json")):
            with self.subTest(language=path.stem):
                states = json.loads(path.read_text(encoding="utf-8"))["entity"][
                    "sensor"
                ]["status"]["state"]
                self.assertEqual(options - set(states), set())


if __name__ == "__main__":
    unittest.main()
