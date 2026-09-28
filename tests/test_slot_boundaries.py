"""Tests for the border cut of weekly slots, kept from the mower's own pushes.

The mower publishes each slot's border cut (`cfg.cut.b`); the copy the Worx
cloud returns on an API refresh has it off on every slot. Seen live: an edit
in the Worx app arrived in a push, then vanished 4 seconds later.
"""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from test_zone_job_retry import COORDINATOR, HELPERS  # noqa: E402

SERIAL = "SN-TEST"


def _raw_slot(day: int, start: int, boundary: int | None) -> dict:
    cut = {"z": [1, 2]}
    if boundary is not None:
        cut["b"] = boundary
    return {"d": day, "s": start, "t": 240, "cfg": {"cut": cut}}


def _cfg(*boundaries: int | None) -> dict:
    # Monday (1) 08:05 and 14:00, Wednesday (3) 08:05.
    slots = [(1, 485), (1, 840), (3, 485)]
    return {"sc": {"slots": [_raw_slot(d, s, b) for (d, s), b in zip(slots, boundaries)]}}


def _parsed(boundary: bool) -> list[dict]:
    return [
        {"day": "monday", "start": "08:05", "boundary": boundary},
        {"day": "monday", "start": "14:00", "boundary": boundary},
        {"day": "wednesday", "start": "08:05", "boundary": boundary},
    ]


class FakeStore:
    def __init__(self) -> None:
        self.saves = 0

    def async_delay_save(self, data_func, _delay) -> None:
        self.saves += 1
        data_func()


def _coordinator():
    coordinator = object.__new__(COORDINATOR.WorxVisionCoordinator)
    coordinator._slot_boundaries = {}
    coordinator._cfg_seen = {}
    coordinator._slot_boundary_store = FakeStore()
    return coordinator


def _device(cfg: dict, parsed_boundary: bool = False) -> SimpleNamespace:
    return SimpleNamespace(raw_cfg=cfg, schedules={"slots": _parsed(parsed_boundary)})


class RawBoundariesTest(unittest.TestCase):
    def test_keys_are_raw_day_and_start(self) -> None:
        self.assertEqual(
            HELPERS.raw_slot_boundaries(_cfg(0, 1, 1)),
            {"1:485": False, "1:840": True, "3:485": True},
        )

    def test_slots_without_the_flag_are_left_out(self) -> None:
        self.assertEqual(HELPERS.raw_slot_boundaries(_cfg(None, 1, None)), {"1:840": True})
        self.assertEqual(HELPERS.raw_slot_boundaries({}), {})
        self.assertEqual(HELPERS.raw_slot_boundaries(None), {})


class ScheduleSlotsTest(unittest.TestCase):
    def test_pushed_boundaries_win_over_the_parsed_ones(self) -> None:
        device = _device(_cfg(0, 0, 0), parsed_boundary=False)
        device._worx_vision_slot_boundaries = {"1:840": True, "3:485": True}
        self.assertEqual(
            [s["boundary"] for s in HELPERS.schedule_slots(device)], [False, True, True]
        )
        # The parsed slots are left untouched.
        self.assertFalse(device.schedules["slots"][1]["boundary"])

    def test_without_pushed_boundaries_the_parsed_ones_stay(self) -> None:
        device = _device(_cfg(1, 1, 1), parsed_boundary=True)
        self.assertEqual([s["boundary"] for s in HELPERS.schedule_slots(device)], [True] * 3)


class CoordinatorTest(unittest.TestCase):
    def test_a_push_teaches_the_boundaries_and_the_cloud_copy_does_not_erase_them(self) -> None:
        coordinator = _coordinator()
        cloud = _device(_cfg(0, 0, 0))
        coordinator._cfg_seen[SERIAL] = cloud.raw_cfg  # first refresh
        coordinator._attach_slot_boundaries(SERIAL, cloud)

        pushed = _device(_cfg(0, 1, 1))
        coordinator._note_pushed_schedule(SERIAL, pushed)
        self.assertEqual(coordinator._slot_boundaries[SERIAL], {"1:485": False, "1:840": True, "3:485": True})
        self.assertEqual([s["boundary"] for s in HELPERS.schedule_slots(pushed)], [False, True, True])

        # API refresh 4 s later: the cloud's copy, every flag off.
        refreshed = _device(_cfg(0, 0, 0))
        coordinator._cfg_seen[SERIAL] = refreshed.raw_cfg
        coordinator._attach_slot_boundaries(SERIAL, refreshed)
        self.assertEqual([s["boundary"] for s in HELPERS.schedule_slots(refreshed)], [False, True, True])

    def test_a_push_without_cfg_teaches_nothing(self) -> None:
        coordinator = _coordinator()
        device = _device(_cfg(0, 0, 0))
        coordinator._cfg_seen[SERIAL] = device.raw_cfg
        coordinator._note_pushed_schedule(SERIAL, device)  # same cfg object
        self.assertNotIn(SERIAL, coordinator._slot_boundaries)

    def test_nothing_is_learnt_before_the_first_refresh(self) -> None:
        coordinator = _coordinator()
        coordinator._note_pushed_schedule(SERIAL, _device(_cfg(0, 0, 0)))
        self.assertNotIn(SERIAL, coordinator._slot_boundaries)

    def test_an_edit_in_the_app_replaces_the_boundaries(self) -> None:
        coordinator = _coordinator()
        coordinator._cfg_seen[SERIAL] = None
        coordinator._note_pushed_schedule(SERIAL, _device(_cfg(1, 1, 1)))
        coordinator._note_pushed_schedule(SERIAL, _device(_cfg(0, 1, 1)))
        self.assertEqual(coordinator._slot_boundaries[SERIAL]["1:485"], False)
        self.assertEqual(coordinator._slot_boundary_store.saves, 2)


if __name__ == "__main__":
    unittest.main()
