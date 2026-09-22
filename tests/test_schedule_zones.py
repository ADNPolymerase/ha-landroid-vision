"""Tests for the zones each weekly slot carries, in attributes and calendar."""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
from typing import Any
import unittest


def _stub(name: str) -> ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = ModuleType(name)
        sys.modules[name] = module
    return module


HOMEASSISTANT_UTIL = _stub("homeassistant.util")
if not hasattr(HOMEASSISTANT_UTIL, "slugify"):
    HOMEASSISTANT_UTIL.slugify = lambda value: str(value).lower().replace(" ", "_")
_stub("homeassistant").util = HOMEASSISTANT_UTIL
DT_UTIL = _stub("homeassistant.util.dt")
DT_UTIL.DEFAULT_TIME_ZONE = dt.UTC
NOW = dt.datetime(2026, 9, 22, 15, 30, tzinfo=dt.UTC)
DT_UTIL.now = lambda: NOW
HOMEASSISTANT_UTIL.dt = DT_UTIL


@dataclass
class CalendarEvent:
    start: Any
    end: Any
    summary: str
    description: str | None = None


_stub("homeassistant.components")
CALENDAR = _stub("homeassistant.components.calendar")
CALENDAR.CalendarEntity = type("CalendarEntity", (), {})
CALENDAR.CalendarEvent = CalendarEvent
_stub("homeassistant.config_entries").ConfigEntry = object
_stub("homeassistant.core").HomeAssistant = object
_stub("homeassistant.helpers")
_stub("homeassistant.helpers.entity_platform").AddConfigEntryEntitiesCallback = object

PACKAGE_DIR = Path(__file__).parents[1] / "custom_components" / "worx_vision_cloud"
PACKAGE = "worx_schedule_zones_pkg"
_package = ModuleType(PACKAGE)
_package.__path__ = [str(PACKAGE_DIR)]
sys.modules[PACKAGE] = _package
CONST = _stub(f"{PACKAGE}.const")
CONST.DOMAIN = "worx_vision_cloud"
CONST.CONF_CALENDAR_DAYS = "calendar_window_days"
CONST.DEFAULT_CALENDAR_DAYS = 7
_stub(f"{PACKAGE}.entity").WorxVisionEntity = type("WorxVisionEntity", (), {})


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.{name}", PACKAGE_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HELPERS = _load("helpers")
CALENDAR_MODULE = _load("calendar")

# Protocol 1 shape: the raw week starts on Sunday (d = 0). Fictional values.
RAW_SC = {
    "enabled": 1,
    "slots": [
        {"e": 1, "d": 1, "s": 480, "t": 270, "cfg": {"cut": {"b": 1, "z": [2, 1], "zo": 1}}},
        {"e": 1, "d": 1, "s": 840, "t": 240, "cfg": {"cut": {"b": 0, "ob": 0, "z": [1, 2], "zo": 0}}},
        {"e": 1, "d": 0, "s": 600, "t": 60, "cfg": {"cut": {"b": 1, "z": [3], "zo": 1}}},
    ],
}
MONDAY_MORNING = {"day": "monday", "start": "08:00", "end": "12:30", "duration": 270, "boundary": True}
MONDAY_AFTERNOON = {"day": "monday", "start": "14:00", "end": "18:00", "duration": 240, "boundary": False}
SUNDAY = {"day": "sunday", "start": "10:00", "end": "11:00", "duration": 60, "boundary": True}
NAMES = {1: "Front lawn", 2: "Back lawn"}


def _device(raw_sc: Any = RAW_SC, slots: list[dict[str, Any]] | None = None) -> SimpleNamespace:
    device = SimpleNamespace(raw_cfg={"sc": raw_sc} if raw_sc is not None else {})
    device.schedules = {"slots": slots if slots is not None else [MONDAY_MORNING, MONDAY_AFTERNOON]}
    return device


class _NamedZones(unittest.TestCase):
    """Stub the map name resolution, which has its own pairing logic."""

    def setUp(self) -> None:
        self._original = HELPERS.rtk_zone_names
        HELPERS.rtk_zone_names = lambda device: dict(NAMES)

    def tearDown(self) -> None:
        HELPERS.rtk_zone_names = self._original


class ScheduleSlotZonesTests(_NamedZones):
    def test_matches_the_raw_slot_on_day_and_start(self) -> None:
        zones = HELPERS.schedule_slot_zones(_device(), MONDAY_MORNING)
        self.assertEqual(zones["zones"], [2, 1])
        self.assertEqual(zones["zone_names"], ["Back lawn", "Front lawn"])
        self.assertEqual(zones["zone_order"], "ordered")

    def test_two_slots_on_the_same_day_stay_apart(self) -> None:
        zones = HELPERS.schedule_slot_zones(_device(), MONDAY_AFTERNOON)
        self.assertEqual(zones["zones"], [1, 2])
        self.assertEqual(zones["zone_order"], "auto")

    def test_sunday_is_raw_day_zero(self) -> None:
        zones = HELPERS.schedule_slot_zones(_device(slots=[SUNDAY]), SUNDAY)
        self.assertEqual(zones["zones"], [3])

    def test_unknown_zone_id_gets_a_generic_name(self) -> None:
        zones = HELPERS.schedule_slot_zones(_device(slots=[SUNDAY]), SUNDAY)
        self.assertEqual(zones["zone_names"], ["Zone 3"])

    def test_no_raw_twin_gives_none(self) -> None:
        other = dict(MONDAY_MORNING, start="09:00")
        self.assertEqual(
            HELPERS.schedule_slot_zones(_device(), other),
            {"zones": None, "zone_names": None, "zone_order": None},
        )

    def test_protocol_0_block_gives_none(self) -> None:
        protocol0 = {"m": 1, "d": [["08:00", 270, 1]] * 7}
        zones = HELPERS.schedule_slot_zones(_device(protocol0), MONDAY_MORNING)
        self.assertIsNone(zones["zones"])

    def test_attributes_carry_zones_per_slot(self) -> None:
        attrs = HELPERS.schedule_attributes(_device())
        self.assertEqual([slot["zones"] for slot in attrs["slots"]], [[2, 1], [1, 2]])
        self.assertEqual(
            [slot["zone_order"] for slot in attrs["slots"]], ["ordered", "auto"]
        )
        self.assertEqual(attrs["slots"][0]["zone_names"], ["Back lawn", "Front lawn"])


class CalendarEventZonesTests(_NamedZones):
    def _event(self, slot: dict[str, Any], language: str = "en") -> CalendarEvent:
        device = _device()
        return CALENDAR_MODULE._slot_to_event(
            slot,
            dt.date(2026, 9, 21),
            dt.UTC,
            language,
            HELPERS.schedule_slot_zones(device, slot),
        )

    def test_summary_names_the_zones_in_order(self) -> None:
        self.assertEqual(self._event(MONDAY_MORNING).summary, "Mowing: Back lawn, Front lawn")

    def test_description_states_the_order(self) -> None:
        description = self._event(MONDAY_MORNING).description
        self.assertIn("Zones: Back lawn, Front lawn (in this order)", description)
        auto = self._event(MONDAY_AFTERNOON).description
        self.assertIn("(order chosen by the mower)", auto)

    def test_french_summary_spacing(self) -> None:
        self.assertEqual(
            self._event(MONDAY_MORNING, "fr").summary, "Tonte : Back lawn, Front lawn"
        )

    def test_without_zones_the_event_is_unchanged(self) -> None:
        event = CALENDAR_MODULE._slot_to_event(
            MONDAY_MORNING, dt.date(2026, 9, 21), dt.UTC, "en"
        )
        self.assertEqual(event.summary, "Mowing")
        self.assertNotIn("Zones", event.description)


class ScheduleLanguageCoverageTests(unittest.TestCase):
    """Schedule and calendar text must exist in every supported UI language."""

    LANGUAGES = {path.stem for path in (PACKAGE_DIR / "translations").glob("*.json")}

    def test_every_translation_language_has_schedule_text(self) -> None:
        self.assertEqual(set(HELPERS.SCHEDULE_DAY_LABELS), self.LANGUAGES)
        self.assertEqual(set(HELPERS.SCHEDULE_TEXT_LABELS), self.LANGUAGES)
        self.assertEqual(set(CALENDAR_MODULE.EVENT_SUMMARY), self.LANGUAGES)
        self.assertEqual(set(CALENDAR_MODULE.EVENT_LABELS), self.LANGUAGES)

    def test_every_language_has_every_key(self) -> None:
        for table in (
            HELPERS.SCHEDULE_DAY_LABELS,
            HELPERS.SCHEDULE_TEXT_LABELS,
            CALENDAR_MODULE.EVENT_LABELS,
        ):
            reference = set(table["en"])
            for language, labels in table.items():
                self.assertEqual(set(labels), reference, language)

    def test_calendar_renders_in_every_language(self) -> None:
        for language in self.LANGUAGES:
            event = CALENDAR_MODULE._slot_to_event(
                MONDAY_MORNING,
                dt.date(2026, 9, 21),
                dt.UTC,
                language,
                {"zones": [1], "zone_names": ["Front lawn"], "zone_order": "ordered"},
            )
            self.assertTrue(event.summary.endswith("Front lawn"), language)


class CalendarWindowTests(unittest.TestCase):
    """The calendar only publishes occurrences around today."""

    def _calendar(self, options: dict[str, Any]) -> Any:
        calendar = CALENDAR_MODULE.WorxVisionScheduleCalendar.__new__(
            CALENDAR_MODULE.WorxVisionScheduleCalendar
        )
        calendar._entry = SimpleNamespace(options=options)
        calendar.requested = []
        calendar._events_between = lambda start, end: calendar.requested.append((start, end)) or ["event"]
        return calendar

    def _get(self, calendar: Any, start: dt.datetime, end: dt.datetime) -> list[Any]:
        import asyncio

        return asyncio.run(calendar.async_get_events(None, start, end))

    def test_window_is_whole_days_around_today(self) -> None:
        first, last = CALENDAR_MODULE.calendar_window(NOW, 7)
        self.assertEqual(first, dt.datetime(2026, 9, 15, tzinfo=dt.UTC))
        self.assertEqual(last, dt.datetime(2026, 9, 30, tzinfo=dt.UTC))

    def test_default_clamps_a_wide_request_to_one_week_each_side(self) -> None:
        calendar = self._calendar({})
        self._get(calendar, dt.datetime(2025, 1, 1, tzinfo=dt.UTC), dt.datetime(2027, 1, 1, tzinfo=dt.UTC))
        self.assertEqual(calendar.requested, [(
            dt.datetime(2026, 9, 15, tzinfo=dt.UTC), dt.datetime(2026, 9, 30, tzinfo=dt.UTC)
        )])

    def test_option_changes_the_window(self) -> None:
        calendar = self._calendar({"calendar_window_days": 30})
        self._get(calendar, dt.datetime(2025, 1, 1, tzinfo=dt.UTC), dt.datetime(2027, 1, 1, tzinfo=dt.UTC))
        start, end = calendar.requested[0]
        self.assertEqual(start, dt.datetime(2026, 8, 23, tzinfo=dt.UTC))
        self.assertEqual(end, dt.datetime(2026, 10, 23, tzinfo=dt.UTC))

    def test_narrow_request_inside_the_window_is_untouched(self) -> None:
        calendar = self._calendar({})
        start = dt.datetime(2026, 9, 21, tzinfo=dt.UTC)
        end = dt.datetime(2026, 9, 28, tzinfo=dt.UTC)
        self._get(calendar, start, end)
        self.assertEqual(calendar.requested, [(start, end)])

    def test_request_outside_the_window_returns_nothing(self) -> None:
        calendar = self._calendar({})
        events = self._get(calendar, dt.datetime(2026, 11, 1, tzinfo=dt.UTC), dt.datetime(2026, 11, 8, tzinfo=dt.UTC))
        self.assertEqual(events, [])
        self.assertEqual(calendar.requested, [])


if __name__ == "__main__":
    unittest.main()
