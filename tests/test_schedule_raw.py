"""Tests for the raw schedule block exposed in diagnostics."""

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
SPEC = importlib.util.spec_from_file_location("worx_helpers_raw_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)


# Shape observed on a protocol 1 mower: two weekly slots carrying a zone list,
# plus the one-time job block. Fictional values, no real mower data.
RAW_SC = {
    "enabled": 1,
    "p": 0,
    "slots": [
        {"e": 1, "d": 1, "s": 480, "t": 270, "cfg": {"cut": {"b": 0, "z": [1]}}},
        {"e": 1, "d": 1, "s": 840, "t": 240, "cfg": {"cut": {"b": 0, "z": [2]}}},
    ],
    "once": {"time": 0, "cfg": {"cut": {"b": 0, "z": []}}},
}


def _device(raw_cfg: object = None) -> SimpleNamespace:
    """Return a mower-like object carrying a raw cfg payload."""
    device = SimpleNamespace()
    if raw_cfg is not None:
        device.raw_cfg = raw_cfg
    return device


class RawScheduleConfigTests(unittest.TestCase):
    """The raw cfg.sc block must reach diagnostics untouched."""

    def test_returns_the_block_verbatim(self) -> None:
        self.assertEqual(HELPERS.raw_schedule_config(_device({"sc": RAW_SC})), RAW_SC)

    def test_keeps_the_zone_list_of_every_slot(self) -> None:
        result = HELPERS.raw_schedule_config(_device({"sc": RAW_SC}))
        zones = [slot["cfg"]["cut"]["z"] for slot in result["slots"]]
        self.assertEqual(zones, [[1], [2]])

    def test_keeps_the_one_time_block(self) -> None:
        result = HELPERS.raw_schedule_config(_device({"sc": RAW_SC}))
        self.assertIn("once", result)
        self.assertEqual(result["once"]["cfg"]["cut"]["z"], [])

    def test_parsed_schedule_loses_the_zones_raw_keeps_them(self) -> None:
        # The regression this block exists for: pyworxcloud normalizes slots
        # down to day/start/duration/boundary, so the zones only survive raw.
        device = _device({"sc": RAW_SC})
        device.schedules = {
            "slots": [
                {"day": "monday", "start": "08:00", "duration": 270, "boundary": False},
                {"day": "monday", "start": "14:00", "duration": 240, "boundary": False},
            ]
        }
        parsed = HELPERS.schedule_slots(device)
        self.assertTrue(parsed)
        self.assertFalse(any("z" in slot or "zones" in slot for slot in parsed))
        self.assertTrue(
            all(
                slot["cfg"]["cut"]["z"]
                for slot in HELPERS.raw_schedule_config(device)["slots"]
            )
        )

    def test_missing_raw_cfg_is_empty(self) -> None:
        self.assertEqual(HELPERS.raw_schedule_config(_device()), {})

    def test_cfg_without_schedule_is_empty(self) -> None:
        self.assertEqual(HELPERS.raw_schedule_config(_device({"rtk": {}})), {})

    def test_non_dict_schedule_is_empty(self) -> None:
        for value in ([], "sc", 0, None):
            with self.subTest(value=value):
                self.assertEqual(
                    HELPERS.raw_schedule_config(_device({"sc": value})), {}
                )

    def test_non_dict_raw_cfg_is_empty(self) -> None:
        for value in ([], "cfg", 0):
            with self.subTest(value=value):
                self.assertEqual(HELPERS.raw_schedule_config(_device(value)), {})


if __name__ == "__main__":
    unittest.main()
