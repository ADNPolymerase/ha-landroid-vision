"""Tests for the maintenance status sensor."""

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


def _functions(names: list[str], namespace: dict[str, Any]) -> dict[str, Any]:
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            module = ast.Module(body=[node], type_ignores=[])
            exec(compile(module, "sensor.py", "exec"), namespace)
    return namespace


OPTIONS = _assigned("MAINTENANCE_STATE_OPTIONS")


def _since_reset(device: Any, total_key: str, reset_key: str) -> int | None:
    return device.counters.get(total_key)


NS = _functions(
    ["_service_due", "_maintenance_state"],
    {
        "_since_reset": _since_reset,
        "_blade_threshold_minutes": lambda device: 6000,
        "_battery_threshold_cycles": lambda device: 800,
    },
)
STATE = NS["_maintenance_state"]


def _device(blade: int | None, battery: int | None) -> SimpleNamespace:
    return SimpleNamespace(
        counters={"blade_work_time": blade, "battery_charge_cycles": battery}
    )


class MaintenanceStateTests(unittest.TestCase):
    def test_nothing_due(self) -> None:
        self.assertEqual(STATE(_device(100, 10)), "ok")

    def test_blade_only(self) -> None:
        self.assertEqual(STATE(_device(6000, 10)), "blade_service_due")

    def test_battery_only(self) -> None:
        self.assertEqual(STATE(_device(100, 800)), "battery_service_due")

    def test_blade_does_not_hide_battery(self) -> None:
        self.assertEqual(
            STATE(_device(6000, 800)), "blade_and_battery_service_due"
        )

    def test_unknown_counters(self) -> None:
        self.assertIsNone(STATE(_device(None, None)))
        self.assertEqual(STATE(_device(None, 800)), "battery_service_due")

    def test_every_state_is_translated(self) -> None:
        for path in sorted((COMPONENT / "translations").glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            states = data["entity"]["sensor"]["maintenance_status"]["state"]
            with self.subTest(language=path.stem):
                self.assertEqual(set(states), set(OPTIONS))


if __name__ == "__main__":
    unittest.main()
