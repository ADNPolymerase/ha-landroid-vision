"""Tests for the diagnostics redaction list.

diagnostics.py cannot be imported here because it pulls in Home Assistant, so
the TO_REDACT literal is read straight from the source instead. That is enough
to guard the regression that matters: a key silently dropping off the list.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest


SOURCE = (
    Path(__file__).parents[1]
    / "custom_components"
    / "worx_vision_cloud"
    / "diagnostics.py"
).read_text(encoding="utf-8")


def _to_redact() -> set[str]:
    """Return the literal string members of the TO_REDACT set."""
    tree = ast.parse(SOURCE)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "TO_REDACT"
            for target in node.targets
        ):
            continue
        return {
            element.value
            for element in node.value.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        }
    raise AssertionError("TO_REDACT not found in diagnostics.py")


class RedactionListTests(unittest.TestCase):
    """Keys that carry personal data must stay in the redaction list."""

    def setUp(self) -> None:
        self.to_redact = _to_redact()

    def test_sim_identifiers_are_redacted(self) -> None:
        # The 4G module reports these inside module_status, where the account
        # level "sim" key never reached them.
        for key in ("ICCID", "IMSI", "iccid", "imsi"):
            with self.subTest(key=key):
                self.assertIn(key, self.to_redact)

    def test_previously_leaked_keys_are_still_redacted(self) -> None:
        # pin_code leaked until 2.4.0, the rest guard the same class of data.
        for key in ("pin_code", "pin", "sim", "mac", "gps", "serial_number"):
            with self.subTest(key=key):
                self.assertIn(key, self.to_redact)

    def test_location_keys_are_redacted(self) -> None:
        for key in ("latitude", "longitude", "coordinates", "address", "city"):
            with self.subTest(key=key):
                self.assertIn(key, self.to_redact)


if __name__ == "__main__":
    unittest.main()
