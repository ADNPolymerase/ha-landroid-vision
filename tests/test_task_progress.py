"""Tests for the current task progress read from the mower's task list.

The garden, its zone names and areas are made up. The figures of the first
test mirror a reading made against the Worx app: 86 % and 262.7 m2 left on a
305.45 m2 zone, with 3 h 23 left.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

HOMEASSISTANT = ModuleType("homeassistant")
HOMEASSISTANT_UTIL = ModuleType("homeassistant.util")
HOMEASSISTANT_UTIL.slugify = lambda value: str(value).lower().replace(" ", "_")
HOMEASSISTANT.util = HOMEASSISTANT_UTIL
sys.modules.setdefault("homeassistant", HOMEASSISTANT)
sys.modules.setdefault("homeassistant.util", HOMEASSISTANT_UTIL)

COMPONENT = Path(__file__).parents[1] / "custom_components" / "worx_vision_cloud"
SPEC = importlib.util.spec_from_file_location(
    "worx_helpers_task_under_test", COMPONENT / "helpers.py"
)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)


def _device(tasks, *, with_map: bool = True) -> SimpleNamespace:
    zones_cfg = [
        {"id": 1, "cfg": {"cut": {"d": 30}}},
        {"id": 2, "cfg": {"cut": {"d": 120}}},
    ]
    map_data = {
        "layers": {
            "boundaries": [
                {
                    "zones": [
                        {"name": "Lawn", "area": 305_450_000, "metadata": {"cut_direction": 30}},
                        {"name": "Orchard", "area": 33_700_000, "metadata": {"cut_direction": 120}},
                        {"name": "Path", "area": 4_000_000, "metadata": {}},
                    ]
                }
            ]
        }
    }
    device = SimpleNamespace(
        raw_cfg={"rtk": {"zs": zones_cfg}},
        raw_dat={"cut": {"tsk": tasks}},
    )
    if with_map:
        device._worx_vision_rtk_map = map_data
    return device


def _task(tm: str, zones, tr: int = 1) -> dict:
    return {"id": "task-" + tm, "st": 0, "tm": tm, "tr": tr, "z": zones}


class ZoneAreasTest(unittest.TestCase):
    def test_areas_follow_the_zone_names(self) -> None:
        self.assertEqual(HELPERS.rtk_zone_areas(_device([])), {1: 305.45, 2: 33.7})

    def test_no_map_no_areas(self) -> None:
        self.assertEqual(HELPERS.rtk_zone_areas(_device([], with_map=False)), {})


class TaskProgressTest(unittest.TestCase):
    def test_matches_the_worx_app_remaining_view(self) -> None:
        device = _device(
            [_task("2026-06-01T10:00:00.000Z", [{"id": 1, "p": 14, "rtg": 12180, "rtn": 12180, "a": 7}])]
        )
        task = HELPERS.current_task_progress(device)
        zone = task["zones"][0]
        self.assertEqual(zone["name"], "Lawn")
        self.assertEqual(zone["remaining_pct"], 86)
        self.assertEqual(zone["remaining_m2"], 262.7)
        self.assertEqual(zone["remaining_time_s"], 12180)
        self.assertEqual(task["remaining_pct"], 86)
        self.assertEqual(task["trigger"], "manual")
        self.assertTrue(task["active"])
        self.assertNotIn("raw_a", zone)

    def test_a_stopped_task_is_listed_but_not_active(self) -> None:
        stopped = {**_task("2026-06-01T10:00:00.000Z", [{"id": 1, "p": 14}]), "st": 3}
        task = HELPERS.current_task_progress(_device([stopped]))
        self.assertFalse(task["active"])
        self.assertEqual(task["remaining_pct"], 86)

    def test_a_finished_task_is_not_active(self) -> None:
        done = {**_task("2026-06-01T10:00:00.000Z", [{"id": 2, "p": 100, "rtg": 0}]), "st": 2}
        task = HELPERS.current_task_progress(_device([done]))
        self.assertFalse(task["active"])
        self.assertEqual(task["remaining_pct"], 0)

    def test_remaining_share_is_weighted_by_area(self) -> None:
        device = _device(
            [
                _task(
                    "2026-06-01T10:00:00.000Z",
                    [{"id": 1, "p": 50}, {"id": 2, "p": 0}],
                    tr=2,
                )
            ]
        )
        task = HELPERS.current_task_progress(device)
        # (152.7 + 33.7) / 339.15
        self.assertEqual(task["remaining_pct"], 55.0)
        self.assertEqual(task["trigger"], "schedule")

    def test_plain_average_without_areas(self) -> None:
        device = _device(
            [_task("2026-06-01T10:00:00.000Z", [{"id": 1, "p": 50}, {"id": 2, "p": 0}])],
            with_map=False,
        )
        task = HELPERS.current_task_progress(device)
        self.assertEqual(task["remaining_pct"], 75.0)
        self.assertIsNone(task["zones"][0]["remaining_m2"])

    def test_latest_task_wins(self) -> None:
        device = _device(
            [
                _task("2026-06-01T08:00:00.000Z", [{"id": 2, "p": 90}], tr=2),
                _task("2026-06-01T12:00:00.000Z", [{"id": 1, "p": 10}]),
            ]
        )
        task = HELPERS.current_task_progress(device)
        self.assertEqual([z["id"] for z in task["zones"]], [1])
        self.assertEqual(task["task_count"], 2)

    def test_out_of_range_and_missing_values(self) -> None:
        device = _device(
            [_task("2026-06-01T10:00:00.000Z", [{"id": 1, "p": 120}, {"id": 2, "p": "x"}, {"p": 5}])]
        )
        zones = HELPERS.current_task_progress(device)["zones"]
        self.assertEqual(zones[0]["remaining_pct"], 0)
        self.assertIsNone(zones[1]["remaining_pct"])
        self.assertIsNone(zones[1]["remaining_time_s"])
        self.assertEqual(len(zones), 2)

    def test_no_task(self) -> None:
        for tasks in ([], None, "x", [{"id": "no zones"}]):
            with self.subTest(tasks=tasks):
                self.assertIsNone(HELPERS.current_task_progress(_device(tasks)))


if __name__ == "__main__":
    unittest.main()
