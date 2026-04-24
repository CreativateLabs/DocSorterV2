"""Nachtarbeiter — Automatisierungen & Zeitplanung."""

from __future__ import annotations

import re
from typing import Any

from nicegui import run, ui

from ...config import load_config
from ...scheduler import load_jobs, run_job, run_due_jobs, save_jobs, ScheduledJob


# ---------------------------------------------------------------------------
# Konstanten / Styles
# ---------------------------------------------------------------------------

_STATUS: dict[str, tuple[str, str]] = {
    "idle":    ("#6B7280", "Bereit"),
    "running": ("#3B82F6", "Laueft"),
    "success": ("#22C55E", "OK"),
    "error":   ("#EF4444", "Fehler"),
}

_SECTION_STYLE = (
    "font-size:0.68rem;font-weight:700;letter-spacing:0.1em;"
    "text-transform:uppercase;color:#00d4ff;opacity:0.7;margin-bottom:6px"
)

_CARD = (
    "background:rgba(10,22,40,0.88);"
    "border:1px solid rgba(0,212,255,0.13);"
    "border-radius:14px;padding:18px 22px;"
    "backdrop-filter:blur(8px);"
    "transition:border-color .2s;"
    "width:100%"
)

_CARD_HOVER = _CARD.replace("rgba(0,212,255,0.13)", "rgba(0,212,255,0.28)")

_INPUT_STYLE = (
    "background:rgba(0,212,255,0.07);"
    "border:1px solid rgba(0,212,255,0.2);"
    "border-radius:8px;color:#E2E8F0;"
    "font-size:0.82rem;padding:0 10px"
)

# Intervall-Auswahl: Label → Stunden
_INTERVALS: list[tuple[str, float]] = [
    ("15 Minuten",  0.25),
    ("30 Minuten",  0.5),
    ("1 Stunde",    1.0),
    ("2 Stunden",   2.0),
    ("4 Stunden",   4.0),
    ("6 Stunden",   6.0),
    ("12 Stunden",  12.0),
    ("Täglich",     24.0),
    ("2 Tage",      48.0),
    ("Wöchentlich", 168.0),
    ("2 Wochen",    336.0),
    ("Monatlich",   720.0),
]
_INTERVAL_OPTS = {v: l for l, v in _INTERVALS}   # {hours: label} für ui.select
_HRS_TO_LABEL  = {v: l for l, v in _INTERVALS}

_CATEGORIES = [
    ("dokumente", "folder_open",      "Dokument-Erkennung"),
    ("email",     "mail_outline",     "E-Mail"),
    ("assistent", "smart_toy",        "Assistent"),
    ("system",    "settings_suggest", "System"),
]


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _fmt_ts(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        from datetime import datetime
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return iso


def _valid_time(s: str) -> bool:
    return bool(re.match(r"^\d{1,2}:\d{2}$", s.strip()))


def _normalize_time(s: str) -> str:
    h, m = s.strip().split(":")
    return f"{int(h):02d}:{int(m):02d}"


def _status_chip(status: str) -> None:
    color, text = _STATUS.get(status, ("#6B7280", status))
    pulse = "animation:pulse 1.5s infinite;" if status == "running" else ""
    ui.label(text).style(
        f"display:inline-block;padding:2px 9px;border-radius:20px;"
        f"font-size:0.68rem;font-weight:700;letter-spacing:.05em;"
        f"text-transform:uppercase;"
        f"background:{color}22;color:{color};border:1px solid {color}55;{pulse}"
    )


# ---------------------------------------------------------------------------
# Watcher-Einstellungen (separate Karte, schreibt in config.yaml)
# ---------------------------------------------------------------------------

def _build_watcher_card(cfg: dict) -> None:
    watcher = cfg.get("watcher", {})

    with ui.card().style(_CARD).classes("w-full"):
        # Header
        with ui.row().classes("items-center justify-between w-full gap-2"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("sensors").style("color:#00d4ff;font-size:1.25rem")
                with ui.column().classes("gap-0"):
                    ui.label("Datei-Watcher").style(
                        "font-size:.95rem;font-weight:600;color:#F1F5F9"
                    )
                    ui.label("Inbox in Echtzeit auf neue Dokumente überwachen").style(
                        "font-size:.75rem;color:#9CA3AF"
                    )

            enabled_val = {"v": watcher.get("enabled", False)}
            enabled_label = ui.label(
                "Aktiv" if enabled_val["v"] else "Inaktiv"
            ).style(
                f"font-size:.75rem;font-weight:600;"
                f"color:{'#22C55E' if enabled_val['v'] else '#6B7280'}"
            )

            def _toggle_watcher(e):
                enabled_val["v"] = e.value
                enabled_label.text = "Aktiv" if e.value else "Inaktiv"
                enabled_label.style(
                    f"font-size:.75rem;font-weight:600;"
                    f"color:{'#22C55E' if e.value else '#6B7280'}"
                )

            ui.switch(value=enabled_val["v"], on_change=_toggle_watcher).props(
                "dense color=cyan"
            )

        ui.separator().style("border-color:rgba(0,212,255,0.08);margin:10px 0")

        # Einstellungs-Felder
        with ui.row().classes("gap-6 flex-wrap items-end"):
            poll_ref = {"v": str(watcher.get("poll_interval", 5.0))}
            with ui.column().classes("gap-1"):
                ui.label("Prüf-Intervall (Sekunden)").style(
                    "font-size:.72rem;color:#9CA3AF;font-weight:600"
                )
                poll_input = ui.input(value=poll_ref["v"]).props(
                    "dense outlined"
                ).style("width:130px;" + _INPUT_STYLE)
                ui.label("Wie oft die Inbox auf neue Dateien geprüft wird").style(
                    "font-size:.68rem;color:#6B7280"
                )

            debounce_ref = {"v": str(watcher.get("debounce_seconds", 2.0))}
            with ui.column().classes("gap-1"):
                ui.label("Wartezeit (Sekunden)").style(
                    "font-size:.72rem;color:#9CA3AF;font-weight:600"
                )
                debounce_input = ui.input(value=debounce_ref["v"]).props(
                    "dense outlined"
                ).style("width:130px;" + _INPUT_STYLE)
                ui.label("Warten bis die Datei vollständig geschrieben ist").style(
                    "font-size:.68rem;color:#6B7280"
                )

            auto_ref = {"v": watcher.get("auto_process", True)}
            with ui.column().classes("gap-1"):
                ui.label("Auto-Verarbeitung").style(
                    "font-size:.72rem;color:#9CA3AF;font-weight:600"
                )
                auto_switch = ui.switch(
                    "Dokumente sofort klassifizieren",
                    value=auto_ref["v"],
                ).props("dense color=cyan").style(
                    "font-size:.78rem;color:#CBD5E1"
                )

        # Speichern-Button
        with ui.row().classes("justify-end mt-3"):
            async def _save_watcher():
                try:
                    from ...config import load_config_raw, save_config
                    poll = float(poll_input.value or 5)
                    deb  = float(debounce_input.value or 2)
                    data = load_config_raw()
                    data.setdefault("watcher", {})
                    data["watcher"]["enabled"]          = enabled_val["v"]
                    data["watcher"]["poll_interval"]    = poll
                    data["watcher"]["debounce_seconds"] = deb
                    data["watcher"]["auto_process"]     = auto_switch.value
                    save_config(data)
                    ui.notify("Watcher-Einstellungen gespeichert", color="green", timeout=2500)
                except Exception as exc:
                    ui.notify(f"Fehler: {exc}", color="red", timeout=4000)

            ui.button("Speichern", icon="save", on_click=_save_watcher).props(
                "unelevated dense no-caps"
            ).style(
                "background:rgba(0,212,255,0.12);color:#00d4ff;"
                "border:1px solid rgba(0,212,255,0.35);border-radius:8px;padding:4px 16px"
            )


# ---------------------------------------------------------------------------
# Einzel-Job-Karte
# ---------------------------------------------------------------------------

def _build_job_card(job: ScheduledJob, cfg: dict, state: dict, redraw_fn) -> None:
    """Eine Job-Konfigurationskarte bauen."""

    with ui.card().style(_CARD).classes("w-full"):

        # ----- Zeile 1: Icon + Label + Status + Toggle -----
        with ui.row().classes("items-center justify-between w-full gap-3"):
            with ui.row().classes("items-center gap-2 flex-1"):
                ui.icon(job.icon).style("color:#00d4ff;font-size:1.25rem")
                with ui.column().classes("gap-0"):
                    ui.label(job.label).style(
                        "font-size:.95rem;font-weight:600;color:#F1F5F9"
                    )
                    ui.label(job.description).style(
                        "font-size:.75rem;color:#9CA3AF"
                    )
            _status_chip(job.status)
            enabled_label = ui.label(
                "Aktiv" if job.enabled else "Pausiert"
            ).style(
                f"font-size:.72rem;font-weight:600;"
                f"color:{'#22C55E' if job.enabled else '#6B7280'}"
            )

            def make_toggle(j=job):
                def _on(e):
                    jobs = load_jobs(cfg)
                    for jj in jobs:
                        if jj.id == j.id:
                            jj.enabled = e.value
                    save_jobs(cfg, jobs)
                    state["jobs"] = jobs
                    enabled_label.text = "Aktiv" if e.value else "Pausiert"
                    enabled_label.style(
                        f"font-size:.72rem;font-weight:600;"
                        f"color:{'#22C55E' if e.value else '#6B7280'}"
                    )
                return _on

            ui.switch(value=job.enabled, on_change=make_toggle()).props("dense color=cyan")

        ui.separator().style("border-color:rgba(0,212,255,0.08);margin:10px 0 12px 0")

        # ----- Zeile 2: Ausführungs-Modus -----
        mode_ref = {"v": job.schedule_type}  # "interval" | "daily"
        times_ref: dict[str, list] = {"v": list(job.run_times)}

        mode_label = ui.label(
            "Ausführung: Intervall" if mode_ref["v"] == "interval" else "Ausführung: Täglich"
        ).style("font-size:.72rem;color:#9CA3AF;font-weight:600;margin-bottom:6px")

        interval_area  = ui.column().classes("gap-2")
        daily_area     = ui.column().classes("gap-3")

        def _refresh_mode():
            mode_label.text = (
                "Ausführung: Intervall" if mode_ref["v"] == "interval"
                else "Ausführung: Täglich"
            )
            interval_area.set_visibility(mode_ref["v"] == "interval")
            daily_area.set_visibility(mode_ref["v"] == "daily")

        # Mode-Toggle-Buttons
        with ui.row().classes("gap-2 mb-3"):
            def _set_interval():
                mode_ref["v"] = "interval"
                _refresh_mode()
            def _set_daily():
                mode_ref["v"] = "daily"
                _refresh_mode()

            ui.button("Intervall", icon="repeat", on_click=_set_interval).props(
                "dense no-caps unelevated"
            ).style(
                "font-size:.78rem;border-radius:8px;padding:3px 12px;"
                "background:rgba(0,212,255,0.1);color:#00d4ff;"
                "border:1px solid rgba(0,212,255,0.3)"
            )
            ui.button("Täglich (Uhrzeiten)", icon="access_time", on_click=_set_daily).props(
                "dense no-caps unelevated"
            ).style(
                "font-size:.78rem;border-radius:8px;padding:3px 12px;"
                "background:rgba(0,212,255,0.1);color:#00d4ff;"
                "border:1px solid rgba(0,212,255,0.3)"
            )

        # ----- Intervall-Bereich -----
        current_hrs_label = _HRS_TO_LABEL.get(job.interval_hours)
        interval_ref = {"v": job.interval_hours}

        with interval_area:
            with ui.row().classes("items-center gap-4 flex-wrap"):
                with ui.column().classes("gap-1"):
                    ui.label("Alle").style("font-size:.72rem;color:#9CA3AF;font-weight:600")
                    interval_select = ui.select(
                        options=_INTERVAL_OPTS,
                        value=job.interval_hours,
                        on_change=lambda e: interval_ref.update({"v": e.value}),
                    ).props("dense outlined options-dense").style(
                        "width:170px;" + _INPUT_STYLE
                    )

        # ----- Tages-Uhrzeit-Bereich -----
        times_chip_row = ui.row().classes("gap-2 flex-wrap items-center")

        def _rebuild_time_chips():
            times_chip_row.clear()
            with times_chip_row:
                for t in times_ref["v"]:
                    _time_chip(t)
                _add_time_row()

        def _time_chip(t: str):
            with ui.row().classes("items-center gap-1").style(
                "background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.25);"
                "border-radius:20px;padding:3px 10px"
            ):
                ui.icon("schedule").style("font-size:.9rem;color:#00d4ff")
                ui.label(t).style("font-size:.82rem;color:#E2E8F0;font-weight:600")
                def make_remove(time=t):
                    def _rm():
                        if time in times_ref["v"]:
                            times_ref["v"].remove(time)
                        _rebuild_time_chips()
                    return _rm
                ui.icon("close").style(
                    "font-size:.85rem;color:#9CA3AF;cursor:pointer"
                ).on("click", make_remove(t))

        def _add_time_row():
            new_time_ref = {"v": ""}
            with ui.row().classes("items-center gap-2"):
                new_input = ui.input(
                    placeholder="HH:MM",
                ).props("dense outlined").style("width:90px;" + _INPUT_STYLE)
                def _add():
                    val = new_input.value.strip()
                    if not val:
                        return
                    if not _valid_time(val):
                        ui.notify("Bitte im Format HH:MM eingeben (z.B. 08:30)", color="orange", timeout=2500)
                        return
                    norm = _normalize_time(val)
                    if norm not in times_ref["v"]:
                        times_ref["v"].append(norm)
                        times_ref["v"].sort()
                    _rebuild_time_chips()
                ui.button(icon="add", on_click=_add).props("dense flat round").style(
                    "color:#00d4ff;width:28px;height:28px"
                )
                ui.label("Uhrzeit hinzufügen").style("font-size:.72rem;color:#6B7280")

        with daily_area:
            ui.label("Ausführung täglich um:").style(
                "font-size:.72rem;color:#9CA3AF;font-weight:600"
            )
            with times_chip_row:
                for t in times_ref["v"]:
                    _time_chip(t)
                _add_time_row()
            ui.label(
                "Der Job wird täglich zu den eingestellten Uhrzeiten gestartet."
            ).style("font-size:.68rem;color:#6B7280;margin-top:4px")

        # Initiale Sichtbarkeit
        interval_area.set_visibility(mode_ref["v"] == "interval")
        daily_area.set_visibility(mode_ref["v"] == "daily")

        ui.separator().style("border-color:rgba(0,212,255,0.08);margin:12px 0 8px 0")

        # ----- Zeile 3: Timestamps + Buttons -----
        with ui.row().classes("items-center justify-between w-full flex-wrap gap-3"):
            with ui.row().classes("gap-4 flex-wrap"):
                if job.last_run:
                    with ui.row().classes("items-center gap-1"):
                        ui.icon("history").style("font-size:.85rem;color:#6B7280")
                        ui.label(f"Zuletzt: {_fmt_ts(job.last_run)}").style(
                            "font-size:.72rem;color:#9CA3AF"
                        )
                if job.next_run and mode_ref["v"] == "interval":
                    with ui.row().classes("items-center gap-1"):
                        ui.icon("schedule").style("font-size:.85rem;color:#6B7280")
                        ui.label(f"Nächste: {_fmt_ts(job.next_run)}").style(
                            "font-size:.72rem;color:#9CA3AF"
                        )
                if job.last_message:
                    ui.label(job.last_message).style(
                        f"font-size:.7rem;font-style:italic;"
                        f"color:{'#EF4444' if job.status == 'error' else '#22C55E'}"
                    )

            with ui.row().classes("gap-2"):
                # Speichern-Button
                def make_save(j=job):
                    async def _save():
                        jobs = load_jobs(cfg)
                        for jj in jobs:
                            if jj.id == j.id:
                                jj.schedule_type   = mode_ref["v"]
                                jj.interval_hours  = float(
                                    interval_select.value
                                    if interval_select.value
                                    else jj.interval_hours
                                )
                                jj.run_times = list(times_ref["v"])
                        save_jobs(cfg, jobs)
                        state["jobs"] = jobs
                        ui.notify(f'"{j.label}" gespeichert', color="green", timeout=2000)
                    return _save
                ui.button("Speichern", icon="save", on_click=make_save()).props(
                    "flat dense no-caps"
                ).style(
                    "color:#00d4ff;border:1px solid rgba(0,212,255,0.3);"
                    "border-radius:6px;padding:2px 12px;font-size:.78rem"
                )

                # Jetzt-starten-Button
                def make_run(j=job):
                    async def _run():
                        ui.notify(f"Starte: {j.label}…", timeout=2000, color="blue")
                        result = await run.io_bound(run_job, j.id, cfg)
                        state["jobs"] = load_jobs(cfg)
                        redraw_fn()
                        if result["status"] == "success":
                            ui.notify(f"{j.label}: {result['message']}", color="green", timeout=4000)
                        else:
                            ui.notify(f"Fehler: {result['message']}", color="red", timeout=5000)
                    return _run
                ui.button("Jetzt starten", icon="play_arrow", on_click=make_run()).props(
                    "unelevated dense no-caps"
                ).style(
                    "background:rgba(0,212,255,0.12);color:#00d4ff;"
                    "border:1px solid rgba(0,212,255,0.35);border-radius:6px;"
                    "padding:2px 12px;font-size:.78rem"
                )


# ---------------------------------------------------------------------------
# Haupt-Build
# ---------------------------------------------------------------------------

def build() -> None:
    """Nachtarbeiter-Seite aufbauen."""

    try:
        cfg = load_config()
    except Exception as exc:
        ui.label(f"Konfiguration konnte nicht geladen werden: {exc}").style("color:#EF4444")
        return

    state: dict = {"jobs": load_jobs(cfg)}

    # ── Header ──────────────────────────────────────────────────────────────
    with ui.row().classes("items-center justify-between w-full mb-1"):
        with ui.column().classes("gap-0"):
            ui.label("Automatisierung").style(
                "font-size:1.6rem;font-weight:700;color:#00d4ff;letter-spacing:-.02em"
            )
            ui.label(
                "Automatische Hintergrundaufgaben — läuft wenn du schläfst"
            ).style("font-size:.82rem;color:#9CA3AF")

        with ui.row().classes("gap-2 items-center"):
            def _refresh_all():
                state["jobs"] = load_jobs(cfg)
                _redraw()

            ui.button("Aktualisieren", icon="refresh", on_click=_refresh_all).props(
                "flat dense no-caps"
            ).style(
                "color:#00d4ff;border:1px solid rgba(0,212,255,0.3);"
                "border-radius:8px;padding:4px 14px"
            ).tooltip("Job-Status neu laden")

            async def _run_all():
                ui.notify("Starte fällige Jobs…", color="blue", timeout=2000)
                results = await run.io_bound(run_due_jobs, cfg)
                state["jobs"] = load_jobs(cfg)
                _redraw()
                done   = sum(1 for r in results if r["status"] == "success")
                errors = sum(1 for r in results if r["status"] == "error")
                if not results:
                    ui.notify("Keine fälligen Jobs", timeout=3000)
                else:
                    ui.notify(
                        f"{done} Job(s) erfolgreich" + (f", {errors} Fehler" if errors else ""),
                        color="green" if not errors else "orange",
                        timeout=4000,
                    )

            ui.button("Fällige Jobs starten", icon="play_circle", on_click=_run_all).props(
                "unelevated dense no-caps"
            ).style(
                "background:rgba(0,212,255,0.12);color:#00d4ff;"
                "border:1px solid rgba(0,212,255,0.35);"
                "border-radius:8px;padding:4px 16px"
            ).tooltip("Alle überfälligen automatischen Jobs jetzt ausführen")

    ui.separator().style("border-color:rgba(0,212,255,0.1);margin:6px 0 20px 0")

    # ── Info-Banner ──────────────────────────────────────────────────────────
    with ui.row().classes("w-full gap-4 mb-4 flex-wrap"):
        for icon, label, value in [
            ("play_circle", "Aktive Jobs",
             str(sum(1 for j in state["jobs"] if j.enabled))),
            ("schedule", "Nächste Ausführung",
             _fmt_ts(min(
                 (j.next_run for j in state["jobs"] if j.next_run and j.enabled and j.schedule_type == "interval"),
                 default=None,
             ))),
            ("check_circle", "Zuletzt erfolgreich",
             str(sum(1 for j in state["jobs"] if j.status == "success"))),
            ("error_outline", "Fehlgeschlagen",
             str(sum(1 for j in state["jobs"] if j.status == "error"))),
        ]:
            with ui.card().style(
                "background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.15);"
                "border-radius:10px;padding:10px 18px;min-width:140px"
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.icon(icon).style("color:#00d4ff;font-size:1.1rem")
                    with ui.column().classes("gap-0"):
                        ui.label(value).style(
                            "font-size:1.1rem;font-weight:700;color:#F1F5F9"
                        )
                        ui.label(label).style("font-size:.7rem;color:#9CA3AF")

    # ── Scrollbarer Inhalt ──────────────────────────────────────────────────
    main_container = ui.column().classes("w-full gap-2")

    def _redraw():
        main_container.clear()
        with main_container:
            _render_all(cfg, state, _redraw)

    with main_container:
        _render_all(cfg, state, _redraw)

    # Auto-Refresh alle 30 Sekunden
    def _auto():
        state["jobs"] = load_jobs(cfg)
        _redraw()

    ui.timer(30.0, _auto)


# ---------------------------------------------------------------------------
# Alle Sektionen rendern
# ---------------------------------------------------------------------------

def _render_all(cfg: dict, state: dict, redraw_fn) -> None:
    jobs_by_cat: dict[str, list[ScheduledJob]] = {}
    for j in state["jobs"]:
        jobs_by_cat.setdefault(j.category, []).append(j)

    for cat_id, cat_icon, cat_label in _CATEGORIES:
        cat_jobs = jobs_by_cat.get(cat_id, [])

        # Sektion-Header
        with ui.row().classes("items-center gap-2 mt-2 mb-2"):
            ui.icon(cat_icon).style("color:#00d4ff;opacity:.7;font-size:1rem")
            ui.label(cat_label).style(_SECTION_STYLE)

        # Watcher-Karte extra in "dokumente"
        if cat_id == "dokumente":
            _build_watcher_card(cfg)

        if not cat_jobs and cat_id != "dokumente":
            ui.label("Keine Jobs in dieser Kategorie.").style(
                "font-size:.78rem;color:#6B7280;padding:4px 0 12px 0"
            )
            continue

        for job in cat_jobs:
            _build_job_card(job, cfg, state, redraw_fn)

        ui.element("div").style("margin-bottom:12px")
