"""Tests for the weekly schedule line: one block per day, day label once."""

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
SPEC = importlib.util.spec_from_file_location("worx_helpers_summary", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)


def _slot(day: str, start: str, end: str, boundary: bool = False) -> dict:
    """Return a parsed slot as pyworxcloud hands it over."""
    return {"day": day, "start": start, "end": end, "duration": 270,
            "boundary": boundary}


# A full week with two slots on most days: the shape that made the old
# one-line-per-slot format repeat the day label ten times.
FULL_WEEK = [
    _slot("monday", "08:00", "12:30"),
    _slot("monday", "14:00", "18:00"),
    _slot("tuesday", "08:00", "12:30"),
    _slot("tuesday", "14:00", "18:00"),
    _slot("wednesday", "08:00", "12:30"),
    _slot("thursday", "08:00", "12:30"),
    _slot("thursday", "14:00", "18:00"),
    _slot("friday", "08:00", "12:30"),
    _slot("friday", "14:00", "18:00"),
    _slot("saturday", "08:00", "12:30"),
]


def _device(slots: list | None = FULL_WEEK) -> SimpleNamespace:
    """Return a mower-like object carrying a parsed weekly schedule."""
    return SimpleNamespace(schedules={"slots": list(slots or [])})


class DaySummaryTests(unittest.TestCase):
    """A day is written once, then each of its time ranges."""

    def test_two_slots_share_one_day_label(self) -> None:
        self.assertEqual(
            HELPERS.schedule_day_summary(
                "monday", [_slot("monday", "08:00", "12:30"),
                           _slot("monday", "14:00", "18:00")], "en"
            ),
            "Mon 08:00-12:30, 14:00-18:00",
        )

    def test_a_single_slot_still_carries_its_day(self) -> None:
        self.assertEqual(
            HELPERS.schedule_day_summary(
                "wednesday", [_slot("wednesday", "08:00", "12:30")], "en"
            ),
            "Wed 08:00-12:30",
        )

    def test_the_edge_marker_stays_on_its_own_slot(self) -> None:
        summary = HELPERS.schedule_day_summary(
            "monday",
            [_slot("monday", "08:00", "12:30"),
             _slot("monday", "14:00", "18:00", boundary=True)],
            "en",
        )
        self.assertEqual(summary, "Mon 08:00-12:30, 14:00-18:00 + edge")

    def test_the_marker_is_written_once_when_the_whole_day_cuts_the_edge(self) -> None:
        summary = HELPERS.schedule_day_summary(
            "monday",
            [_slot("monday", "08:00", "12:30", boundary=True),
             _slot("monday", "14:00", "18:00", boundary=True)],
            "en",
        )
        self.assertEqual(summary, "Mon 08:00-12:30, 14:00-18:00 + edge")
        self.assertEqual(summary.count("edge"), 1)

    def test_a_lone_edged_slot_keeps_its_marker(self) -> None:
        self.assertEqual(
            HELPERS.schedule_day_summary(
                "monday", [_slot("monday", "08:00", "12:30", boundary=True)], "en"
            ),
            "Mon 08:00-12:30 + edge",
        )

    def test_a_day_without_usable_times_falls_back_to_its_label(self) -> None:
        self.assertEqual(
            HELPERS.schedule_day_summary("monday", [{"day": "monday"}], "en"), "Mon"
        )

    def test_a_slot_without_an_end_uses_its_duration(self) -> None:
        self.assertEqual(
            HELPERS.schedule_day_summary(
                "monday", [{"day": "monday", "start": "08:00", "duration": 90}], "en"
            ),
            "Mon 08:00 (90 min)",
        )


class GroupingTests(unittest.TestCase):
    """Slots are gathered per day, in the order the mower reports them."""

    def test_days_keep_the_reported_order(self) -> None:
        days = [day for day, _ in HELPERS.schedule_slots_by_day(FULL_WEEK)]
        self.assertEqual(
            days,
            ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
        )

    def test_a_day_appears_once_even_when_its_slots_are_split(self) -> None:
        scattered = [
            _slot("monday", "08:00", "12:30"),
            _slot("tuesday", "08:00", "12:30"),
            _slot("monday", "14:00", "18:00"),
        ]
        grouped = HELPERS.schedule_slots_by_day(scattered)
        self.assertEqual([day for day, _ in grouped], ["monday", "tuesday"])
        self.assertEqual(len(grouped[0][1]), 2)

    def test_no_slots_group_to_nothing(self) -> None:
        self.assertEqual(HELPERS.schedule_slots_by_day([]), [])
        self.assertEqual(HELPERS.schedule_slots_by_day(None), [])


class SummaryTests(unittest.TestCase):
    """The sensor state reads one block per day."""

    EXPECTED_EN = (
        "Mon 08:00-12:30, 14:00-18:00 · Tue 08:00-12:30, 14:00-18:00 · "
        "Wed 08:00-12:30 · Thu 08:00-12:30, 14:00-18:00 · "
        "Fri 08:00-12:30, 14:00-18:00 · Sat 08:00-12:30"
    )

    def test_the_week_reads_day_by_day(self) -> None:
        self.assertEqual(HELPERS.schedule_summary(_device(), "en"), self.EXPECTED_EN)

    def test_each_day_label_appears_exactly_once(self) -> None:
        summary = HELPERS.schedule_summary(_device(), "en")
        for label in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat"):
            self.assertEqual(summary.count(label), 1, label)

    def test_it_is_shorter_than_one_line_per_slot(self) -> None:
        grouped = HELPERS.schedule_summary(_device(), "fr")
        per_slot = ", ".join(
            HELPERS.schedule_slot_summary(slot, "fr") for slot in FULL_WEEK
        )
        self.assertLess(len(grouped), len(per_slot))

    def test_days_and_slots_use_different_separators(self) -> None:
        self.assertNotEqual(
            HELPERS.SCHEDULE_DAY_SEPARATOR, HELPERS.SCHEDULE_SLOT_SEPARATOR
        )
        self.assertIn(HELPERS.SCHEDULE_DAY_SEPARATOR, self.EXPECTED_EN)

    def test_an_empty_schedule_says_so(self) -> None:
        self.assertEqual(HELPERS.schedule_summary(_device([]), "fr"),
                         "aucun créneau actif")

    def test_an_oversized_week_falls_back_to_the_count(self) -> None:
        long_week = [
            _slot(day, "08:00", "12:30", boundary=True)
            for day in ("monday", "tuesday", "wednesday", "thursday",
                        "friday", "saturday", "sunday")
        ] * 3
        state = HELPERS.schedule_summary(_device(long_week), "pl")
        self.assertEqual(state, f"{len(long_week)} aktywnych slotów")

    def test_a_full_week_with_the_edge_everywhere_still_fits(self) -> None:
        week = [
            _slot(day, start, end, boundary=True)
            for day in ("monday", "tuesday", "thursday", "friday")
            for start, end in (("08:00", "12:30"), ("14:00", "18:00"))
        ] + [
            _slot("wednesday", "08:00", "12:30", boundary=True),
            _slot("saturday", "08:00", "12:30", boundary=True),
        ]
        for language in ("fr", "en", "de", "pl"):
            with self.subTest(language=language):
                state = HELPERS.schedule_summary(_device(week), language)
                self.assertIn("08:00", state)
                self.assertLessEqual(len(state), HELPERS.MAX_STRING_STATE_LENGTH)

    def test_every_language_groups_the_week(self) -> None:
        for language in HELPERS.SCHEDULE_DAY_LABELS:
            with self.subTest(language=language):
                summary = HELPERS.schedule_summary(_device(), language)
                self.assertIn(HELPERS.SCHEDULE_DAY_SEPARATOR, summary)
                self.assertLessEqual(len(summary), HELPERS.MAX_STRING_STATE_LENGTH)


class AttributeTests(unittest.TestCase):
    """Cards read the detail from the attributes, not from the state."""

    def test_by_day_carries_one_entry_per_day(self) -> None:
        by_day = HELPERS.schedule_attributes(_device(), "en")["by_day"]
        self.assertEqual(len(by_day), 6)
        self.assertEqual(by_day[0]["day"], "monday")
        self.assertEqual(by_day[0]["day_label"], "Mon")
        self.assertEqual(by_day[0]["text"], "Mon 08:00-12:30, 14:00-18:00")
        self.assertEqual(len(by_day[0]["slots"]), 2)

    def test_by_day_slots_keep_the_zone_keys(self) -> None:
        slot = HELPERS.schedule_attributes(_device(), "en")["by_day"][0]["slots"][0]
        for key in ("zones", "zone_names", "zone_order", "start", "end"):
            self.assertIn(key, slot)

    def test_the_flat_slot_list_is_unchanged(self) -> None:
        attrs = HELPERS.schedule_attributes(_device(), "en")
        self.assertEqual(attrs["active_slots"], 10)
        self.assertEqual(len(attrs["slots"]), 10)

    def test_the_text_attribute_survives_the_state_fallback(self) -> None:
        long_week = [
            _slot(day, "08:00", "12:30", boundary=True)
            for day in ("monday", "tuesday", "wednesday", "thursday",
                        "friday", "saturday", "sunday")
        ] * 3
        device = _device(long_week)
        self.assertNotIn("08:00", HELPERS.schedule_summary(device, "pl"))
        self.assertIn("08:00", HELPERS.schedule_attributes(device, "pl")["text"])


if __name__ == "__main__":
    unittest.main()
