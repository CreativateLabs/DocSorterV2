"""Kalender — interaktiver Monatskalender mit Todos, Rechnungen, iCal & eigenen Terminen."""

from __future__ import annotations

import calendar as _cal
import logging
import platform
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from nicegui import ui

from ..theme import page_header

logger = logging.getLogger(__name__)

_MONTHS_DE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]
_DAYS_DE  = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
_DAY_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

_SRC_META: dict[str, tuple[str, str]] = {
    "ical":    ("iCal",     "#00d4ff"),
    "todo":    ("Aufgabe",  "#F59E0B"),
    "invoice": ("Rechnung", "#EF4444"),
    "custom":  ("Eigener",  "#3B82F6"),
}


# ---------------------------------------------------------------------------
# Event-Aggregation
# ---------------------------------------------------------------------------

def _load_all_events() -> dict[str, list[dict]]:
    """Alle Quellen aggregieren → {YYYY-MM-DD: [event_dict, ...]}."""
    result: dict[str, list] = defaultdict(list)

    # iCal ───────────────────────────────────────────────────────────────────
    try:
        from ...calendar_connector import load_calendar_events
        from ...config import load_config
        cfg = load_config()
        for ev in load_calendar_events(cfg, days_ahead=365):
            ds = ev.start.date().isoformat() if hasattr(ev.start, "date") else str(ev.start)
            result[ds].append({
                "title":         ev.title,
                "time":          "" if ev.all_day else ev.start.strftime("%H:%M"),
                "color":         ev.color,
                "icon":          "event",
                "source":        "ical",
                "id":            f"ical_{ds}_{ev.title[:8]}",
                "description":   (ev.description or ev.location or ""),
                "calendar_name": ev.calendar_name,
                "deletable":     False,
            })
    except Exception as exc:
        logger.warning("Kalender-Events (iCal) konnten nicht geladen werden: %s", exc)

    # Todos mit Fälligkeit ───────────────────────────────────────────────────
    try:
        from ...assistant_store import get_todos
        for t in get_todos():
            due = t.get("due", "")
            if not due or t.get("done"):
                continue
            result[due].append({
                "title":       t["text"],
                "time":        "",
                "color":       "#F59E0B",
                "icon":        "task_alt",
                "source":      "todo",
                "id":          t["id"],
                "description": f"Priorität: {t.get('priority', 'normal')}",
                "deletable":   False,
            })
    except Exception as exc:
        logger.warning("Kalender-Events (Todos) konnten nicht geladen werden: %s", exc)

    # Rechnungen ─────────────────────────────────────────────────────────────
    try:
        from ...assistant_store import get_invoices
        for inv in get_invoices():
            ds = inv.get("date", "")
            if not ds:
                continue
            try:
                amount_str = f"{float(inv.get('amount', 0)):.2f} €"
            except (TypeError, ValueError):
                amount_str = str(inv.get("amount", ""))
            result[ds].append({
                "title":       f"{inv.get('vendor', 'Rechnung')} · {amount_str}",
                "time":        "",
                "color":       "#EF4444",
                "icon":        "receipt",
                "source":      "invoice",
                "id":          inv["id"],
                "description": inv.get("notes", ""),
                "deletable":   False,
            })
    except Exception as exc:
        logger.warning("Kalender-Events (Rechnungen) konnten nicht geladen werden: %s", exc)

    # Eigene Einträge ────────────────────────────────────────────────────────
    try:
        from ...calendar_store import get_entries
        for entry in get_entries():
            ds = entry.get("date", "")
            if not ds:
                continue
            result[ds].append({
                "title":       entry["title"],
                "time":        entry.get("time", ""),
                "color":       entry.get("color", "#3B82F6"),
                "icon":        entry.get("icon", "event"),
                "source":      "custom",
                "id":          entry["id"],
                "description": entry.get("description", ""),
                "deletable":   True,
            })
    except Exception as exc:
        logger.warning("Kalender-Events (eigene Einträge) konnten nicht geladen werden: %s", exc)

    return dict(result)


# ---------------------------------------------------------------------------
# Dialog: Neuer Eintrag
# ---------------------------------------------------------------------------

def _open_add_dialog(date_str: str, on_created: Callable) -> None:
    with ui.dialog() as dlg, ui.card().style(
        "background:#0a1628;border:1px solid rgba(59,130,246,0.3);"
        "border-radius:16px;padding:28px;max-width:440px;width:100%"
    ):
        with ui.row().classes("items-center gap-3 mb-4"):
            ui.icon("event_note").style("font-size:1.6rem;color:#3B82F6")
            ui.label("Neuer Eintrag").style("font-size:1.1rem;font-weight:700")

        title_inp = ui.input(
            label="Titel *", placeholder="z.B. Arzttermin, Zahlung, Idee …"
        ).classes("w-full ds-input mb-2")

        with ui.row().classes("w-full gap-2"):
            date_inp = ui.input(label="Datum", value=date_str).classes("flex-1 ds-input")
            date_inp.props("type=date")
            time_inp = ui.input(label="Uhrzeit", placeholder="09:00").classes("w-28 ds-input")

        type_sel = ui.select(
            {"termin": "📅 Termin", "todo": "✅ Aufgabe", "notiz": "📝 Notiz"},
            value="termin",
            label="Typ",
        ).classes("w-full mt-2")

        desc_inp = ui.textarea(label="Beschreibung (optional)").classes(
            "w-full ds-input mt-2"
        ).props("rows=3")

        err = ui.label("").style("font-size:0.78rem;color:#EF4444;margin-top:4px")

        def _save() -> None:
            if not title_inp.value.strip():
                err.set_text("Bitte einen Titel eingeben.")
                return
            if not date_inp.value.strip():
                err.set_text("Bitte ein Datum wählen.")
                return
            try:
                from ...calendar_store import add_entry
                add_entry(
                    title=title_inp.value.strip(),
                    date_str=date_inp.value.strip(),
                    time_str=time_inp.value.strip(),
                    description=desc_inp.value.strip(),
                    entry_type=type_sel.value,
                )
                dlg.close()
                on_created()
                ui.notify("Eintrag gespeichert ✓", type="positive")
            except Exception as exc:
                err.set_text(f"Fehler: {exc}")

        with ui.row().classes("gap-3 mt-5 justify-end"):
            ui.button("Abbrechen", on_click=dlg.close).props("flat no-caps").style(
                "color:#9CA3AF"
            )
            ui.button("Speichern", on_click=_save, icon="save").props(
                "unelevated no-caps"
            ).style(
                "background:#3B82F6;color:white;border-radius:8px;font-weight:600"
            )
    dlg.open()


# ---------------------------------------------------------------------------
# Hilfs-Render
# ---------------------------------------------------------------------------

def _event_pill(ev: dict) -> None:
    color = ev.get("color", "#3B82F6")
    title = ev.get("title", "")
    label = title if len(title) <= 14 else title[:13] + "…"
    with ui.element("div").style(
        f"background:{color}28;border-left:2px solid {color};"
        "border-radius:3px;padding:1px 5px;margin-bottom:1px;"
        "overflow:hidden;white-space:nowrap;text-overflow:ellipsis"
    ):
        ui.label(label).style(
            "font-size:0.6rem;color:var(--ds-text);overflow:hidden;text-overflow:ellipsis"
        )


def _event_detail_row(ev: dict, on_delete: Callable) -> None:
    color  = ev.get("color", "#3B82F6")
    source = ev.get("source", "custom")
    src_label, _ = _SRC_META.get(source, ("", "#9CA3AF"))

    with ui.element("div").style(
        f"border:1px solid {color}28;border-left:3px solid {color};"
        "border-radius:8px;padding:10px 12px;margin-bottom:6px;"
        "background:rgba(255,255,255,0.02)"
    ):
        with ui.row().classes("items-start justify-between gap-2 w-full"):
            with ui.row().classes("items-start gap-2 flex-1 min-w-0"):
                ui.icon(ev.get("icon", "event")).style(
                    f"color:{color};font-size:1rem;flex-shrink:0;margin-top:2px"
                )
                with ui.column().classes("gap-0 flex-1 min-w-0"):
                    ui.label(ev["title"]).style(
                        "font-size:0.88rem;font-weight:600;word-break:break-word;line-height:1.3"
                    )
                    if ev.get("time"):
                        with ui.row().classes("items-center gap-1 mt-1"):
                            ui.icon("schedule").style("font-size:0.7rem;color:var(--ds-text-2)")
                            ui.label(ev["time"]).style("font-size:0.72rem;color:var(--ds-text-2)")
                    if ev.get("description"):
                        ui.label(ev["description"][:100]).style(
                            "font-size:0.72rem;color:var(--ds-text-2);line-height:1.4;margin-top:2px"
                        )
                    if ev.get("calendar_name"):
                        ui.label(ev["calendar_name"]).style(
                            "font-size:0.68rem;color:var(--ds-text-2)"
                        )

            with ui.column().classes("items-end gap-1 flex-shrink-0"):
                ui.label(src_label).style(
                    f"background:{color}22;color:{color};"
                    "border-radius:4px;padding:1px 7px;"
                    "font-size:0.6rem;font-weight:700;white-space:nowrap"
                )
                if ev.get("deletable"):
                    def _make_del(eid: str = ev["id"]) -> Callable:
                        return lambda: on_delete(eid)
                    ui.button(icon="delete_outline", on_click=_make_del()).props(
                        "flat round dense"
                    ).style("color:#EF4444;font-size:0.8rem")


def _render_upcoming(events_by_date: dict, selected: str) -> None:
    try:
        sel_date = date.fromisoformat(selected)
    except ValueError:
        return

    upcoming = []
    for offset in range(1, 60):
        d  = sel_date + timedelta(days=offset)
        ds = d.isoformat()
        if ds in events_by_date:
            upcoming.append((d, events_by_date[ds]))
        if len(upcoming) >= 3:
            break

    if not upcoming:
        return

    with ui.card().classes("ds-card w-full").style("margin-top:12px"):
        ui.label("Demnächst").style(
            "font-size:0.7rem;font-weight:700;color:var(--ds-text-2);"
            "text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px"
        )
        for d, evs in upcoming:
            with ui.row().classes("items-start gap-3 py-1").style(
                "border-top:1px solid rgba(255,255,255,0.05)"
            ):
                with ui.column().classes("gap-0").style("min-width:80px;flex-shrink:0"):
                    ui.label(_DAYS_DE[d.weekday()][:2]).style(
                        "font-size:0.65rem;color:var(--ds-text-2);font-weight:700"
                    )
                    ui.label(f"{d.day}. {_MONTHS_DE[d.month-1][:3]}").style(
                        "font-size:0.72rem;color:var(--ds-text)"
                    )
                with ui.column().classes("gap-1 flex-1 min-w-0"):
                    for ev in evs[:2]:
                        color = ev.get("color", "#3B82F6")
                        title = ev["title"][:24] + ("…" if len(ev["title"]) > 24 else "")
                        with ui.element("div").style(
                            f"background:{color}22;border-left:2px solid {color};"
                            "border-radius:3px;padding:1px 6px;overflow:hidden"
                        ):
                            ui.label(title).style("font-size:0.65rem;color:var(--ds-text)")
                    if len(evs) > 2:
                        ui.label(f"+{len(evs)-2} weitere").style(
                            "font-size:0.62rem;color:var(--ds-text-2)"
                        )


# ---------------------------------------------------------------------------
# Kalender-Sync — Verbindung mit nativen System-Kalendern
# ---------------------------------------------------------------------------

def _detect_macos_calendars() -> list[Path]:
    """macOS: Kalender-Ordner in ~/Library/Calendars/ suchen."""
    base = Path.home() / "Library" / "Calendars"
    if not base.exists():
        return []
    ics_files: list[Path] = []
    # macOS speichert Kalender als .caldav-Ordner mit .ics-Dateien drin
    for subdir in base.rglob("*.ics"):
        ics_files.append(subdir)
    return ics_files[:50]  # Limit für die Anzeige


def _detect_system_ics_paths() -> list[Path]:
    """Plattformübergreifend bekannte Kalender-Pfade finden."""
    found: list[Path] = []
    system = platform.system()

    if system == "Darwin":  # macOS
        candidates = [
            Path.home() / "Library" / "Calendars",
            Path.home() / "Library" / "Application Support" / "Calendar",
            # iCloud Calendar lokal gecacht
            Path.home() / "Library" / "Application Support" / "AddressBook",
        ]
        for c in candidates:
            if c.exists():
                found.append(c)

    elif system == "Windows":
        # Outlook-Export / Windows Calendar
        candidates = [
            Path.home() / "Documents" / "Outlook Files",
            Path.home() / "AppData" / "Local" / "Microsoft" / "Outlook",
            # Windows Calendar (built-in, exportiert manchmal hierhin)
            Path.home() / "AppData" / "Local" / "Packages" /
            "microsoft.windowscommunicationsapps_8wekyb3d8bbwe" / "LocalState" / "Indexed" / "LiveComm",
            # Thunderbird auf Windows
            Path.home() / "AppData" / "Roaming" / "Thunderbird" / "Profiles",
        ]
        for c in candidates:
            if c.exists():
                found.append(c)

    elif system == "Linux":
        # GNOME Calendar / Evolution / KDE Kontact / Thunderbird
        candidates = [
            Path.home() / ".local" / "share" / "gnome-calendar",
            Path.home() / ".local" / "share" / "evolution" / "calendar",
            # KDE Kontact / KOrganizer
            Path.home() / ".local" / "share" / "korganizer",
            Path.home() / ".local" / "share" / "kontact",
            # Thunderbird
            Path.home() / ".thunderbird",
            # GNOME Online Accounts (offline cache)
            Path.home() / ".local" / "share" / "folks",
        ]
        for c in candidates:
            if c.exists():
                found.append(c)

    return found


def _open_calendar_sync_dialog(on_saved: Callable) -> None:
    """Dialog zum Verbinden mit dem System-Kalender."""
    from ...config import load_config_raw, save_config

    cfg_raw = load_config_raw()
    current_paths: list[str] = list(cfg_raw.get("calendar_paths", []))

    with ui.dialog() as dlg, ui.card().style(
        "background:var(--ds-bg-card);border:1px solid rgba(59,130,246,0.3);"
        "border-radius:16px;padding:28px;max-width:580px;width:100%"
    ):
        with ui.row().classes("items-center gap-3 mb-4"):
            ui.icon("sync").style("font-size:1.6rem;color:#00d4ff")
            ui.label("Kalender verbinden").style("font-size:1.1rem;font-weight:700")

        # Info
        with ui.element("div").style(
            "background:rgba(0,212,255,0.08);border-left:3px solid #00d4ff;"
            "border-radius:6px;padding:10px 14px;margin-bottom:16px"
        ):
            ui.label(
                "Doc-Sorter liest .ics-Dateien aus deinem System-Kalender. "
                "Gib einen Ordner oder eine einzelne Datei an — "
                "alle .ics-Dateien darin werden automatisch eingelesen."
            ).style("font-size:0.8rem;color:var(--ds-text-2);line-height:1.5")

        # Auto-Erkennung
        detected = _detect_system_ics_paths()
        if detected:
            ui.label("Gefundene Kalender-Ordner auf diesem Computer:").style(
                "font-size:0.8rem;font-weight:600;margin-bottom:6px"
            )
            for dp in detected:
                dp_str = str(dp)
                already = dp_str in current_paths

                with ui.row().classes("items-center gap-2 mb-1"):
                    ui.icon("folder").style(
                        f"font-size:1rem;color:{'#00e87d' if already else '#00d4ff'}"
                    )
                    ui.label(dp_str).style(
                        "font-size:0.75rem;color:var(--ds-text-2);flex:1;word-break:break-all"
                    )
                    if already:
                        ui.label("✓ verbunden").style("font-size:0.7rem;color:#00e87d;flex-shrink:0")
                    else:
                        def _make_add(p: str = dp_str):
                            def _do_add():
                                if p not in current_paths:
                                    current_paths.append(p)
                                    cfg_raw["calendar_paths"] = current_paths
                                    save_config(cfg_raw)
                                    ui.notify(f"Kalender hinzugefügt ✓", type="positive")
                                    dlg.close()
                                    on_saved()
                            return _do_add
                        ui.button("Verbinden", on_click=_make_add(), icon="link").style(
                            "background:#3B82F6;color:white;border-radius:6px;"
                            "font-size:0.72rem;padding:2px 10px;flex-shrink:0"
                        ).props("dense unelevated no-caps")

        ui.separator().style("margin:16px 0;opacity:0.15")

        # Manueller Pfad
        ui.label("Oder eigenen Pfad eingeben:").style(
            "font-size:0.8rem;font-weight:600;margin-bottom:6px"
        )
        path_inp = ui.input(
            label="Pfad zur .ics-Datei oder zum Kalender-Ordner",
            placeholder="z.B. ~/Desktop/mein-kalender.ics",
        ).classes("w-full ds-input")

        err_lbl = ui.label("").style("font-size:0.75rem;color:#EF4444;margin-top:4px")

        def _add_manual() -> None:
            raw = path_inp.value.strip()
            if not raw:
                err_lbl.set_text("Bitte einen Pfad eingeben.")
                return
            p = Path(raw).expanduser()
            if not p.exists():
                err_lbl.set_text(f"Pfad nicht gefunden: {p}")
                return
            if p.is_file() and p.suffix.lower() != ".ics":
                err_lbl.set_text("Nur .ics-Dateien oder Ordner werden unterstützt.")
                return
            p_str = str(p)
            if p_str in current_paths:
                err_lbl.set_text("Dieser Pfad ist bereits verbunden.")
                return
            current_paths.append(p_str)
            cfg_raw["calendar_paths"] = current_paths
            save_config(cfg_raw)
            ui.notify("Kalender verbunden ✓", type="positive")
            dlg.close()
            on_saved()

        ui.button("Pfad hinzufügen", icon="add_link", on_click=_add_manual).classes(
            "ds-btn-primary mt-2"
        )

        # Aktuelle Verbindungen
        if current_paths:
            ui.separator().style("margin:16px 0;opacity:0.15")
            ui.label("Verbundene Kalender:").style(
                "font-size:0.8rem;font-weight:600;margin-bottom:6px"
            )
            for cp in list(current_paths):
                with ui.row().classes("items-center gap-2 mb-1"):
                    ui.icon("event").style("font-size:0.95rem;color:#00e87d")
                    ui.label(cp).style(
                        "font-size:0.72rem;color:var(--ds-text-2);flex:1;word-break:break-all"
                    )
                    def _make_remove(p: str = cp):
                        def _do_remove():
                            if p in current_paths:
                                current_paths.remove(p)
                            cfg_raw["calendar_paths"] = current_paths
                            save_config(cfg_raw)
                            ui.notify("Verbindung getrennt", type="info")
                            dlg.close()
                            on_saved()
                        return _do_remove
                    ui.button(icon="link_off", on_click=_make_remove()).props(
                        "flat round dense"
                    ).style("color:#EF4444")

        ui.separator().style("margin:16px 0;opacity:0.15")
        ui.button("Schließen", on_click=dlg.close).props("flat no-caps").style(
            "color:#9CA3AF;float:right"
        )

    dlg.open()


# ---------------------------------------------------------------------------
# Haupt-Build — korrekte Reihenfolge: Refreshables → Handler → Aufruf
# ---------------------------------------------------------------------------

def build() -> None:
    """Interaktiver Monatskalender mit Tagesdetail-Panel."""
    today = date.today()
    state = {
        "year":     today.year,
        "month":    today.month,
        "selected": today.isoformat(),
    }
    cache: dict = {"events": {}}

    def _reload() -> None:
        cache["events"] = _load_all_events()

    _reload()

    page_header("Kalender", "Termine · Aufgaben · Rechnungen · eigene Einträge")

    # ── Top-Bar: Refresh + Kalender verbinden + Neuer Termin ───────────────
    # Buttons werden erst nach Handler-Definition geklickt → Lambda reicht
    with ui.row().classes("w-full items-center justify-end gap-2 mb-2"):
        ui.button(
            "Aktualisieren", icon="refresh",
            on_click=lambda: (
                _reload(),
                render_grid.refresh(),    # type: ignore[name-defined]
                render_detail.refresh(),  # type: ignore[name-defined]
            ),
        ).props("unelevated dense no-caps").style(
            "background:rgba(255,255,255,0.06);color:var(--ds-text-2);"
            "border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:4px 12px"
        )
        ui.button(
            "Kalender verbinden", icon="sync",
            on_click=lambda: _open_calendar_sync_dialog(
                lambda: (_reload(), render_grid.refresh(), render_detail.refresh()),  # type: ignore[name-defined]
            ),
        ).props("unelevated dense no-caps").style(
            "background:rgba(0,212,255,0.12);color:#00d4ff;"
            "border:1px solid rgba(0,212,255,0.3);border-radius:8px;padding:4px 12px"
        )
        ui.button(
            "Neuer Termin", icon="add",
            on_click=lambda: _open_add_dialog(
                state["selected"],
                lambda: (_reload(), render_grid.refresh(), render_detail.refresh()),  # type: ignore[name-defined]
            ),
        ).props("unelevated dense no-caps").style(
            "background:#3B82F6;color:white;border-radius:8px;font-weight:600;padding:4px 14px"
        )

    # ── Zweispaltiges Layout ────────────────────────────────────────────────
    with ui.row().classes("w-full gap-4 items-start flex-wrap"):
        left_col  = ui.column().classes("gap-3 flex-1").style("min-width:320px")
        right_col = ui.column().classes("gap-3").style("width:310px;min-width:270px;flex-shrink:0")

    # ── 1. Refreshables definieren (noch NICHT aufrufen) ───────────────────

    @ui.refreshable
    def render_grid() -> None:
        y, m   = state["year"], state["month"]
        sel    = state["selected"]
        evs    = cache["events"]
        today_ = date.today().isoformat()

        # Monats-Navigation
        _month_opts = {i: _MONTHS_DE[i - 1] for i in range(1, 13)}
        _this_year  = date.today().year
        _year_opts  = {yr: str(yr) for yr in range(_this_year - 5, _this_year + 11)}

        with ui.row().classes("items-center justify-between w-full"):
            ui.button(icon="chevron_left", on_click=_prev_month).props(
                "flat round dense"
            ).style("color:var(--ds-text-2)")

            with ui.row().classes("items-center gap-1"):
                # Monat-Dropdown
                ui.select(
                    _month_opts, value=m,
                    on_change=lambda e: _set_month_year(int(e.value), state["year"]),
                ).props("dense borderless").style(
                    "font-size:1.1rem;font-weight:700;min-width:100px;"
                    "color:var(--ds-text)"
                )
                # Jahr-Dropdown
                ui.select(
                    _year_opts, value=y,
                    on_change=lambda e: _set_month_year(state["month"], int(e.value)),
                ).props("dense borderless").style(
                    "font-size:1.1rem;font-weight:700;min-width:64px;"
                    "color:var(--ds-text)"
                )
                ui.button("Heute", on_click=_goto_today).props(
                    "flat dense no-caps"
                ).style(
                    "font-size:0.72rem;color:#3B82F6;padding:2px 8px;"
                    "border:1px solid rgba(59,130,246,0.4);border-radius:6px;margin-left:4px"
                )

            ui.button(icon="chevron_right", on_click=_next_month).props(
                "flat round dense"
            ).style("color:var(--ds-text-2)")

        # Wochentags-Header
        with ui.grid(columns=7).classes("w-full gap-1 mt-1"):
            for dn in _DAY_SHORT:
                ui.label(dn).style(
                    "text-align:center;font-size:0.7rem;font-weight:700;"
                    "color:var(--ds-text-2);padding:4px 2px;letter-spacing:0.04em"
                )

        # Tageszellen
        first_wd, days_in_m = _cal.monthrange(y, m)
        with ui.grid(columns=7).classes("w-full gap-1"):
            for _ in range(first_wd):
                ui.element("div").style("min-height:72px")

            for day in range(1, days_in_m + 1):
                ds       = f"{y}-{m:02d}-{day:02d}"
                day_evs  = evs.get(ds, [])
                is_today = ds == today_
                is_sel   = ds == sel
                is_wkend = _cal.weekday(y, m, day) >= 5

                if is_sel:
                    border = "2px solid #3B82F6"
                    bg     = "rgba(59,130,246,0.14)"
                elif is_today:
                    border = "1px solid rgba(0,212,255,0.5)"
                    bg     = "rgba(0,212,255,0.07)"
                else:
                    border = "1px solid rgba(255,255,255,0.06)"
                    bg     = "rgba(255,255,255,0.01)"

                num_color = (
                    "#3B82F6" if is_sel
                    else "#00d4ff" if is_today
                    else "#6B7280" if is_wkend
                    else "var(--ds-text)"
                )

                def _make_sel(d: str = ds) -> Callable:
                    return lambda: _select(d)

                with ui.element("div").style(
                    f"border:{border};background:{bg};border-radius:8px;"
                    "padding:5px 4px;min-height:72px;cursor:pointer;"
                    "transition:border-color 0.15s,background 0.15s;overflow:hidden"
                ).on("click", _make_sel()):
                    ui.label(str(day)).style(
                        f"font-size:0.78rem;font-weight:{'700' if is_today or is_sel else '500'};"
                        f"color:{num_color};margin-bottom:2px;line-height:1"
                    )
                    for ev in day_evs[:3]:
                        _event_pill(ev)
                    if len(day_evs) > 3:
                        ui.label(f"+{len(day_evs)-3}").style(
                            "font-size:0.58rem;color:var(--ds-text-2);padding-left:2px"
                        )

        # Legende
        with ui.row().classes("items-center gap-4 mt-3 flex-wrap").style(
            "padding:8px 4px;border-top:1px solid rgba(255,255,255,0.06)"
        ):
            for src, (lbl, color) in _SRC_META.items():
                with ui.row().classes("items-center gap-1"):
                    ui.element("div").style(
                        f"width:8px;height:8px;border-radius:2px;background:{color};flex-shrink:0"
                    )
                    ui.label(lbl).style("font-size:0.65rem;color:var(--ds-text-2)")

    @ui.refreshable
    def render_detail() -> None:
        sel    = state["selected"]
        evs    = cache["events"].get(sel, [])
        today_ = date.today().isoformat()

        try:
            sel_date   = date.fromisoformat(sel)
            day_name   = _DAYS_DE[sel_date.weekday()]
            month_name = _MONTHS_DE[sel_date.month - 1]
            is_today_  = sel == today_
        except ValueError:
            sel_date   = date.today()
            day_name   = ""
            month_name = ""
            is_today_  = True

        with ui.card().classes("ds-card w-full"):
            with ui.row().classes("items-start justify-between mb-3 gap-2"):
                with ui.column().classes("gap-0"):
                    ui.label(
                        ("Heute · " if is_today_ else "") + day_name
                    ).style(
                        "font-size:0.72rem;color:var(--ds-text-2);"
                        "font-weight:700;text-transform:uppercase;letter-spacing:0.05em"
                    )
                    ui.label(
                        f"{sel_date.day}. {month_name} {sel_date.year}"
                    ).style("font-size:1.05rem;font-weight:700")
                ui.button(
                    icon="add",
                    on_click=lambda s=sel: _open_add_dialog(s, _on_created),
                ).props("unelevated round dense color=primary").style(
                    "background:#3B82F6;flex-shrink:0"
                ).tooltip("Neuer Eintrag für diesen Tag")

            ui.separator().style("margin:0 0 10px;opacity:0.15")

            if not evs:
                with ui.column().classes("items-center gap-2 py-6"):
                    ui.icon("event_available").style(
                        "font-size:2.2rem;color:rgba(255,255,255,0.15)"
                    )
                    ui.label("Keine Einträge").style(
                        "font-size:0.85rem;color:var(--ds-text-2)"
                    )
                    ui.label("Klicke + um einen Termin hinzuzufügen").style(
                        "font-size:0.72rem;color:var(--ds-text-2);text-align:center"
                    )
            else:
                for ev in sorted(evs, key=lambda e: e.get("time") or ""):
                    _event_detail_row(ev, _on_delete)

        _render_upcoming(cache["events"], sel)

    # ── 2. Handler definieren (Refreshables sind jetzt bekannt) ────────────

    def _prev_month() -> None:
        m, y = state["month"] - 1, state["year"]
        if m < 1:
            m, y = 12, y - 1
        state["month"], state["year"] = m, y
        render_grid.refresh()

    def _next_month() -> None:
        m, y = state["month"] + 1, state["year"]
        if m > 12:
            m, y = 1, y + 1
        state["month"], state["year"] = m, y
        render_grid.refresh()

    def _set_month_year(m: int, y: int) -> None:
        state["month"], state["year"] = m, y
        render_grid.refresh()

    def _goto_today() -> None:
        t = date.today()
        state.update({"year": t.year, "month": t.month, "selected": t.isoformat()})
        render_grid.refresh()
        render_detail.refresh()

    def _select(ds: str) -> None:
        state["selected"] = ds
        try:
            d = date.fromisoformat(ds)
            state["year"]  = d.year
            state["month"] = d.month
        except ValueError:
            pass
        render_grid.refresh()
        render_detail.refresh()

    def _on_created() -> None:
        _reload()
        render_grid.refresh()
        render_detail.refresh()

    def _on_delete(entry_id: str) -> None:
        try:
            from ...calendar_store import delete_entry
            delete_entry(entry_id)
            ui.notify("Eintrag gelöscht", type="positive", timeout=2000)
        except Exception as exc:
            ui.notify(f"Fehler: {exc}", type="negative")
        _reload()
        render_grid.refresh()
        render_detail.refresh()

    # ── 3. Refreshables in die vorbereiteten Container rendern ─────────────
    with left_col:
        render_grid()

    with right_col:
        render_detail()
