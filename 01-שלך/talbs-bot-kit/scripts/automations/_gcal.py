"""Google Calendar via Secret iCal URL.

Read-only access. No OAuth, no API key. Just an HTTP GET to the secret feed URL
that the user copies from Google Calendar Settings → Integrate calendar.

Uses the `icalendar` library for parsing (pure Python, pip-installed).
"""
from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

import requests
from icalendar import Calendar
from dateutil.rrule import rrulestr


def fetch_ical(url: str, timeout: int = 30) -> str:
    """GET the iCal feed. Returns the raw ICS text."""
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "TalBot/1.0"})
    r.raise_for_status()
    return r.text


def _to_local_dt(value: Any, tz: ZoneInfo) -> dt.datetime | dt.date:
    """Normalize an ICS DTSTART/DTEND value to local timezone datetime, or date for all-day."""
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(tz)
    if isinstance(value, dt.date):
        return value
    raise TypeError(f"Unexpected dtstart type: {type(value)}")


def _occurs_today(event, today_start: dt.datetime, today_end: dt.datetime,
                  tz: ZoneInfo) -> dt.datetime | dt.date | None:
    """Return the today-occurrence start time if this event happens today, else None.

    Handles single events and basic recurring events (RRULE).
    """
    dtstart_raw = event.get("DTSTART")
    if dtstart_raw is None:
        return None
    dtstart_val = dtstart_raw.dt
    is_all_day = isinstance(dtstart_val, dt.date) and not isinstance(dtstart_val, dt.datetime)

    rrule_prop = event.get("RRULE")

    if rrule_prop is None:
        # Single event — check if its start is today (local TZ).
        if is_all_day:
            return dtstart_val if dtstart_val == today_start.date() else None
        local = _to_local_dt(dtstart_val, tz)
        if today_start <= local < today_end:
            return local
        return None

    # Recurring event — expand RRULE between today_start and today_end.
    try:
        rrule_str = rrule_prop.to_ical().decode("utf-8") if hasattr(rrule_prop, "to_ical") else str(rrule_prop)
    except Exception:
        return None

    # rrule needs a dtstart in datetime form. For all-day we use midnight UTC.
    if is_all_day:
        dt0 = dt.datetime.combine(dtstart_val, dt.time.min, tzinfo=dt.timezone.utc)
    else:
        if dtstart_val.tzinfo is None:
            dt0 = dtstart_val.replace(tzinfo=dt.timezone.utc)
        else:
            dt0 = dtstart_val

    try:
        rule = rrulestr(f"RRULE:{rrule_str}", dtstart=dt0)
    except Exception:
        return None

    # Pull EXDATE exceptions
    exdates: set[dt.datetime] = set()
    exdate_prop = event.get("EXDATE")
    if exdate_prop is not None:
        items = exdate_prop if isinstance(exdate_prop, list) else [exdate_prop]
        for ex in items:
            for d in ex.dts:
                v = d.dt
                if isinstance(v, dt.datetime):
                    if v.tzinfo is None:
                        v = v.replace(tzinfo=dt.timezone.utc)
                    exdates.add(v.astimezone(tz))
                elif isinstance(v, dt.date):
                    exdates.add(dt.datetime.combine(v, dt.time.min, tzinfo=tz))

    # Search a window slightly wider than today (in UTC) to catch tz-edge cases
    window_start = today_start - dt.timedelta(hours=1)
    window_end = today_end + dt.timedelta(hours=1)
    try:
        occurrences = list(rule.between(window_start, window_end, inc=True))
    except Exception:
        return None
    for occ in occurrences:
        local = occ.astimezone(tz)
        if today_start <= local < today_end and local not in exdates:
            return local
    return None


def list_events_today(ics_text: str, tz: str = "Asia/Jerusalem") -> list[dict[str, Any]]:
    """Parse ICS, return today's events as simple dicts sorted by time."""
    zone = ZoneInfo(tz)
    now_local = dt.datetime.now(zone)
    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + dt.timedelta(days=1)

    cal = Calendar.from_ical(ics_text)
    out: list[dict[str, Any]] = []

    for component in cal.walk("VEVENT"):
        status = str(component.get("STATUS", "")).upper()
        if status == "CANCELLED":
            continue

        when = _occurs_today(component, today_start, today_end, zone)
        if when is None:
            continue

        summary = str(component.get("SUMMARY", "(ללא כותרת)")).strip()
        if isinstance(when, dt.datetime):
            time_label = when.strftime("%H:%M")
            all_day = False
            sort_key = when
        else:
            time_label = "כל היום"
            all_day = True
            sort_key = dt.datetime.combine(today_start.date(), dt.time.min, tzinfo=zone)

        out.append({
            "time": time_label,
            "title": summary,
            "all_day": all_day,
            "_sort": sort_key,
        })

    out.sort(key=lambda e: (not e["all_day"], e["_sort"]))
    for e in out:
        e.pop("_sort", None)
    # All-day events at top, then chronological
    out.sort(key=lambda e: (0 if e["all_day"] else 1, e["time"]))
    return out


def format_morning_agenda(name: str, events: list[dict[str, Any]]) -> str:
    """Format events into the exact Hebrew message Tal used to send."""
    header = f"היי {name} בוקר טוב 😊"
    footer = ("\n\nהאם יש לך משימה בשבילי להיום?\n\n"
              f"יום מקסים {name}, תני בראש!\n\n"
              "תזכורת: כל יום הוא יום לעשות מעשים טובים 🔥")

    if not events:
        body = "\nאין לך פגישות היום, יום פנוי 🎉"
    else:
        lines = ["\nסדר היום שלך הוא:"]
        for ev in events:
            lines.append(f"✅ {ev['time']} - {ev['title']}")
        body = "\n".join(lines)

    return f"{header}{body}{footer}"
