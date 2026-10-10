"""Persistent daily statistics derived from cumulative Worx counters."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from typing import Any

# A mowing streak that resumes within this delay continues the same session
# (short stops, a STOP press, a hop between zones). A longer break, such as a
# trip back to the station to charge, starts a new session.
SESSION_MERGE_SECONDS = 600


def _as_float(value: Any) -> float | None:
    """Return a finite non-negative float."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result < 0 or result != result:
        return None
    return result


@dataclass
class DailyAreaRecord:
    """State needed to turn a cumulative area counter into a daily value."""

    day: str
    baseline_total: float
    last_total: float


@dataclass
class DailyMowingRecord:
    """Locally observed blade-active time for one day."""

    day: str
    seconds: float = 0.0


@dataclass
class MowingSession:
    """One locally observed mowing session."""

    start: datetime
    end: datetime | None
    seconds: float
    last_seen: datetime
    zones: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Return the serializable form."""
        return {
            "start": self.start.isoformat(),
            "end": None if self.end is None else self.end.isoformat(),
            "seconds": self.seconds,
            "last_seen": self.last_seen.isoformat(),
            "zones": list(self.zones),
        }

    @classmethod
    def from_dict(cls, raw: Any) -> MowingSession | None:
        """Restore a session, or return None when the data is unusable."""
        if not isinstance(raw, dict):
            return None
        start = _as_datetime(raw.get("start"))
        last_seen = _as_datetime(raw.get("last_seen"))
        seconds = _as_float(raw.get("seconds"))
        if start is None or last_seen is None or seconds is None:
            return None
        end = None
        if raw.get("end") is not None:
            end = _as_datetime(raw.get("end"))
            if end is None:
                return None
        zones = raw.get("zones")
        zones = [str(zone) for zone in zones] if isinstance(zones, list) else []
        return cls(start, end, seconds, last_seen, zones)


def _as_datetime(value: Any) -> datetime | None:
    """Return a timezone-aware datetime parsed from ISO text."""
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        return None
    return result if result.tzinfo is not None else None


class DailyStatisticsTracker:
    """Track daily area and mowing time without trusting counter labels.

    Keyed by mower serial number and persisted through Home Assistant
    storage, so the daily baselines survive restarts, entity renames and
    entity re-creation, and every daily sensor shares the same baseline.
    """

    def __init__(self, stored: dict[str, Any] | None = None) -> None:
        """Restore valid records from storage."""
        self._area: dict[str, DailyAreaRecord] = {}
        self._mowing: dict[str, DailyMowingRecord] = {}
        self._active_since: dict[str, datetime] = {}
        self._yesterday: dict[str, DailyMowingRecord] = {}
        self._session: dict[str, MowingSession] = {}
        self._last_session: dict[str, MowingSession] = {}
        self._session_since: dict[str, datetime] = {}

        stored = stored if isinstance(stored, dict) else {}
        for serial, raw in (stored.get("area") or {}).items():
            if not isinstance(raw, dict):
                continue
            baseline = _as_float(raw.get("baseline_total"))
            last_total = _as_float(raw.get("last_total"))
            day = raw.get("day")
            if isinstance(day, str) and baseline is not None and last_total is not None:
                self._area[str(serial)] = DailyAreaRecord(
                    day=day,
                    baseline_total=baseline,
                    last_total=last_total,
                )

        for serial, raw in (stored.get("mowing") or {}).items():
            if not isinstance(raw, dict):
                continue
            seconds = _as_float(raw.get("seconds"))
            day = raw.get("day")
            if isinstance(day, str) and seconds is not None:
                self._mowing[str(serial)] = DailyMowingRecord(
                    day=day,
                    seconds=seconds,
                )

        for serial, raw in (stored.get("yesterday") or {}).items():
            if not isinstance(raw, dict):
                continue
            seconds = _as_float(raw.get("seconds"))
            day = raw.get("day")
            if isinstance(day, str) and seconds is not None:
                self._yesterday[str(serial)] = DailyMowingRecord(day, seconds)

        for key, target in (
            ("session", self._session),
            ("last_session", self._last_session),
        ):
            for serial, raw in (stored.get(key) or {}).items():
                session = MowingSession.from_dict(raw)
                if session is not None:
                    target[str(serial)] = session

    def as_dict(self) -> dict[str, Any]:
        """Return the serializable state used by Home Assistant storage."""
        return {
            "area": {
                serial: {
                    "day": record.day,
                    "baseline_total": record.baseline_total,
                    "last_total": record.last_total,
                }
                for serial, record in self._area.items()
            },
            "mowing": {
                serial: {
                    "day": record.day,
                    "seconds": record.seconds,
                }
                for serial, record in self._mowing.items()
            },
            "yesterday": {
                serial: {"day": record.day, "seconds": record.seconds}
                for serial, record in self._yesterday.items()
            },
            "session": {
                serial: session.as_dict()
                for serial, session in self._session.items()
            },
            "last_session": {
                serial: session.as_dict()
                for serial, session in self._last_session.items()
            },
        }

    def update(
        self,
        serial: str,
        *,
        area_total: Any,
        mowing_active: bool,
        now_utc: datetime,
        local_day: date,
        local_midnight_utc: datetime,
        zone: str | None = None,
    ) -> bool:
        """Update one mower and return whether persistent data changed."""
        changed = self._update_area(serial, area_total, local_day)
        changed |= self._update_mowing(
            serial,
            mowing_active,
            now_utc,
            local_day,
            local_midnight_utc,
        )
        changed |= self._update_session(serial, mowing_active, now_utc, zone)
        return changed

    def _update_area(self, serial: str, value: Any, local_day: date) -> bool:
        total = _as_float(value)
        if total is None:
            return False

        day_text = local_day.isoformat()
        record = self._area.get(serial)
        if record is None:
            self._area[serial] = DailyAreaRecord(day_text, total, total)
            return True

        changed = False
        if record.day != day_text:
            try:
                previous_day = date.fromisoformat(record.day)
            except ValueError:
                previous_day = None

            # When only one day elapsed, retain the last counter observed before
            # midnight. For longer gaps, do not attribute several days to today.
            if (
                previous_day is not None
                and (local_day - previous_day).days == 1
                and total >= record.last_total
            ):
                record.baseline_total = record.last_total
            else:
                record.baseline_total = total
            record.day = day_text
            changed = True

        # A lower value means the cloud counter was reset or replaced.
        if total < record.baseline_total or total < record.last_total:
            record.baseline_total = total
            changed = True

        if total != record.last_total:
            record.last_total = total
            changed = True
        return changed

    def _update_mowing(
        self,
        serial: str,
        active: bool,
        now_utc: datetime,
        local_day: date,
        local_midnight_utc: datetime,
    ) -> bool:
        day_text = local_day.isoformat()
        record = self._mowing.get(serial)
        active_since = self._active_since.get(serial)
        changed = False

        if record is not None and record.day != day_text:
            # Keep the finished day: what was counted, plus the part of a
            # streak still running at the last update, up to midnight.
            previous = record.seconds
            if active_since is not None:
                stop = min(now_utc, local_midnight_utc)
                previous += max(0.0, (stop - active_since).total_seconds())
            self._yesterday[serial] = DailyMowingRecord(record.day, previous)

        if record is None or record.day != day_text:
            seconds = 0.0
            if active and active_since is not None:
                # A streak crossing midnight only credits today with the part
                # mowed after local midnight.
                start = max(active_since, local_midnight_utc)
                seconds = max(0.0, (now_utc - start).total_seconds())
            self._mowing[serial] = DailyMowingRecord(day_text, seconds)
            record = self._mowing[serial]
            self._active_since.pop(serial, None)
            active_since = None
            changed = True

        if active:
            if active_since is not None:
                elapsed = max(0.0, (now_utc - active_since).total_seconds())
                if elapsed:
                    record.seconds += elapsed
                    changed = True
            self._active_since[serial] = now_utc
        elif active_since is not None:
            elapsed = max(0.0, (now_utc - active_since).total_seconds())
            if elapsed:
                record.seconds += elapsed
                changed = True
            self._active_since.pop(serial, None)

        return changed

    def _update_session(
        self,
        serial: str,
        active: bool,
        now_utc: datetime,
        zone: str | None,
    ) -> bool:
        session = self._session.get(serial)
        since = self._session_since.get(serial)
        changed = False

        if active:
            if session is None or (
                session.end is not None
                and (now_utc - session.end).total_seconds() > SESSION_MERGE_SECONDS
            ):
                session = MowingSession(now_utc, None, 0.0, now_utc)
                self._session[serial] = session
                since = None
                changed = True
            elif session.end is not None:
                # Mowing resumed shortly after a stop: same session.
                session.end = None
                changed = True
            if since is not None:
                elapsed = max(0.0, (now_utc - since).total_seconds())
                if elapsed:
                    session.seconds += elapsed
                    changed = True
            self._session_since[serial] = now_utc
            if session.last_seen != now_utc:
                session.last_seen = now_utc
                changed = True
            if zone and zone not in session.zones:
                session.zones.append(zone)
                changed = True
            return changed

        if session is not None and session.end is None:
            if since is not None:
                session.seconds += max(0.0, (now_utc - since).total_seconds())
                session.end = now_utc
            else:
                # Home Assistant restarted while the mower was mowing: the
                # last moment it was seen mowing is the best end we have.
                session.end = session.last_seen
            self._last_session[serial] = replace(session, zones=list(session.zones))
            changed = True
        self._session_since.pop(serial, None)
        return changed

    def area_mowed_today(self, serial: str, local_day: date) -> float | None:
        """Return the cumulative-counter delta for the requested local day."""
        record = self._area.get(serial)
        if record is None:
            return None
        if record.day != local_day.isoformat():
            return 0.0
        return round(max(0.0, record.last_total - record.baseline_total), 2)

    def area_details(self, serial: str) -> dict[str, Any]:
        """Return diagnostic details for a daily-area calculation."""
        record = self._area.get(serial)
        if record is None:
            return {}
        return {
            "baseline_date": record.day,
            "baseline_total": record.baseline_total,
            "area_mowed_total": record.last_total,
        }

    def mowing_minutes_today(
        self, serial: str, now_utc: datetime, local_day: date
    ) -> float:
        """Return locally observed blade-active minutes for one day."""
        record = self._mowing.get(serial)
        if record is None or record.day != local_day.isoformat():
            return 0.0

        seconds = record.seconds
        active_since = self._active_since.get(serial)
        if active_since is not None:
            seconds += max(0.0, (now_utc - active_since).total_seconds())
        return round(seconds / 60, 2)

    def mowing_minutes_yesterday(
        self, serial: str, now_utc: datetime, local_day: date
    ) -> float | None:
        """Return locally observed mowing minutes for the previous local day.

        None means nothing is known yet, 0 means no mowing was seen.
        """
        yesterday = (local_day - timedelta(days=1)).isoformat()
        record = self._yesterday.get(serial)
        if record is not None and record.day == yesterday:
            return round(record.seconds / 60, 2)

        # Read right after midnight, before the first update of the new day.
        current = self._mowing.get(serial)
        if current is not None and current.day == yesterday:
            seconds = current.seconds
            active_since = self._active_since.get(serial)
            if active_since is not None:
                seconds += max(0.0, (now_utc - active_since).total_seconds())
            return round(seconds / 60, 2)

        if record is None and current is None:
            return None
        return 0.0

    def last_session(self, serial: str) -> dict[str, Any] | None:
        """Return the last finished mowing session, if one was seen."""
        session = self._last_session.get(serial)
        if session is None or session.end is None:
            return None
        return {
            "start": session.start,
            "end": session.end,
            "duration_min": round(session.seconds / 60, 1),
            "zones": list(session.zones),
        }
