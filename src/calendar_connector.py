"""Kalender-Connector — liest lokale .ics-Dateien und CalDAV-Feeds."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CalendarEvent:
    id: str
    title: str
    start: datetime
    end: Optional[datetime]
    description: str
    location: str
    calendar_name: str
    all_day: bool
    color: str


def _color_from_name(name: str) -> str:
    """Derive a deterministic color from a calendar name."""
    _palette = [
        "#00d4ff", "#a78bfa", "#34d399", "#f59e0b",
        "#f472b6", "#60a5fa", "#fb923c", "#4ade80",
    ]
    idx = int(hashlib.md5(name.encode()).hexdigest(), 16) % len(_palette)
    return _palette[idx]


def _unfold_lines(lines: list[str]) -> list[str]:
    """Unfold RFC 5545 folded lines (continuation lines start with space or tab)."""
    unfolded: list[str] = []
    for raw in lines:
        line = raw.rstrip("\r\n")
        if line and line[0] in (" ", "\t") and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def _parse_ics_datetime(value: str, tzid: str | None) -> datetime:
    """Parse a DTSTART/DTEND value into a datetime.

    Handles:
    - YYYYMMDD              (all-day, returns midnight naive)
    - YYYYMMDDTHHmmss       (naive local)
    - YYYYMMDDTHHmmssZ      (UTC)
    """
    value = value.strip()

    if len(value) == 8:
        # DATE-only: 20240315
        d = date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
        return datetime(d.year, d.month, d.day, 0, 0, 0)

    if "T" in value:
        date_part = value[:8]
        time_part = value[9:15] if len(value) >= 15 else value[9:]
        year = int(date_part[0:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
        hour = int(time_part[0:2]) if len(time_part) >= 2 else 0
        minute = int(time_part[2:4]) if len(time_part) >= 4 else 0
        second = int(time_part[4:6]) if len(time_part) >= 6 else 0

        if value.endswith("Z"):
            return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        else:
            return datetime(year, month, day, hour, minute, second)

    # Fallback: try direct date parse
    try:
        d = date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
        return datetime(d.year, d.month, d.day, 0, 0, 0)
    except Exception as exc:
        raise ValueError(f"Cannot parse datetime value: {value!r}") from exc


def parse_ics_file(
    path: Path,
    calendar_name: str = "",
    color: str = "",
) -> list[CalendarEvent]:
    """Parse a single .ics file and return a list of CalendarEvent objects."""
    events: list[CalendarEvent] = []

    if not calendar_name:
        calendar_name = path.stem

    if not color:
        color = _color_from_name(calendar_name)

    try:
        raw_text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Kalender-Datei nicht lesbar: %s — %s", path, exc)
        return events

    # Split by both CRLF and LF
    raw_lines = raw_text.splitlines(keepends=True)
    lines = _unfold_lines(raw_lines)

    # Find all VEVENT blocks
    in_event = False
    current: dict[str, str] = {}

    for line in lines:
        line_stripped = line.strip()

        if line_stripped == "BEGIN:VEVENT":
            in_event = True
            current = {}
            continue

        if line_stripped == "END:VEVENT":
            in_event = False
            event = _build_event(current, calendar_name, color)
            if event is not None:
                events.append(event)
            current = {}
            continue

        if not in_event:
            continue

        # Parse property line: NAME;PARAM=val:value or NAME:value
        if ":" not in line_stripped:
            continue

        colon_idx = line_stripped.index(":")
        prop_full = line_stripped[:colon_idx]
        prop_value = line_stripped[colon_idx + 1:]

        # Extract base property name (strip parameters)
        prop_name = prop_full.split(";")[0].upper()

        # Special handling for DTSTART / DTEND with TZID or VALUE param
        if prop_name in ("DTSTART", "DTEND"):
            # Store both the full prop key (for TZID extraction) and value
            current[prop_name + "_FULL"] = prop_full
            current[prop_name] = prop_value
        elif prop_name == "SUMMARY":
            current["SUMMARY"] = prop_value
        elif prop_name == "DESCRIPTION":
            current["DESCRIPTION"] = prop_value
        elif prop_name == "LOCATION":
            current["LOCATION"] = prop_value
        elif prop_name == "UID":
            current["UID"] = prop_value

    return events


def _extract_tzid(prop_full: str) -> str | None:
    """Extract TZID parameter value from a property like DTSTART;TZID=Europe/Berlin."""
    for param in prop_full.split(";")[1:]:
        if param.upper().startswith("TZID="):
            return param[5:]
    return None


def _build_event(
    props: dict[str, str],
    calendar_name: str,
    color: str,
) -> CalendarEvent | None:
    """Build a CalendarEvent from parsed VEVENT properties."""
    dt_start_raw = props.get("DTSTART", "")
    if not dt_start_raw:
        return None

    dt_start_full = props.get("DTSTART_FULL", "DTSTART")
    tzid = _extract_tzid(dt_start_full)

    try:
        start = _parse_ics_datetime(dt_start_raw, tzid)
    except Exception as exc:
        logger.debug("DTSTART parse error: %s — %s", dt_start_raw, exc)
        return None

    # Determine all_day
    all_day = len(dt_start_raw.strip()) == 8 or "VALUE=DATE" in dt_start_full.upper()

    end: datetime | None = None
    dt_end_raw = props.get("DTEND", "")
    if dt_end_raw:
        dt_end_full = props.get("DTEND_FULL", "DTEND")
        end_tzid = _extract_tzid(dt_end_full)
        try:
            end = _parse_ics_datetime(dt_end_raw, end_tzid)
        except Exception as exc:
            logger.debug("DTEND parse error: %s — %s", dt_end_raw, exc)

    uid = props.get("UID", "")
    title = props.get("SUMMARY", "(Kein Titel)")
    description = props.get("DESCRIPTION", "")
    location = props.get("LOCATION", "")

    # Normalise description (replace escaped newlines)
    description = description.replace("\\n", "\n").replace("\\,", ",")
    location = location.replace("\\,", ",")

    event_id = uid or f"{calendar_name}_{start.isoformat()}_{title}"

    return CalendarEvent(
        id=event_id,
        title=title,
        start=start,
        end=end,
        description=description,
        location=location,
        calendar_name=calendar_name,
        all_day=all_day,
        color=color,
    )


def _collect_ics_paths(cfg: dict) -> list[tuple[Path, str]]:
    """Collect all .ics file paths from config and inbox/archive folders.

    Returns list of (path, calendar_name) tuples.
    """
    result: list[tuple[Path, str]] = []
    seen: set[Path] = set()

    def _add(p: Path, name: str = "") -> None:
        resolved = p.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        result.append((p, name or p.stem))

    # From calendar_paths in config
    for entry in cfg.get("calendar_paths", []):
        candidate = Path(str(entry)).expanduser()
        if candidate.is_dir():
            for ics in candidate.glob("*.ics"):
                _add(ics)
        elif candidate.is_file() and candidate.suffix.lower() == ".ics":
            _add(candidate)
        # Silently skip non-existent paths

    # Scan inbox and archive folders for .ics files
    for folder_key in ("inbox", "archive"):
        folder_str = cfg.get("paths", {}).get(folder_key, "")
        if folder_str:
            folder = Path(folder_str).expanduser()
            if folder.is_dir():
                for ics in folder.rglob("*.ics"):
                    _add(ics)

    return result


def _naive_now() -> datetime:
    """Current local datetime without tzinfo (for comparison with naive datetimes)."""
    return datetime.now()


def _as_naive(dt: datetime) -> datetime:
    """Strip timezone info to make datetime naive (for uniform comparison)."""
    if dt.tzinfo is not None:
        # Convert UTC to local naive approximation
        return dt.replace(tzinfo=None)
    return dt


def load_calendar_events(cfg: dict, days_ahead: int = 30) -> list[CalendarEvent]:
    """Load all calendar events from configured sources.

    Filters to events starting within days_ahead days from today, sorted by start.
    """
    ics_paths = _collect_ics_paths(cfg)

    all_events: list[CalendarEvent] = []
    for path, cal_name in ics_paths:
        try:
            parsed = parse_ics_file(path, calendar_name=cal_name)
            all_events.extend(parsed)
        except Exception as exc:
            logger.warning("Fehler beim Parsen von %s: %s", path, exc)

    now_naive = _naive_now()
    cutoff = now_naive + timedelta(days=days_ahead)

    filtered: list[CalendarEvent] = []
    for ev in all_events:
        start_naive = _as_naive(ev.start)
        if start_naive >= now_naive and start_naive <= cutoff:
            filtered.append(ev)

    filtered.sort(key=lambda e: _as_naive(e.start))
    return filtered


def get_today_events(cfg: dict) -> list[CalendarEvent]:
    """Return events starting today."""
    today = date.today()
    all_events = load_calendar_events(cfg, days_ahead=1)

    result: list[CalendarEvent] = []
    for ev in all_events:
        start_naive = _as_naive(ev.start)
        if start_naive.date() == today:
            result.append(ev)

    # Also include events that span today (started before today but end after)
    # For that we do a broader load and filter
    broader = load_calendar_events(cfg, days_ahead=0)
    seen_ids = {e.id for e in result}
    for ev in broader:
        if ev.id in seen_ids:
            continue
        start_naive = _as_naive(ev.start)
        if start_naive.date() == today:
            result.append(ev)

    result.sort(key=lambda e: _as_naive(e.start))
    return result


def get_upcoming_events(cfg: dict, days: int = 7) -> list[CalendarEvent]:
    """Return events starting in the next N days."""
    return load_calendar_events(cfg, days_ahead=days)
