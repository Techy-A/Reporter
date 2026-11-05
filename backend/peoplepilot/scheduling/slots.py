"""Find free interview slots. Pure functions (no DB), so they are easy to test."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

STEP = timedelta(minutes=30)


@dataclass(frozen=True)
class Slot:
    start: datetime  # naive UTC
    interviewer_id: int


@dataclass(frozen=True)
class Preference:
    after_hour: int | None = None  # local hour
    before_hour: int | None = None
    on_date: date | None = None  # local date


def _to_utc_naive(local_dt: datetime) -> datetime:
    return local_dt.astimezone(timezone.utc).replace(tzinfo=None)


def _local(utc_naive: datetime, tz: ZoneInfo) -> datetime:
    return utc_naive.replace(tzinfo=timezone.utc).astimezone(tz)


def overlaps(a_start: datetime, a_len: timedelta, b_start: datetime, b_len: timedelta) -> bool:
    return a_start < b_start + b_len and b_start < a_start + a_len


def find_slots(
    *,
    window_start: datetime,
    window_end: datetime,
    day_start_hour: int,
    day_end_hour: int,
    duration: timedelta,
    buffer: timedelta,
    interviewer_ids: list[int],
    busy: dict[int, list[tuple[datetime, timedelta]]],
    tz_name: str,
    now: datetime,
    limit: int,
    preference: Preference | None = None,
    min_notice: timedelta = timedelta(hours=3),
    exclude: set[datetime] | None = None,
) -> list[Slot]:
    """Return up to `limit` slots, spread across different days where possible.

    `busy[interviewer_id]` holds (start, length) of existing bookings in naive UTC; the
    buffer is applied on both sides of each booking.
    """
    if not interviewer_ids or limit <= 0:
        return []
    tz = ZoneInfo(tz_name)
    pref = preference or Preference()
    exclude = exclude or set()
    earliest = now + min_notice

    first_day = _local(max(window_start, now), tz).date()
    last_day = _local(window_end, tz).date()
    by_day: dict[date, list[Slot]] = {}

    day = first_day
    while day <= last_day:
        if day.weekday() < 6 and (pref.on_date is None or pref.on_date == day):  # Mon-Sat
            start_h = max(day_start_hour, pref.after_hour if pref.after_hour is not None else 0)
            end_h = min(day_end_hour, pref.before_hour if pref.before_hour is not None else 24)
            t = datetime.combine(day, time(hour=start_h), tzinfo=tz)
            day_end = datetime.combine(day, time(hour=0), tzinfo=tz) + timedelta(hours=end_h)
            while t + duration <= day_end:
                start_utc = _to_utc_naive(t)
                if window_start <= start_utc <= window_end and start_utc >= earliest and start_utc not in exclude:
                    for iid in interviewer_ids:
                        clash = any(
                            overlaps(start_utc - buffer, duration + 2 * buffer, b_start, b_len)
                            for b_start, b_len in busy.get(iid, [])
                        )
                        if not clash:
                            by_day.setdefault(day, []).append(Slot(start_utc, iid))
                            break
                t += STEP
        day += timedelta(days=1)

    # Spread: take the first slot of each day, then the next ones, round-robin.
    picked: list[Slot] = []
    days = sorted(by_day)
    i = 0
    while len(picked) < limit and any(i < len(by_day[d]) for d in days):
        for d in days:
            if i < len(by_day[d]) and len(picked) < limit:
                picked.append(by_day[d][i])
        i += 1
    return sorted(picked, key=lambda s: s.start)


def format_slot(start_utc: datetime, tz_name: str) -> str:
    """Short label that fits a WhatsApp button (<= 20 chars), e.g. 'Tue 12 Nov, 11:00'."""
    local = _local(start_utc, ZoneInfo(tz_name))
    return local.strftime("%a %d %b, %H:%M")
