"""Tests for the one-time mowing options kept across restarts.

The coordinator is loaded with the Home Assistant and pyworxcloud stubs of
test_zone_job_retry, and a fake store records what would be written.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from test_zone_job_retry import COORDINATOR  # noqa: E402

TRANSLATIONS = (
    Path(__file__).parents[1]
    / "custom_components"
    / "worx_vision_cloud"
    / "translations"
)
SERIAL = "SN-TEST"


class FakeStore:
    """Keeps the last scheduled save instead of writing to disk."""

    def __init__(self) -> None:
        self.saved = None
        self.saves = 0

    def async_delay_save(self, data_func, _delay) -> None:
        self.saves += 1
        self.saved = data_func()


def _coordinator():
    coordinator = object.__new__(COORDINATOR.WorxVisionCoordinator)
    coordinator.data = {}
    coordinator._one_time_mowing_options = {}
    coordinator._one_time_mowing_store = FakeStore()
    coordinator.raise_if_updating = lambda _serial: None
    coordinator.async_set_updated_data = lambda _data: None
    return coordinator


class RestoreTest(unittest.TestCase):
    def test_valid_options_are_restored(self) -> None:
        coordinator = _coordinator()
        coordinator._restore_one_time_options(
            {SERIAL: {"runtime": 45, "edge_cut": True, "zones": [3, 1, 3]}}
        )
        self.assertEqual(coordinator.one_time_mowing_runtime(SERIAL), 45)
        self.assertTrue(coordinator.one_time_mowing_edge_cut(SERIAL))
        self.assertEqual(coordinator.one_time_mowing_zones(SERIAL), [3, 1])

    def test_runtime_is_clamped(self) -> None:
        coordinator = _coordinator()
        coordinator._restore_one_time_options(
            {"A": {"runtime": 500}, "B": {"runtime": 0}}
        )
        self.assertEqual(coordinator.one_time_mowing_runtime("A"), 120)
        self.assertEqual(coordinator.one_time_mowing_runtime("B"), 10)

    def test_missing_fields_keep_defaults(self) -> None:
        coordinator = _coordinator()
        coordinator._restore_one_time_options({SERIAL: {}})
        self.assertEqual(
            coordinator.one_time_mowing_runtime(SERIAL),
            COORDINATOR.DEFAULT_ONE_TIME_MOWING_RUNTIME,
        )
        self.assertFalse(coordinator.one_time_mowing_edge_cut(SERIAL))
        self.assertEqual(coordinator.one_time_mowing_zones(SERIAL), [])

    def test_invalid_data_is_ignored(self) -> None:
        for stored in (None, [], "text", {SERIAL: "text"}, {SERIAL: None}):
            with self.subTest(stored=stored):
                coordinator = _coordinator()
                coordinator._restore_one_time_options(stored)
                self.assertEqual(
                    coordinator.one_time_mowing_runtime(SERIAL),
                    COORDINATOR.DEFAULT_ONE_TIME_MOWING_RUNTIME,
                )

    def test_unreadable_values_do_not_raise(self) -> None:
        coordinator = _coordinator()
        coordinator._restore_one_time_options(
            {SERIAL: {"runtime": "soon", "zones": ["x"]}}
        )
        self.assertEqual(
            coordinator.one_time_mowing_runtime(SERIAL),
            COORDINATOR.DEFAULT_ONE_TIME_MOWING_RUNTIME,
        )


class SaveTest(unittest.IsolatedAsyncioTestCase):
    async def test_each_setter_schedules_a_save(self) -> None:
        coordinator = _coordinator()
        store = coordinator._one_time_mowing_store
        await coordinator.async_set_one_time_mowing_runtime(SERIAL, 30)
        await coordinator.async_set_one_time_mowing_edge_cut(SERIAL, True)
        await coordinator.async_set_one_time_mowing_zones(SERIAL, [2, 2, 5])
        self.assertEqual(store.saves, 3)
        self.assertEqual(
            store.saved, {SERIAL: {"runtime": 30, "edge_cut": True, "zones": [2, 5]}}
        )

    async def test_round_trip_through_the_store(self) -> None:
        before = _coordinator()
        await before.async_set_one_time_mowing_runtime(SERIAL, 75)
        await before.async_set_one_time_mowing_zones(SERIAL, [4])
        saved = json.loads(json.dumps(before._one_time_mowing_store.saved))

        after = _coordinator()
        after._restore_one_time_options(saved)
        self.assertEqual(after.one_time_mowing_runtime(SERIAL), 75)
        self.assertEqual(after.one_time_mowing_zones(SERIAL), [4])

    async def test_saved_data_is_a_copy(self) -> None:
        coordinator = _coordinator()
        await coordinator.async_set_one_time_mowing_zones(SERIAL, [1])
        coordinator._one_time_mowing_store.saved[SERIAL]["zones"].append(9)
        self.assertEqual(coordinator.one_time_mowing_zones(SERIAL), [1])


class ReauthTranslationsTest(unittest.TestCase):
    def test_every_language_has_the_reauth_strings(self) -> None:
        files = sorted(TRANSLATIONS.glob("*.json"))
        self.assertEqual(len(files), 11)
        for path in files:
            with self.subTest(language=path.stem):
                config = json.loads(path.read_text(encoding="utf-8"))["config"]
                step = config["step"]["reauth_confirm"]
                self.assertTrue(step["title"])
                self.assertIn("{email}", step["description"])
                self.assertTrue(step["data"]["password"])
                self.assertTrue(config["abort"]["reauth_successful"])


if __name__ == "__main__":
    unittest.main()
