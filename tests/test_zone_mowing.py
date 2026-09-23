"""Tests for the command that starts a one-time job on RTK zones."""

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
SPEC = importlib.util.spec_from_file_location("worx_helpers_zone_mowing", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)

# Fictional map with three zones, listed out of order on purpose.
DEVICE = SimpleNamespace(
    raw_cfg={
        "rtk": {
            "map": "map-id",
            "zs": [
                {"id": 3, "cfg": {"cut": {}}},
                {"id": 1, "cfg": {"cut": {}}},
                {"id": 2, "cfg": {"cut": {}}},
            ],
        }
    }
)


class ZoneJobCommandTests(unittest.TestCase):
    def test_matches_the_command_the_app_sends(self) -> None:
        # Watched live: zone 2, order fixed, edge routine off.
        self.assertEqual(
            HELPERS.zone_job_command([2], False, True, [1, 2]),
            {"cmd": 1, "cut": {"b": 0, "z": [2], "zo": 1}},
        )

    def test_keys_come_in_the_order_the_app_writes_them(self) -> None:
        command = HELPERS.zone_job_command([2], True, True, [1, 2])
        self.assertEqual(list(command), ["cmd", "cut"])
        self.assertEqual(list(command["cut"]), ["b", "z", "zo"])

    def test_no_duration_travels_with_it(self) -> None:
        command = HELPERS.zone_job_command([2], False, True)
        self.assertNotIn("sc", command)
        self.assertNotIn("time", command["cut"])

    def test_edge_routine_is_an_integer_flag(self) -> None:
        self.assertEqual(HELPERS.zone_job_command([1], True, True)["cut"]["b"], 1)
        self.assertEqual(HELPERS.zone_job_command([1], False, True)["cut"]["b"], 0)
        self.assertEqual(HELPERS.zone_job_command([1], "yes", True)["cut"]["b"], 1)

    def test_the_given_order_is_kept(self) -> None:
        self.assertEqual(HELPERS.zone_job_command([2, 1], False, True)["cut"]["z"], [2, 1])

    def test_auto_order_is_zero(self) -> None:
        self.assertEqual(HELPERS.zone_job_command([2, 1], False, False)["cut"]["zo"], 0)

    def test_no_selection_sends_every_known_zone_in_auto_order(self) -> None:
        for zones in ([], None):
            with self.subTest(zones=zones):
                cut = HELPERS.zone_job_command(zones, False, True, [1, 2, 3])["cut"]
                self.assertEqual(cut["z"], [1, 2, 3])
                self.assertEqual(cut["zo"], 0)

    def test_no_selection_and_no_map_sends_an_empty_list(self) -> None:
        cut = HELPERS.zone_job_command([], False, True, [])["cut"]
        self.assertEqual(cut["z"], [])
        self.assertEqual(cut["zo"], 0)

    def test_zone_ids_are_integers(self) -> None:
        self.assertEqual(HELPERS.zone_job_command(["2"], False, True)["cut"]["z"], [2])

    def test_the_caller_list_is_not_aliased(self) -> None:
        zones = [1, 2]
        HELPERS.zone_job_command(zones, False, True)["cut"]["z"].append(3)
        self.assertEqual(zones, [1, 2])


class RtkZoneIdsTests(unittest.TestCase):
    def test_zone_ids_are_read_from_the_map_and_sorted(self) -> None:
        self.assertEqual(HELPERS.rtk_zone_ids(DEVICE), [1, 2, 3])

    def test_unusable_ids_are_skipped(self) -> None:
        device = SimpleNamespace(
            raw_cfg={"rtk": {"zs": [{"id": "x"}, {"id": 0}, {"id": 2}, {"id": 2}, "junk"]}}
        )
        self.assertEqual(HELPERS.rtk_zone_ids(device), [2])

    def test_a_mower_without_a_map_has_no_zones(self) -> None:
        self.assertEqual(HELPERS.rtk_zone_ids(SimpleNamespace(raw_cfg={})), [])
        self.assertEqual(HELPERS.rtk_zone_ids(object()), [])


if __name__ == "__main__":
    unittest.main()
