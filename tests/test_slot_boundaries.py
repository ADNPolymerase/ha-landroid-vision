"""Tests for the border cut of weekly slots, read from the RTK map's schedule.

The Worx app keeps each slot's border cut in the schedule stored with the RTK
map. The mower's own cfg (`cut.b`) reports it off on every slot minutes after
an edit in the app, both in its answers and in the messages it sends on its
own, so it cannot be trusted. The map's times are the app's: a slot set to
08:00 there reads 08:05 from the mower with Save the hedgehogs on.
"""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from test_zone_job_retry import HELPERS  # noqa: E402

SERIAL = "SN-TEST"


def _parsed(boundary: bool = False) -> list[dict]:
    # Monday 08:05-12:30 and 14:00-18:00, Wednesday 08:05-12:30, as parsed
    # from the mower's cfg, where the border cut is always off.
    return [
        {"day": "monday", "start": "08:05", "end": "12:30", "duration": 265, "boundary": boundary},
        {"day": "monday", "start": "14:00", "end": "18:00", "duration": 240, "boundary": boundary},
        {"day": "wednesday", "start": "08:05", "end": "12:30", "duration": 265, "boundary": boundary},
    ]


def _entry(day: int, start: int, duration: int, border: bool, *, enabled: bool = True, owner: str | None = SERIAL) -> dict:
    return {
        "product_item": owner,
        "enabled": enabled,
        "day_of_week": day,
        "starts_at": start,
        "duration": duration,
        "zones": [1, 2],
        "zones_ordered": False,
        "border_cut": border,
    }


def _map_schedule() -> list[dict]:
    # As the app keeps it: Monday 08:00 without, 14:00 with, Wednesday 08:00
    # with, and the disabled placeholders the app stores around them.
    return [
        _entry(0, 0, 1425, False, enabled=False),
        _entry(1, 0, 420, False, enabled=False),
        _entry(1, 480, 270, False),
        _entry(1, 840, 240, True),
        _entry(1, 1260, 165, False, enabled=False),
        _entry(3, 480, 270, True),
    ]


def _device(schedule: list | None = None, *, parsed_boundary: bool = False) -> SimpleNamespace:
    device = SimpleNamespace(serial_number=SERIAL, schedules={"slots": _parsed(parsed_boundary)})
    if schedule is not None:
        device._worx_vision_rtk_map = {"layers": {}, "schedule": schedule}
    return device


def _boundaries(device) -> list:
    return [slot["boundary"] for slot in HELPERS.schedule_slots(device)]


class MapScheduleTest(unittest.TestCase):
    def test_the_border_cut_follows_the_app(self) -> None:
        self.assertEqual(_boundaries(_device(_map_schedule())), [False, True, True])

    def test_the_mower_cfg_is_overridden_both_ways(self) -> None:
        schedule = [_entry(1, 480, 270, True), _entry(1, 840, 240, False), _entry(3, 480, 270, False)]
        self.assertEqual(_boundaries(_device(schedule, parsed_boundary=True)), [True, False, False])

    def test_the_parsed_slots_are_left_untouched(self) -> None:
        device = _device(_map_schedule())
        HELPERS.schedule_slots(device)
        self.assertFalse(device.schedules["slots"][1]["boundary"])

    def test_without_a_map_the_mower_cfg_stays(self) -> None:
        self.assertEqual(_boundaries(_device(None, parsed_boundary=True)), [True] * 3)
        self.assertEqual(_boundaries(_device([], parsed_boundary=True)), [True] * 3)

    def test_disabled_slots_and_other_mowers_are_ignored(self) -> None:
        schedule = [
            _entry(1, 840, 240, False, enabled=False),
            _entry(1, 840, 240, False, owner="OTHER"),
            _entry(1, 840, 240, True),
        ]
        self.assertEqual(_boundaries(_device(schedule)), [False, True, False])

    def test_entries_without_an_owner_count(self) -> None:
        self.assertEqual(_boundaries(_device([_entry(1, 840, 240, True, owner=None)])), [False, True, False])

    def test_unreadable_entries_are_skipped(self) -> None:
        schedule = [
            "x",
            {**_entry(1, 840, 240, True), "starts_at": "14:00"},
            {**_entry(1, 840, 240, True), "day_of_week": True},
        ]
        self.assertEqual(_boundaries(_device(schedule)), [False, False, False])


class MatchingTest(unittest.TestCase):
    def test_a_later_start_matches_by_its_end(self) -> None:
        # 08:00 for 270 min in the app, 08:05 for 265 min from the mower.
        self.assertEqual(_boundaries(_device([_entry(1, 480, 270, True)])), [True, False, False])

    def test_the_nearest_start_within_an_hour_matches(self) -> None:
        self.assertEqual(_boundaries(_device([_entry(1, 470, 200, True)])), [True, False, False])
        self.assertEqual(_boundaries(_device([_entry(1, 400, 200, True)])), [False, False, False])

    def test_another_day_never_matches(self) -> None:
        self.assertEqual(_boundaries(_device([_entry(2, 840, 240, True)])), [False, False, False])

    def test_a_map_slot_is_used_once(self) -> None:
        device = _device([_entry(1, 840, 240, True)])
        device.schedules["slots"].append(
            {"day": "monday", "start": "14:00", "end": "18:00", "duration": 240, "boundary": False}
        )
        self.assertEqual(_boundaries(device), [False, True, False, False])


if __name__ == "__main__":
    unittest.main()
