"""Tests for the temporary schedule slot behind zone mowing."""

from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
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

# Monday 21:00 local, so the raw day is 1 and the start minute 1260.
MONDAY_EVENING = dt.datetime(2026, 9, 21, 21, 0, tzinfo=dt.UTC)
SUNDAY_MORNING = dt.datetime(2026, 9, 27, 9, 30, tzinfo=dt.UTC)
# Fictional week: one morning slot and one afternoon slot on Monday.
WEEK = [
    {"e": 1, "d": 1, "s": 480, "t": 270, "cfg": {"cut": {"b": 1, "z": [1, 2], "zo": 0}}},
    {"e": 1, "d": 1, "s": 840, "t": 240, "cfg": {"cut": {"b": 1, "z": [1, 2], "zo": 0}}},
]


def _device(slots: Any) -> SimpleNamespace:
    return SimpleNamespace(raw_cfg={"sc": {"enabled": 1, "slots": slots}})


class TemporarySlotTests(unittest.TestCase):
    def test_slot_shape_matches_a_weekly_slot(self) -> None:
        slot = HELPERS.temporary_schedule_slot(MONDAY_EVENING, 30, [2, 1])
        self.assertEqual(
            slot,
            {
                "e": 1,
                "d": 1,
                "s": 1260,
                "t": 30,
                "cfg": {"cut": {"b": 0, "ob": 0, "z": [2, 1], "zo": 1}},
            },
        )

    def test_sunday_is_raw_day_zero(self) -> None:
        self.assertEqual(
            HELPERS.temporary_schedule_slot(SUNDAY_MORNING, 20, [1])["d"], 0
        )

    def test_edge_cut_drops_the_over_border_field(self) -> None:
        slot = HELPERS.temporary_schedule_slot(MONDAY_EVENING, 30, [1], True)
        self.assertEqual(slot["cfg"]["cut"], {"b": 1, "z": [1], "zo": 1})

    def test_zone_order_is_kept(self) -> None:
        self.assertEqual(
            HELPERS.temporary_schedule_slot(MONDAY_EVENING, 30, [2, 1])["cfg"]["cut"]["z"],
            [2, 1],
        )

    def test_payload_carries_the_whole_week(self) -> None:
        slot = HELPERS.temporary_schedule_slot(MONDAY_EVENING, 30, [1])
        payload = HELPERS.schedule_slots_payload([*WEEK, slot])
        self.assertEqual(payload["sc"]["slots"][-1], slot)
        self.assertEqual(len(payload["sc"]["slots"]), 3)

    def test_raw_slots_are_read_from_the_mower(self) -> None:
        self.assertEqual(HELPERS.raw_schedule_slots(_device(WEEK)), WEEK)
        self.assertEqual(HELPERS.raw_schedule_slots(_device(None)), [])


class ConflictTests(unittest.TestCase):
    def test_free_evening_has_no_conflict(self) -> None:
        slot = HELPERS.temporary_schedule_slot(MONDAY_EVENING, 30, [1])
        self.assertIsNone(HELPERS.conflicting_schedule_slot(WEEK, slot))

    def test_overlapping_slot_is_reported(self) -> None:
        # 15:00 Monday falls inside the 14:00 to 18:00 slot.
        start = MONDAY_EVENING.replace(hour=15)
        slot = HELPERS.temporary_schedule_slot(start, 30, [1])
        conflict = HELPERS.conflicting_schedule_slot(WEEK, slot)
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict["s"], 840)

    def test_a_slot_starting_exactly_at_the_end_is_free(self) -> None:
        start = MONDAY_EVENING.replace(hour=18, minute=0)
        slot = HELPERS.temporary_schedule_slot(start, 30, [1])
        self.assertIsNone(HELPERS.conflicting_schedule_slot(WEEK, slot))

    def test_disabled_slots_do_not_conflict(self) -> None:
        week = [dict(WEEK[1], e=0)]
        start = MONDAY_EVENING.replace(hour=15)
        slot = HELPERS.temporary_schedule_slot(start, 30, [1])
        self.assertIsNone(HELPERS.conflicting_schedule_slot(week, slot))

    def test_another_day_does_not_conflict(self) -> None:
        start = MONDAY_EVENING.replace(day=22, hour=15)
        slot = HELPERS.temporary_schedule_slot(start, 30, [1])
        self.assertIsNone(HELPERS.conflicting_schedule_slot(WEEK, slot))

    def test_a_job_running_past_midnight_is_refused(self) -> None:
        slot = HELPERS.temporary_schedule_slot(
            MONDAY_EVENING.replace(hour=23, minute=45), 30, [1]
        )
        self.assertTrue(HELPERS.slot_crosses_midnight(slot))
        self.assertFalse(
            HELPERS.slot_crosses_midnight(
                HELPERS.temporary_schedule_slot(MONDAY_EVENING, 30, [1])
            )
        )


class RestoreReasonTests(unittest.TestCase):
    NOW = dt.datetime(2026, 9, 21, 21, 30, tzinfo=dt.UTC)

    def _job(self, **kwargs: Any) -> dict[str, Any]:
        job = {
            "slots": WEEK,
            "deadline": dt.datetime(2026, 9, 21, 22, 30, tzinfo=dt.UTC).isoformat(),
            "left": False,
        }
        job.update(kwargs)
        return job

    def test_nothing_to_do_while_the_mower_is_still_out(self) -> None:
        self.assertIsNone(
            HELPERS.zone_mowing_restore_reason(self._job(left=True), False, self.NOW)
        )

    def test_docked_before_leaving_does_not_end_the_job(self) -> None:
        # The mower is still on its base in the two minutes before the start.
        self.assertIsNone(
            HELPERS.zone_mowing_restore_reason(self._job(), True, self.NOW)
        )

    def test_back_home_after_leaving_ends_the_job(self) -> None:
        self.assertEqual(
            HELPERS.zone_mowing_restore_reason(self._job(left=True), True, self.NOW),
            "docked",
        )

    def test_deadline_ends_the_job_even_away_from_base(self) -> None:
        late = self.NOW + dt.timedelta(hours=2)
        self.assertEqual(
            HELPERS.zone_mowing_restore_reason(self._job(left=True), False, late),
            "deadline",
        )

    def test_unreadable_deadline_still_ends_on_docking(self) -> None:
        job = self._job(deadline="not a date", left=True)
        self.assertEqual(
            HELPERS.zone_mowing_restore_reason(job, True, self.NOW), "docked"
        )
        self.assertIsNone(HELPERS.zone_mowing_restore_reason(job, False, self.NOW))

    def test_a_job_booked_for_later_ignores_todays_mowing(self) -> None:
        # The mower goes out and comes back for its usual slot before the
        # booked job even starts: the temporary slot must survive that.
        job = self._job(
            start=(self.NOW + dt.timedelta(days=1)).isoformat(),
            deadline=(self.NOW + dt.timedelta(days=1, hours=2)).isoformat(),
            left=True,
        )
        self.assertIsNone(HELPERS.zone_mowing_restore_reason(job, True, self.NOW))

    def test_a_job_booked_for_later_ends_normally_once_started(self) -> None:
        job = self._job(
            start=(self.NOW - dt.timedelta(minutes=30)).isoformat(), left=True
        )
        self.assertEqual(
            HELPERS.zone_mowing_restore_reason(job, True, self.NOW), "docked"
        )

    def test_an_unreadable_start_does_not_block_the_end(self) -> None:
        job = self._job(start="not a date", left=True)
        self.assertEqual(
            HELPERS.zone_mowing_restore_reason(job, True, self.NOW), "docked"
        )


class SlotConfirmationTests(unittest.TestCase):
    """An unacknowledged slot is checked against the published week."""

    def setUp(self) -> None:
        self.slot = HELPERS.temporary_schedule_slot(MONDAY_EVENING, 30, [2, 1])

    def test_absent_from_the_week(self) -> None:
        self.assertFalse(HELPERS.slot_in_schedule(WEEK, self.slot))

    def test_present_in_the_week(self) -> None:
        self.assertTrue(HELPERS.slot_in_schedule([*WEEK, self.slot], self.slot))

    def test_a_rewritten_cut_block_still_matches(self) -> None:
        # The firmware echoes the cut block back in its own shape, which does
        # not make it another slot.
        echoed = {
            "e": 1,
            "d": self.slot["d"],
            "s": self.slot["s"],
            "t": self.slot["t"],
            "cfg": {"cut": {"b": 0, "z": [2, 1], "zo": 1}},
        }
        self.assertTrue(HELPERS.slot_in_schedule([*WEEK, echoed], self.slot))

    def test_same_time_another_day_does_not_match(self) -> None:
        other = dict(self.slot, d=(self.slot["d"] + 1) % 7)
        self.assertFalse(HELPERS.slot_in_schedule([*WEEK, other], self.slot))

    def test_same_start_another_runtime_does_not_match(self) -> None:
        other = dict(self.slot, t=self.slot["t"] + 15)
        self.assertFalse(HELPERS.slot_in_schedule([*WEEK, other], self.slot))

    def test_a_week_without_slots_is_safe(self) -> None:
        self.assertFalse(HELPERS.slot_in_schedule(None, self.slot))


if __name__ == "__main__":
    unittest.main()
