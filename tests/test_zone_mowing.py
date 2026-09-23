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
# The `sc` block the mower publishes carries more than its slots, and the
# whole block is replaced on a write, so the rest has to be echoed back.
SC_BLOCK = {
    "enabled": 1,
    "p": 0,
    "once": {"time": 0, "cfg": {"cut": {"b": 0, "z": []}}},
}
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
        payload = HELPERS.schedule_slots_payload(SC_BLOCK, [*WEEK, slot])
        self.assertEqual(payload["sc"]["slots"][-1], slot)
        self.assertEqual(len(payload["sc"]["slots"]), 3)

    def test_payload_echoes_everything_beside_the_slots(self) -> None:
        # The mower replaces its whole `sc` block, so a field left out is a
        # field erased. `enabled` is the schedule's own on switch.
        payload = HELPERS.schedule_slots_payload(SC_BLOCK, WEEK)["sc"]
        self.assertEqual(payload["enabled"], 1)
        self.assertEqual(payload["p"], 0)
        self.assertEqual(payload["once"], SC_BLOCK["once"])

    def test_payload_does_not_share_the_published_block(self) -> None:
        payload = HELPERS.schedule_slots_payload(SC_BLOCK, WEEK)["sc"]
        payload["once"]["time"] = 999
        self.assertEqual(SC_BLOCK["once"]["time"], 0)

    def test_the_old_slots_are_replaced_not_merged(self) -> None:
        payload = HELPERS.schedule_slots_payload(
            {**SC_BLOCK, "slots": WEEK}, [WEEK[0]]
        )["sc"]
        self.assertEqual(payload["slots"], [WEEK[0]])

    def test_a_mower_that_published_nothing_still_gets_its_slots(self) -> None:
        for published in ({}, None, [], "sc"):
            with self.subTest(published=published):
                payload = HELPERS.schedule_slots_payload(published, WEEK)
                self.assertEqual(payload, {"sc": {"slots": WEEK}})

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


class SlotVerdictTests(unittest.TestCase):
    """When an unacknowledged slot may be declared lost.

    A Landroid acknowledges no schedule write at all, mowing or docked, so
    the verdict can only come from the week it publishes, and that week may
    be minutes old in Home Assistant.
    """

    def setUp(self) -> None:
        self.slot = HELPERS.temporary_schedule_slot(MONDAY_EVENING, 30, [2, 1])
        self.job = {
            "slot": self.slot,
            "slots": WEEK,
            "start": MONDAY_EVENING.isoformat(),
            "confirmed": False,
        }

    def _verdict(self, slots: Any, now: dt.datetime) -> str:
        return HELPERS.zone_slot_verdict(self.job, slots, now)

    def test_the_slot_in_the_published_week_confirms_the_job(self) -> None:
        self.assertEqual(
            self._verdict([*WEEK, self.slot], MONDAY_EVENING), "confirmed"
        )

    def test_before_the_start_nothing_is_concluded(self) -> None:
        early = MONDAY_EVENING - dt.timedelta(hours=3)
        self.assertEqual(self._verdict(WEEK, early), "waiting")

    def test_the_verdict_waits_through_the_grace_period(self) -> None:
        # The published week is read from whatever arrived last, so the call
        # is held until the slot should be visibly running.
        for minutes in (0, 1, 4):
            with self.subTest(minutes=minutes):
                now = MONDAY_EVENING + dt.timedelta(minutes=minutes)
                self.assertEqual(self._verdict(WEEK, now), "waiting")

    def test_past_the_grace_period_a_missing_slot_is_dropped(self) -> None:
        now = MONDAY_EVENING + dt.timedelta(minutes=5)
        self.assertEqual(self._verdict(WEEK, now), "dropped")

    def test_a_slot_that_shows_up_late_is_still_confirmed(self) -> None:
        now = MONDAY_EVENING + dt.timedelta(hours=1)
        self.assertEqual(self._verdict([*WEEK, self.slot], now), "confirmed")

    def test_the_grace_period_is_configurable(self) -> None:
        now = MONDAY_EVENING + dt.timedelta(minutes=5)
        self.assertEqual(
            HELPERS.zone_slot_verdict(self.job, WEEK, now, 30), "waiting"
        )

    def test_an_unreadable_start_does_not_hold_the_job_forever(self) -> None:
        for start in ("", "tomorrow", None):
            with self.subTest(start=start):
                job = dict(self.job, start=start)
                self.assertEqual(
                    HELPERS.zone_slot_verdict(job, WEEK, MONDAY_EVENING), "dropped"
                )

    def test_a_job_without_a_slot_is_nothing_to_check(self) -> None:
        job = dict(self.job, slot=None)
        self.assertEqual(
            HELPERS.zone_slot_verdict(job, WEEK, MONDAY_EVENING), "confirmed"
        )

    def test_the_mowers_own_activity_never_decides(self) -> None:
        # The bug this replaces: any message from the mower was taken as
        # proof that it had republished its week, so an unacknowledged job
        # was dropped within a second. Only the week itself decides now.
        soon = MONDAY_EVENING - dt.timedelta(minutes=1)
        self.assertEqual(self._verdict(WEEK, soon), "waiting")


if __name__ == "__main__":
    unittest.main()
