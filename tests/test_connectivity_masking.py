"""Tests for connectivity short-drop masking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
SPEC = importlib.util.spec_from_file_location(
    "worx_helpers_connectivity_under_test", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)

NOW = datetime(2026, 7, 28, 12, 0, 0, tzinfo=UTC)


class MaskedConnectivityTests(unittest.TestCase):
    """Exercise the grace-period behavior of masked_connectivity."""

    def test_connected_passes_through(self) -> None:
        self.assertTrue(HELPERS.masked_connectivity(True, None, 30, NOW))

    def test_unknown_passes_through(self) -> None:
        self.assertIsNone(HELPERS.masked_connectivity(None, None, 30, NOW))

    def test_short_drop_is_masked(self) -> None:
        since = NOW - timedelta(minutes=10)
        self.assertTrue(HELPERS.masked_connectivity(False, since, 30, NOW))

    def test_long_drop_is_reported(self) -> None:
        since = NOW - timedelta(minutes=31)
        self.assertFalse(HELPERS.masked_connectivity(False, since, 30, NOW))

    def test_drop_exactly_at_grace_is_reported(self) -> None:
        since = NOW - timedelta(minutes=30)
        self.assertFalse(HELPERS.masked_connectivity(False, since, 30, NOW))

    def test_zero_grace_reports_live(self) -> None:
        since = NOW - timedelta(seconds=1)
        self.assertFalse(HELPERS.masked_connectivity(False, since, 0, NOW))

    def test_missing_timestamp_reports_disconnected(self) -> None:
        self.assertFalse(HELPERS.masked_connectivity(False, None, 30, NOW))


if __name__ == "__main__":
    unittest.main()
