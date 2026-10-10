"""Tests for yesterday's mowing time and the last mowing session."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "worx_vision_cloud"
    / "statistics.py"
)
SPEC = importlib.util.spec_from_file_location("worx_history_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
STATISTICS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = STATISTICS
SPEC.loader.exec_module(STATISTICS)
DailyStatisticsTracker = STATISTICS.DailyStatisticsTracker

SERIAL = "mower"
DAY = date(2026, 7, 6)
MIDNIGHT = datetime(2026, 7, 6, tzinfo=UTC)


def feed(tracker, when, active, zone=None, day=DAY, midnight=MIDNIGHT):
    """Push one snapshot into the tracker."""
    return tracker.update(
        SERIAL,
        area_total=None,
        mowing_active=active,
        now_utc=when,
        local_day=day,
        local_midnight_utc=midnight,
        zone=zone,
    )


def mow(tracker, start, minutes, zone=None, step=5):
    """Report mowing every `step` minutes, then a stop at the end."""
    t = start
    while t < start + timedelta(minutes=minutes):
        feed(tracker, t, True, zone)
        t += timedelta(minutes=step)
    end = start + timedelta(minutes=minutes)
    feed(tracker, end, False)
    return end


class LastSessionTests(unittest.TestCase):
    """A session's start, end, duration and zones."""

    def test_nothing_known_before_a_first_session(self) -> None:
        tracker = DailyStatisticsTracker()
        feed(tracker, MIDNIGHT + timedelta(hours=8), False)
        self.assertIsNone(tracker.last_session(SERIAL))

    def test_one_session(self) -> None:
        tracker = DailyStatisticsTracker()
        start = MIDNIGHT + timedelta(hours=8)
        end = mow(tracker, start, 90, zone="Front")
        session = tracker.last_session(SERIAL)
        self.assertEqual(session["start"], start)
        self.assertEqual(session["end"], end)
        self.assertEqual(session["duration_min"], 90.0)
        self.assertEqual(session["zones"], ["Front"])

    def test_session_in_progress_keeps_the_previous_one(self) -> None:
        tracker = DailyStatisticsTracker()
        first_end = mow(tracker, MIDNIGHT + timedelta(hours=8), 30)
        feed(tracker, first_end + timedelta(hours=2), True)
        self.assertEqual(tracker.last_session(SERIAL)["end"], first_end)

    def test_short_stop_continues_the_session(self) -> None:
        tracker = DailyStatisticsTracker()
        start = MIDNIGHT + timedelta(hours=8)
        stop = mow(tracker, start, 40, zone="Front")
        end = mow(tracker, stop + timedelta(minutes=5), 20, zone="Back")
        session = tracker.last_session(SERIAL)
        self.assertEqual(session["start"], start)
        self.assertEqual(session["end"], end)
        # Mowing time only: the five-minute stop is not counted.
        self.assertEqual(session["duration_min"], 60.0)
        self.assertEqual(session["zones"], ["Front", "Back"])

    def test_long_break_starts_a_new_session(self) -> None:
        tracker = DailyStatisticsTracker()
        stop = mow(tracker, MIDNIGHT + timedelta(hours=8), 40)
        second = stop + timedelta(minutes=11)
        end = mow(tracker, second, 20)
        session = tracker.last_session(SERIAL)
        self.assertEqual(session["start"], second)
        self.assertEqual(session["end"], end)
        self.assertEqual(session["duration_min"], 20.0)

    def test_zone_listed_once_and_in_order(self) -> None:
        tracker = DailyStatisticsTracker()
        start = MIDNIGHT + timedelta(hours=8)
        for minute, zone in ((0, "A"), (5, "B"), (10, "A"), (15, None)):
            feed(tracker, start + timedelta(minutes=minute), True, zone)
        feed(tracker, start + timedelta(minutes=20), False)
        self.assertEqual(tracker.last_session(SERIAL)["zones"], ["A", "B"])

    def test_restart_mid_session_survives_and_ends_at_last_sighting(self) -> None:
        tracker = DailyStatisticsTracker()
        start = MIDNIGHT + timedelta(hours=8)
        for minute in range(0, 35, 5):
            feed(tracker, start + timedelta(minutes=minute), True, "Front")
        restored = DailyStatisticsTracker(tracker.as_dict())
        # First update after the restart: the mower is back on its station.
        feed(restored, start + timedelta(hours=2), False)
        session = restored.last_session(SERIAL)
        self.assertEqual(session["start"], start)
        self.assertEqual(session["end"], start + timedelta(minutes=30))
        self.assertEqual(session["duration_min"], 30.0)

    def test_restart_mid_session_then_more_mowing_is_one_session(self) -> None:
        tracker = DailyStatisticsTracker()
        start = MIDNIGHT + timedelta(hours=8)
        feed(tracker, start, True)
        feed(tracker, start + timedelta(minutes=10), True)
        restored = DailyStatisticsTracker(tracker.as_dict())
        feed(restored, start + timedelta(minutes=12), True)
        feed(restored, start + timedelta(minutes=22), False)
        session = restored.last_session(SERIAL)
        self.assertEqual(session["start"], start)
        # The two minutes HA was down are not counted.
        self.assertEqual(session["duration_min"], 20.0)

    def test_finished_session_survives_a_restart(self) -> None:
        tracker = DailyStatisticsTracker()
        end = mow(tracker, MIDNIGHT + timedelta(hours=8), 45, zone="Front")
        restored = DailyStatisticsTracker(tracker.as_dict())
        self.assertEqual(restored.last_session(SERIAL)["end"], end)
        self.assertEqual(restored.last_session(SERIAL)["zones"], ["Front"])

    def test_corrupt_stored_session_is_dropped(self) -> None:
        restored = DailyStatisticsTracker(
            {"last_session": {SERIAL: {"start": "nonsense", "seconds": 10}}}
        )
        self.assertIsNone(restored.last_session(SERIAL))

    def test_naive_timestamps_are_rejected(self) -> None:
        restored = DailyStatisticsTracker(
            {
                "last_session": {
                    SERIAL: {
                        "start": "2026-07-06T08:00:00",
                        "end": "2026-07-06T09:00:00",
                        "last_seen": "2026-07-06T09:00:00",
                        "seconds": 3600,
                    }
                }
            }
        )
        self.assertIsNone(restored.last_session(SERIAL))


class YesterdayTests(unittest.TestCase):
    """The previous local day's mowing time."""

    next_day = date(2026, 7, 7)
    next_midnight = datetime(2026, 7, 7, tzinfo=UTC)

    def test_unknown_before_any_data(self) -> None:
        tracker = DailyStatisticsTracker()
        self.assertIsNone(
            tracker.mowing_minutes_yesterday(SERIAL, MIDNIGHT, DAY)
        )

    def test_today_becomes_yesterday_at_midnight(self) -> None:
        tracker = DailyStatisticsTracker()
        mow(tracker, MIDNIGHT + timedelta(hours=14), 130)
        feed(tracker, self.next_midnight + timedelta(minutes=1), False,
             day=self.next_day, midnight=self.next_midnight)
        self.assertEqual(
            tracker.mowing_minutes_yesterday(
                SERIAL, self.next_midnight + timedelta(minutes=1), self.next_day
            ),
            130.0,
        )
        self.assertEqual(
            tracker.mowing_minutes_today(
                SERIAL, self.next_midnight + timedelta(minutes=1), self.next_day
            ),
            0.0,
        )

    def test_streak_across_midnight_is_split(self) -> None:
        tracker = DailyStatisticsTracker()
        feed(tracker, self.next_midnight - timedelta(minutes=20), True)
        feed(tracker, self.next_midnight - timedelta(minutes=10), True)
        now = self.next_midnight + timedelta(minutes=15)
        feed(tracker, now, True, day=self.next_day, midnight=self.next_midnight)
        self.assertEqual(
            tracker.mowing_minutes_yesterday(SERIAL, now, self.next_day), 20.0
        )
        self.assertEqual(
            tracker.mowing_minutes_today(SERIAL, now, self.next_day), 15.0
        )

    def test_read_after_midnight_before_any_update(self) -> None:
        tracker = DailyStatisticsTracker()
        mow(tracker, MIDNIGHT + timedelta(hours=14), 45)
        self.assertEqual(
            tracker.mowing_minutes_yesterday(
                SERIAL, self.next_midnight + timedelta(seconds=30), self.next_day
            ),
            45.0,
        )

    def test_day_without_mowing_is_zero(self) -> None:
        tracker = DailyStatisticsTracker()
        feed(tracker, MIDNIGHT + timedelta(hours=10), False)
        feed(tracker, self.next_midnight + timedelta(hours=1), False,
             day=self.next_day, midnight=self.next_midnight)
        self.assertEqual(
            tracker.mowing_minutes_yesterday(
                SERIAL, self.next_midnight + timedelta(hours=1), self.next_day
            ),
            0.0,
        )

    def test_stale_record_after_a_gap_is_not_yesterday(self) -> None:
        tracker = DailyStatisticsTracker()
        mow(tracker, MIDNIGHT + timedelta(hours=14), 60)
        later = date(2026, 7, 9)
        later_midnight = datetime(2026, 7, 9, tzinfo=UTC)
        feed(tracker, later_midnight + timedelta(hours=1), False,
             day=later, midnight=later_midnight)
        # The 60 minutes belong to the 6th, not to the 8th.
        self.assertEqual(
            tracker.mowing_minutes_yesterday(
                SERIAL, later_midnight + timedelta(hours=1), later
            ),
            0.0,
        )

    def test_yesterday_survives_a_restart(self) -> None:
        tracker = DailyStatisticsTracker()
        mow(tracker, MIDNIGHT + timedelta(hours=14), 75)
        feed(tracker, self.next_midnight + timedelta(minutes=1), False,
             day=self.next_day, midnight=self.next_midnight)
        restored = DailyStatisticsTracker(tracker.as_dict())
        self.assertEqual(
            restored.mowing_minutes_yesterday(
                SERIAL, self.next_midnight + timedelta(hours=3), self.next_day
            ),
            75.0,
        )

    def test_old_storage_without_new_keys_still_loads(self) -> None:
        restored = DailyStatisticsTracker(
            {"mowing": {SERIAL: {"day": DAY.isoformat(), "seconds": 600}}}
        )
        self.assertEqual(
            restored.mowing_minutes_today(SERIAL, MIDNIGHT, DAY), 10.0
        )
        self.assertIsNone(restored.last_session(SERIAL))


if __name__ == "__main__":
    unittest.main()
