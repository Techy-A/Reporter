"""Minimal RFC 5545 calendar file for an interview."""
from __future__ import annotations

from datetime import datetime, timedelta


def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n").replace("\r", "")


def build_ics(*, uid: str, start: datetime, minutes: int, summary: str, location: str) -> str:
    fmt = "%Y%m%dT%H%M%SZ"
    end = start + timedelta(minutes=minutes)
    now = datetime.utcnow().strftime(fmt)
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//PeoplePilot//Interview//EN", "METHOD:PUBLISH",
        "BEGIN:VEVENT", f"UID:{_esc(uid)}@peoplepilot", f"DTSTAMP:{now}",
        f"DTSTART:{start.strftime(fmt)}", f"DTEND:{end.strftime(fmt)}",
        f"SUMMARY:{_esc(summary)}", f"LOCATION:{_esc(location)}",
        "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"
