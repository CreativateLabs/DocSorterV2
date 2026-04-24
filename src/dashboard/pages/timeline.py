"""Zeitraumsuche — „Wann war ich wo?" — chronologische Gesamtübersicht.

Durchsucht alle Datenquellen mit Datumsfilter:
  Dokumente (Archiv/Inbox/Pruefung) · Todos · Rechnungen · Ausgaben · E-Mails
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path

from nicegui import run, ui

from ..theme import callout, page_header, section_title, empty_state


# ---------------------------------------------------------------------------
# Datumshelfer
# ---------------------------------------------------------------------------

_DATE_RE = [
    re.compile(r'(\d{4})[_\-](\d{2})[_\-](\d{2})'),   # YYYY-MM-DD
    re.compile(r'(\d{2})[_\-\.](\d{2})[_\-\.](\d{4})'), # DD.MM.YYYY
]
_MONTH_DE = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
}


def _file_date(path: Path) -> date:
    """Datum aus Dateiname extrahieren, Fallback auf mtime."""
    name = path.stem
    m = _DATE_RE[0].search(name)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = _DATE_RE[1].search(name)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).date()
    except Exception:
        return date.today()


def _parse_iso(s: str) -> date | None:
    """ISO-String (YYYY-MM-DD oder Datetime-ISO) -> date."""
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except Exception:
        return None


def _ym(d: date) -> str:
    return d.strftime("%Y-%m")


# ---------------------------------------------------------------------------
# Daten sammeln
# ---------------------------------------------------------------------------

_TYPE_META = {
    "doc":      ("📄", "#00d4ff", "Dokument"),
    "todo":     ("✅", "#a78bfa", "Todo"),
    "invoice":  ("🧾", "#00e87d", "Rechnung"),
    "expense":  ("💶", "#ff9f0a", "Ausgabe"),
    "email":    ("📧", "#38bdf8", "E-Mail"),
    "calendar": ("📅", "#c084fc", "Termin"),
}


def _collect_events(
    date_from: date,
    date_to: date,
    keyword: str = "",
    types: set[str] | None = None,
) -> list[dict]:
    """Alle Ereignisse im Zeitraum [date_from, date_to] sammeln."""
    events: list[dict] = []
    kw = keyword.lower().strip() if keyword else ""
    active_types = types or {"doc", "todo", "invoice", "expense", "email", "calendar"}

    # ── Dokumente ──────────────────────────────────────────────────────────
    if "doc" in active_types:
        try:
            from ...config import load_config
            cfg = load_config()
            paths_cfg = cfg.get("paths", {})
            for path_key, label, color in [
                ("archive", "Archiv",   "#00d4ff"),
                ("inbox",   "Inbox",    "#38bdf8"),
                ("review",  "Prüfung",  "#ff9f0a"),
            ]:
                folder = Path(paths_cfg.get(path_key, "")).expanduser()
                if not folder.exists():
                    continue
                for f in folder.rglob("*"):
                    if not f.is_file():
                        continue
                    d = _file_date(f)
                    if not (date_from <= d <= date_to):
                        continue
                    if kw and kw not in f.name.lower():
                        continue
                    # linked todos
                    try:
                        from ...assistant_store import find_todos_linked_to_doc
                        linked = find_todos_linked_to_doc(str(f))
                    except Exception:
                        linked = []
                    events.append({
                        "type": "doc", "date": d, "label": label,
                        "color": color,
                        "title": f.name,
                        "subtitle": f"{label} · {f.stat().st_size // 1024} KB",
                        "path": str(f),
                        "linked": [{"type": "todo", "label": t.get("text", "")[:50]} for t in linked],
                    })
        except Exception:
            pass

    # ── Todos ──────────────────────────────────────────────────────────────
    if "todo" in active_types:
        try:
            from ...assistant_store import get_todos
            for todo in get_todos():
                d = _parse_iso(todo.get("due") or todo.get("created", ""))
                if d is None or not (date_from <= d <= date_to):
                    continue
                text = todo.get("text", "")
                if kw and kw not in text.lower():
                    continue
                prio = todo.get("priority", "normal")
                prio_color = {"hoch": "#ff3366", "normal": "#a78bfa", "niedrig": "var(--ds-text-2)"}.get(prio, "#a78bfa")
                docs = todo.get("linked_docs", [])
                events.append({
                    "type": "todo", "date": d, "label": "Todo",
                    "color": prio_color,
                    "title": text,
                    "subtitle": f"Priorität: {prio} · {'✓ Erledigt' if todo.get('done') else 'Offen'}",
                    "linked": [{"type": "doc", "label": r["label"]} for r in docs],
                })
        except Exception:
            pass

    # ── Rechnungen ─────────────────────────────────────────────────────────
    if "invoice" in active_types:
        try:
            from ...assistant_store import get_invoices
            for inv in get_invoices():
                d = _parse_iso(inv.get("date", ""))
                if d is None or not (date_from <= d <= date_to):
                    continue
                title = f"{inv.get('vendor', '?')} — {float(inv.get('amount', 0)):.2f} €"
                if kw and kw not in title.lower() and kw not in inv.get("category", "").lower():
                    continue
                todos = inv.get("linked_todos", [])
                events.append({
                    "type": "invoice", "date": d, "label": "Rechnung",
                    "color": "#00e87d",
                    "title": title,
                    "subtitle": f"{inv.get('category', '')} · Nr. {inv.get('invoice_number', '–')}",
                    "source_file": inv.get("source_file", ""),
                    "linked": [{"type": "todo", "label": r["label"]} for r in todos],
                })
        except Exception:
            pass

    # ── Ausgaben (recurring) ───────────────────────────────────────────────
    if "expense" in active_types:
        try:
            from ...assistant_store import get_expenses
            for exp in get_expenses():
                d = _parse_iso(exp.get("created", ""))
                if d is None or not (date_from <= d <= date_to):
                    continue
                title = f"{exp.get('name', '?')} — {float(exp.get('amount', 0)):.2f} €"
                if kw and kw not in title.lower() and kw not in exp.get("category", "").lower():
                    continue
                events.append({
                    "type": "expense", "date": d, "label": "Ausgabe",
                    "color": "#ff9f0a",
                    "title": title,
                    "subtitle": f"{exp.get('category', '')} · {exp.get('cycle', 'monatlich')}",
                    "linked": [],
                })
        except Exception:
            pass

    # ── E-Mails ────────────────────────────────────────────────────────────
    if "email" in active_types:
        try:
            from ...config import load_config
            from ...email_connector import load_emails
            cfg = load_config()
            for msg in load_emails(cfg):
                # Parse DD.MM.YYYY HH:MM
                d = None
                try:
                    d = datetime.strptime(msg.date[:10], "%d.%m.%Y").date()
                except Exception:
                    try:
                        d = _parse_iso(msg.date)
                    except Exception:
                        pass
                if d is None or not (date_from <= d <= date_to):
                    continue
                if kw and kw not in msg.subject.lower() and kw not in msg.sender_email.lower():
                    continue
                events.append({
                    "type": "email", "date": d, "label": "E-Mail",
                    "color": "#38bdf8",
                    "title": msg.subject,
                    "subtitle": f"Von: {msg.sender_email}",
                    "linked": [],
                })
        except Exception:
            pass

    # ── Kalender-Termine ───────────────────────────────────────────────────
    if "calendar" in active_types:
        try:
            from ...config import load_config
            from ...calendar_connector import load_calendar_events
            cfg = load_config()
            days = max(1, (date_to - date_from).days + 1)
            for ev in load_calendar_events(cfg, days_ahead=days + 7):
                d = ev.start.date() if hasattr(ev.start, "date") else ev.start
                if not (date_from <= d <= date_to):
                    continue
                if kw and kw not in ev.title.lower() and kw not in ev.location.lower():
                    continue
                time_str = "Ganztägig" if ev.all_day else ev.start.strftime("%H:%M")
                events.append({
                    "type": "calendar", "date": d, "label": "Termin",
                    "color": ev.color or "#c084fc",
                    "title": ev.title,
                    "subtitle": f"{time_str}" + (f" · {ev.location}" if ev.location else ""),
                    "linked": [],
                })
        except Exception:
            pass

    events.sort(key=lambda e: e["date"], reverse=True)
    return events


# ---------------------------------------------------------------------------
# Schnell-Vorschläge
# ---------------------------------------------------------------------------

_QUICK_RANGES = [
    ("Heute",            0,   0),
    ("Diese Woche",      6,   0),
    ("Diesen Monat",     30,  0),
    ("Letzter Monat",    60,  31),
    ("Letztes Quartal",  90,  0),
    ("Dieses Jahr",      365, 0),
    ("Letztes Jahr",     730, 366),
]


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build() -> None:
    page_header(
        "Timeline",
        "Vollständige History aller verarbeiteten Dokumente, Aufgaben, Rechnungen und E-Mails."
    )

    today = date.today()

    # ── Filterleiste ─────────────────────────────────────────────────────
    with ui.card().classes("ds-card-flat w-full mb-4"):
        with ui.column().classes("gap-3 w-full"):

            with ui.row().classes("items-end gap-3 flex-wrap w-full"):
                date_from_inp = ui.input(
                    label="Von",
                    value=(today - timedelta(days=30)).isoformat(),
                ).classes("ds-input").style("min-width:140px")
                date_to_inp = ui.input(
                    label="Bis",
                    value=today.isoformat(),
                ).classes("ds-input").style("min-width:140px")
                kw_inp = ui.input(
                    label="Stichwort suchen (optional)",
                    placeholder="z.B. GASAG, Amazon, Rechnung …",
                ).classes("ds-input flex-1").style("min-width:200px")

            # Schnell-Zeiträume
            with ui.row().classes("gap-2 flex-wrap"):
                ui.label("Schnell:").style("font-size:0.72rem;color:var(--ds-text-2);align-self:center")
                for label, back, offset in _QUICK_RANGES:
                    def make_range(b=back, o=offset):
                        def handler():
                            end = today - timedelta(days=o)
                            start = today - timedelta(days=b)
                            date_from_inp.value = start.isoformat()
                            date_to_inp.value = end.isoformat()
                        return handler
                    ui.button(label, on_click=make_range()).props("flat dense no-caps").style(
                        "font-size:0.7rem;color:#00d4ff;padding:2px 8px"
                    )

            # Typ-Filter
            with ui.row().classes("gap-4 flex-wrap items-center"):
                ui.label("Typen:").style("font-size:0.72rem;color:var(--ds-text-2)")
                type_checks: dict[str, ui.checkbox] = {}
                for t_key, (icon, color, name) in _TYPE_META.items():
                    cb = ui.checkbox(f"{icon} {name}", value=True).style(
                        f"font-size:0.75rem"
                    )
                    type_checks[t_key] = cb

            search_btn = ui.button("Zeitraum anzeigen", icon="search").classes("ds-btn-primary").style(
                "align-self:flex-start"
            ).tooltip("Alle Ereignisse im gewählten Zeitraum laden")

    # ── Ergebnis-Bereich ──────────────────────────────────────────────────
    results_area = ui.column().classes("w-full gap-0")

    async def do_search():
        results_area.clear()

        try:
            d_from = date.fromisoformat(date_from_inp.value.strip())
            d_to   = date.fromisoformat(date_to_inp.value.strip())
        except Exception:
            ui.notify("Ungültiges Datumsformat (YYYY-MM-DD erwartet).", type="warning")
            return

        if d_from > d_to:
            d_from, d_to = d_to, d_from

        active_types = {k for k, cb in type_checks.items() if cb.value}
        kw = kw_inp.value.strip()

        events = await run.io_bound(_collect_events, d_from, d_to, kw, active_types)

        with results_area:
            if not events:
                empty_state(
                    "event_busy",
                    "Keine Einträge im gewählten Zeitraum",
                    f"Für den Zeitraum {d_from} – {d_to}" + (f' mit Stichwort "{kw}"' if kw else '') + " wurden keine Dokumente, Todos oder E-Mails gefunden. Versuche einen anderen Zeitraum oder entferne das Stichwort.",
                )
                return

            # Zusammenfassung
            type_counts: dict[str, int] = {}
            for ev in events:
                type_counts[ev["type"]] = type_counts.get(ev["type"], 0) + 1

            with ui.row().classes("items-center gap-3 flex-wrap mb-3"):
                ui.label(f"{len(events)} Einträge").style(
                    "font-size:0.85rem;font-weight:700;color:var(--ds-text)"
                )
                for t_key, count in type_counts.items():
                    icon_ch, color, name = _TYPE_META[t_key]
                    ui.label(f"{icon_ch} {count} {name}{'s' if count > 1 else ''}").style(
                        f"font-size:0.72rem;padding:2px 8px;border-radius:4px;"
                        f"background:{color}12;color:{color};border:1px solid {color}25"
                    )

            # Gruppierung nach Monat
            current_ym = ""
            for ev in events:
                ym = _ym(ev["date"])
                if ym != current_ym:
                    current_ym = ym
                    yr, mn = int(ym[:4]), int(ym[5:7])
                    header = f"{_MONTH_DE[mn]} {yr}"
                    with ui.row().classes("items-center gap-3 mt-4 mb-2"):
                        ui.element("div").style(
                            "flex:1;height:1px;background:rgba(0,212,255,0.15)"
                        )
                        ui.label(header).style(
                            "font-size:0.75rem;font-weight:700;color:#00d4ff;"
                            "white-space:nowrap;letter-spacing:0.04em"
                        )
                        ui.element("div").style(
                            "flex:1;height:1px;background:rgba(0,212,255,0.15)"
                        )

                _render_event(ev)

    search_btn.on("click", do_search)

    # Initial: letzten Monat laden
    ui.timer(0.1, do_search, once=True)


def _render_event(ev: dict) -> None:
    """Ein Ereignis in der Timeline rendern."""
    t_key = ev["type"]
    color = ev["color"]
    icon_ch, _, type_label = _TYPE_META[t_key]

    with ui.row().classes("items-start gap-3").style(
        "padding:8px 0;border-bottom:1px solid rgba(0,212,255,0.05)"
    ):
        # Datums-Badge
        d: date = ev["date"]
        with ui.column().classes("items-center gap-0").style(
            "min-width:42px;flex-shrink:0;padding-top:2px"
        ):
            ui.label(d.strftime("%d")).style(
                "font-size:1rem;font-weight:800;color:var(--ds-text);line-height:1"
            )
            ui.label(d.strftime("%b")).style(
                "font-size:0.6rem;color:var(--ds-text-3);text-transform:uppercase"
            )

        # Typ-Indikator
        with ui.element("div").style(
            f"width:3px;min-height:40px;border-radius:2px;background:{color};flex-shrink:0"
        ):
            pass

        # Inhalt
        with ui.column().classes("gap-1 flex-1 min-w-0"):
            with ui.row().classes("items-center gap-2 flex-wrap"):
                ui.label(f"{icon_ch} {ev['title'][:80]}").style(
                    "font-size:0.82rem;font-weight:600;color:var(--ds-text);word-break:break-word"
                )
                if ev.get("linked"):
                    for link in ev["linked"][:2]:
                        l_icon = "📄" if link["type"] == "doc" else "✅" if link["type"] == "todo" else "🧾"
                        ui.label(f"🔗 {l_icon} {link['label'][:30]}").style(
                            "font-size:0.62rem;padding:1px 6px;border-radius:4px;"
                            "background:rgba(167,139,250,0.12);color:#a78bfa;"
                            "border:1px solid rgba(167,139,250,0.25);white-space:nowrap"
                        )

            if ev.get("subtitle"):
                ui.label(ev["subtitle"]).style("font-size:0.68rem;color:var(--ds-text-2)")

        # Typ-Label rechts
        ui.label(type_label).style(
            f"font-size:0.6rem;font-weight:700;padding:2px 7px;border-radius:4px;"
            f"background:{color}12;color:{color};border:1px solid {color}25;"
            f"white-space:nowrap;flex-shrink:0;align-self:flex-start;margin-top:3px"
        )
