"""Tests for the body accepted by the raw command service."""

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
SPEC = importlib.util.spec_from_file_location("worx_helpers_raw_command", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)

# The shape the Worx app leaves in cfg.cut when it starts a zone job.
ZONE_START = {"cmd": 1, "cut": {"b": 1, "z": [2], "zo": 1}}


class RawCommandPayloadTests(unittest.TestCase):
    def test_mapping_is_accepted_as_is(self) -> None:
        self.assertEqual(HELPERS.raw_command_payload(ZONE_START), ZONE_START)

    def test_json_text_is_accepted(self) -> None:
        text = '{"cmd": 1, "cut": {"b": 1, "z": [2], "zo": 1}}'
        self.assertEqual(HELPERS.raw_command_payload(text), ZONE_START)

    def test_result_does_not_share_nested_state(self) -> None:
        payload = HELPERS.raw_command_payload(ZONE_START)
        payload["cut"]["z"].append(1)
        self.assertEqual(ZONE_START["cut"]["z"], [2])

    def test_invalid_json_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            HELPERS.raw_command_payload('{"cmd": 1,')

    def test_non_object_is_refused(self) -> None:
        for value in ([1, 2], "[1]", 1, "1", None, "null"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                HELPERS.raw_command_payload(value)

    def test_empty_object_is_refused(self) -> None:
        for value in ({}, "{}"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                HELPERS.raw_command_payload(value)

    def test_envelope_keys_are_refused(self) -> None:
        for key in ("id", "uuid", "tm"):
            with self.subTest(key=key), self.assertRaises(ValueError) as ctx:
                HELPERS.raw_command_payload({"cmd": 1, key: "x"})
            self.assertIn(key, str(ctx.exception))

    def test_nested_envelope_names_are_left_alone(self) -> None:
        # Zone entries carry their own `id`, which is not the envelope's.
        payload = {"cmd": 1, "cut": {"z": [{"id": 2}]}}
        self.assertEqual(HELPERS.raw_command_payload(payload), payload)


if __name__ == "__main__":
    unittest.main()
