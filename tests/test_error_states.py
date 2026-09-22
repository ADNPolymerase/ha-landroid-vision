"""Tests for the mower error sensor mapping."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import unittest

COMPONENT = Path(__file__).parents[1] / "custom_components" / "worx_vision_cloud"
TREE = ast.parse((COMPONENT / "sensor.py").read_text(encoding="utf-8"))


def _assigned(name: str) -> Any:
    for node in TREE.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in sensor.py")


def _function(name: str, namespace: dict[str, Any]) -> Any:
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            module = ast.Module(body=[node], type_ignores=[])
            exec(compile(module, "sensor.py", "exec"), namespace)
            return namespace[name]
    raise AssertionError(f"{name} not found in sensor.py")


KEYS = _assigned("ERROR_STATE_KEYS")
OTHER = _assigned("OTHER_ERROR")
OPTIONS = [*KEYS.values(), OTHER]


def _error(device: Any, key: str, default: Any = None) -> Any:
    return device.error.get(key, default)


ERROR_STATE = _function(
    "_error_state",
    {"_error": _error, "ERROR_STATE_KEYS": KEYS, "OTHER_ERROR": OTHER},
)


def _device(error_id: Any, description: str = "unknown") -> SimpleNamespace:
    return SimpleNamespace(error={"id": error_id, "description": description})


class ErrorStateTests(unittest.TestCase):
    def test_lifted_is_named(self) -> None:
        # The case that read unknown on a live mower.
        self.assertEqual(ERROR_STATE(_device(2, "lifted")), "lifted")

    def test_camera_error_is_named(self) -> None:
        self.assertEqual(ERROR_STATE(_device(110, "camera error")), "camera_error")

    def test_no_error(self) -> None:
        self.assertEqual(ERROR_STATE(_device(0, "no error")), "no_error")

    def test_id_wins_over_an_unknown_description(self) -> None:
        # pyworxcloud describes ids it does not know as "unknown".
        self.assertEqual(ERROR_STATE(_device(117)), "unsupported_blade_height")

    def test_unlisted_id_is_other_error(self) -> None:
        self.assertEqual(ERROR_STATE(_device(250)), OTHER)

    def test_placeholder_and_garbage_give_none(self) -> None:
        self.assertIsNone(ERROR_STATE(_device(-1)))
        self.assertIsNone(ERROR_STATE(_device(None)))
        self.assertIsNone(ERROR_STATE(_device("x")))

    def test_keys_are_unique(self) -> None:
        self.assertEqual(len(set(OPTIONS)), len(OPTIONS))

    def test_every_language_labels_every_error(self) -> None:
        for path in sorted((COMPONENT / "translations").glob("*.json")):
            states = json.loads(path.read_text(encoding="utf-8"))["entity"]["sensor"]["error"]["state"]
            self.assertEqual(set(states), set(OPTIONS), path.name)
            self.assertTrue(all(states.values()), path.name)


if __name__ == "__main__":
    unittest.main()
