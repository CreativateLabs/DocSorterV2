"""DocSorterV2 — Refokussiertes Dashboard-Layout (Input → Output).

Header-Navigation: Logo | Input | Output | Profil-Icon
Keine Sidebar. Onboarding laeuft Fullscreen (siehe wizard.py).

V1-Pages (chat, finance, bank, messenger, calendar, scheduler, timeline,
terminal, analytics, file_browser, folders, archiv_info, history, overview,
search_chat, unified_chat, assistant, email_manager) sind nicht in der
Navigation — die Files bleiben liegen und koennen bei Bedarf reaktiviert
werden.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from nicegui import app, run, ui

from .pages import config_editor, wizard, landing
from .pages import system as system_page
from .pages import profile as profile_page
from .pages import keywords_hub as keywords_hub_page
from .pages import input_page, output_page, settings, roadmap
from ..version import __version__ as _APP_VERSION
from ..email_webhook import register_routes as _register_email_webhook
from ..messenger_webhook import register_routes as _register_messenger_webhook
from .theme import inject_theme, enable_scroll
from .agent import DocSorterAgent

# ---------------------------------------------------------------------------
# Session-basierter Agent Store — zwei getrennte Agents pro Session
# ---------------------------------------------------------------------------
_agent_store: dict[str, DocSorterAgent] = {}         # Such-Chat + Navigation
_archive_agent_store: dict[str, DocSorterAgent] = {} # Archiv-Chat (isoliert)


def _ensure_session_id() -> str:
    """Session-ID sicherstellen und zurueckgeben."""
    storage = app.storage.user
    session_id = storage.get("session_id")
    if not session_id:
        session_id = str(uuid4())[:12]
        storage["session_id"] = session_id
    return session_id


def _get_session_agent() -> DocSorterAgent:
    """Such-Chat + Navigation Agent (shared fuer alle Seiten ausser Archiv-Chat)."""
    session_id = _ensure_session_id()
    if session_id not in _agent_store:
        username = app.storage.user.get("username", "")
        _agent_store[session_id] = DocSorterAgent(username=username)
    return _agent_store[session_id]


def _get_archive_agent() -> DocSorterAgent:
    """Archiv-Chat Agent — komplett isolierte Message-History."""
    session_id = _ensure_session_id()
    key = f"archive_{session_id}"
    if key not in _archive_agent_store:
        username = app.storage.user.get("username", "")
        _archive_agent_store[key] = DocSorterAgent(username=username)
    return _archive_agent_store[key]


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

# Globale Referenzen fuer Panel-Toggles
_left_panel_ref: ui.column | None = None
_right_panel_ref: ui.column | None = None
_backdrop_ref = None


_panels_open: dict[str, bool] = {"left": False, "right": False}


def _logout() -> None:
    app.storage.user["logged_in"] = False
    app.storage.user.pop("username", None)
    ui.navigate.to("/landing")


def _confirm_logout() -> None:
    """Logout mit kurzem Bestätigungs-Dialog."""
    username = app.storage.user.get("username", "")
    with ui.dialog() as dlg, ui.card().style(
        "background:#0a1628;border:1px solid rgba(255,255,255,0.1);"
        "border-radius:16px;padding:24px;max-width:360px;width:100%"
    ):
        with ui.row().classes("items-center gap-3 mb-3"):
            ui.icon("logout").style("font-size:1.5rem;color:#EF4444")
            ui.label("Abmelden?").style("font-size:1.1rem;font-weight:700;color:var(--ds-text)")
        ui.label(
            f'Möchtest du dich als "{username}" abmelden?'
            if username else "Möchtest du dich abmelden?"
        ).style("font-size:0.85rem;color:var(--ds-text-2);margin-bottom:16px")
        with ui.row().classes("gap-3 justify-end w-full"):
            ui.button("Abbrechen", on_click=dlg.close).props("flat no-caps").style("color:#9CA3AF")
            ui.button("Abmelden", on_click=lambda: (_logout(), dlg.close()), icon="logout").props(
                "unelevated no-caps"
            ).style("background:#EF4444;color:white;border-radius:8px;font-weight:700")
    dlg.open()


def _close_all_panels() -> None:
    """Alle Panels schliessen und Backdrop entfernen."""
    _panels_open["left"] = False
    _panels_open["right"] = False
    if _left_panel_ref:
        _left_panel_ref.classes(remove="ds-panel-visible")
    if _right_panel_ref:
        _right_panel_ref.classes(remove="ds-panel-visible")
    if _backdrop_ref:
        _backdrop_ref.classes(remove="active")


def _header(active: str = "") -> None:
    """Schlanker Header: Logo | Input | Output | Profil-Icon.

    `active` ist eine der Routen ("/input" oder "/output") und steuert
    den aktiven Nav-Link.
    """

    def _nav_btn(label: str, route: str, icon: str) -> None:
        is_active = active == route
        bg = "rgba(0,212,255,0.12)" if is_active else "transparent"
        border = "1px solid rgba(0,212,255,0.35)" if is_active else "1px solid transparent"
        color = "#00d4ff" if is_active else "#e2e8f0"
        weight = "700" if is_active else "500"
        ui.button(label, icon=icon, on_click=lambda r=route: ui.navigate.to(r)).props(
            "flat no-caps dense"
        ).style(
            f"background:{bg};border:{border};color:{color};font-weight:{weight};"
            "border-radius:8px;padding:6px 14px;letter-spacing:0.01em;"
            "text-transform:none"
        )

    with ui.header().classes("ds-header items-center justify-between px-4"):
        # Links: Branding
        with ui.row().classes("items-center gap-3"):
            with ui.element("div").style("cursor:pointer;display:flex;align-items:center;gap:8px") \
                    .on("click", lambda: ui.navigate.to("/input")):
                ui.icon("description").classes("text-xl text-blue-400")
                ui.label("Doc-Sorter").style(
                    "font-size:1.125rem;font-weight:700;color:white;letter-spacing:-0.01em"
                )
                ui.label(f"v{_APP_VERSION}").style(
                    "font-size:0.65rem;font-weight:600;color:rgba(148,163,184,0.8);"
                    "background:rgba(255,255,255,0.08);padding:2px 8px;border-radius:4px;"
                    "letter-spacing:0.02em"
                )

        # Mitte: Kern-Navigation
        with ui.row().classes("items-center gap-2"):
            _nav_btn("Input", "/input", "upload_file")
            _nav_btn("Output", "/output", "folder_special")

        # Rechts: Profil-Icon mit Dropdown
        with ui.row().classes("items-center gap-1"):
            username = app.storage.user.get("username", "User")
            with ui.button(icon="account_circle").props(
                "flat round color=white size=sm"
            ).tooltip(f"Profil: {username}"):
                with ui.menu().style("min-width:200px;padding:4px 0"):
                    with ui.column().style("padding:10px 16px 6px;gap:0"):
                        ui.label(username).style("font-weight:600;font-size:0.85rem")
                        ui.label("Angemeldet").style("font-size:0.7rem;color:#9CA3AF")
                    ui.separator()
                    ui.menu_item("Mein Profil", on_click=lambda: ui.navigate.to("/profile"))
                    ui.menu_item("Einstellungen", on_click=lambda: ui.navigate.to("/settings"))
                    ui.menu_item("Roadmap", on_click=lambda: ui.navigate.to("/roadmap"))
                    ui.separator()
                    ui.menu_item("Abmelden", on_click=_confirm_logout).style("color:#EF4444")


# ---------------------------------------------------------------------------
# Left Panel: Navigation + Quick-Actions + Dateibaum
# ---------------------------------------------------------------------------

# Sidebar UI-Referenzen fuer Live-Updates
_sidebar_stat_labels: dict[str, ui.label] = {}


def _left_panel(agent: DocSorterAgent, current_route: str = "/") -> ui.column:
    """Left Panel: Navigation, Quick-Actions und Dateibaum."""
    global _left_panel_ref
    panel = ui.column().classes("ds-left-panel")
    _left_panel_ref = panel

    def _is_active(route: str) -> bool:
        return current_route == route

    with panel:
        # --- Navigation ---
        ui.label("Navigation").classes("ds-section-label")
        with ui.column().classes("gap-1").style("padding:0 8px"):
            _nav_item("Chat & Suche", "/", "forum", active=_is_active("/") or _is_active("/archive-chat"))
            _nav_item("Kalender", "/calendar", "calendar_month", active=_is_active("/calendar"))
            _nav_item("Mein Assistent", "/assistant", "smart_toy", active=_is_active("/assistant"))
            _nav_item("Timeline", "/timeline", "timeline", active=_is_active("/timeline"))
            _nav_item("Einstellungen", "/config", "tune", active=_is_active("/config"))

        ui.separator().classes("my-2 mx-3")

        # --- Quick-Actions ---
        ui.label("Aktionen").classes("ds-section-label")
        with ui.column().classes("gap-1").style("padding:0 8px"):
            _quick_actions = [
                ("Inbox scannen",      "search",      "rescan",               "Neue Dokumente in der Inbox erkennen und klassifizieren"),
                ("Dateien anzeigen",   "folder_open", "show_files_inbox",     "Alle Dateien in Inbox, Archiv und Prüfung anzeigen"),
                ("Analyse & Charts",   "analytics",   "show_chart_timeline",  "Statistik-Übersicht: Dokumentarten, Zeitachse, Auswertung"),
                ("History",            "history",     "show_history",         "Zuletzt verarbeitete und archivierte Dokumente"),
                ("System-Status",      "memory",      "show_system",          "Systeminfo: Ordner, OCR, KI-Modell, Version"),
                ("Unsichere prüfen",   "rate_review", "show_uncertain",       "Dokumente mit niedriger Erkennungs-Konfidenz manuell prüfen"),
            ]

            for label, icon, action_key, tooltip_text in _quick_actions:
                def make_action_handler(k=action_key):
                    async def handler():
                        await run.io_bound(agent.execute_action, k)
                    return handler

                ui.button(
                    label, on_click=make_action_handler(), icon=icon,
                ).classes("ds-quick-action").props("dense unelevated no-caps flat").tooltip(tooltip_text)

        ui.separator().classes("my-2 mx-3")

        # --- Dateibaum (kompakt, scrollbar wenn viele) ---
        ui.label("Dateien").classes("ds-section-label")
        with ui.column().classes("gap-2").style("padding:0 8px;padding-bottom:16px"):
            stats = agent.get_stats()

            _sidebar_stat_labels["inbox"] = _file_tree_item(
                "inbox", "Inbox", stats["inbox"], "#3B82F6"
            )
            _sidebar_stat_labels["review"] = _file_tree_item(
                "rate_review", "Pruefung", stats["review"], "#F59E0B"
            )
            _sidebar_stat_labels["processed"] = _file_tree_item(
                "archive", "Archiv", stats["processed"], "#22C55E"
            )

    # Periodisches Update der Sidebar-Zahlen (async, kein Event-Loop Blocking)
    async def _refresh_sidebar():
        try:
            new_stats = await run.io_bound(agent.refresh_stats)
            for key, label in _sidebar_stat_labels.items():
                label.set_text(str(new_stats.get(key, 0)))
        except Exception:
            pass

    ui.timer(30.0, _refresh_sidebar)

    return panel


def _nav_item(label: str, route: str, icon: str, active: bool = False) -> None:
    """Ein Navigations-Eintrag mit CSS-Klassen fuer Dark Mode."""
    active_cls = " active" if active else ""

    with ui.link(target=route).classes("ds-nav-link"):
        with ui.row().classes(f"ds-nav-row items-center gap-3{active_cls}"):
            ui.icon(icon).classes("ds-nav-icon-active" if active else "ds-nav-icon")
            ui.label(label).classes("ds-nav-label-active" if active else "ds-nav-label")


def _file_tree_item(icon: str, label: str, count: int, color: str) -> ui.label:
    """Ein Dateibaum-Eintrag im Left Panel. Gibt count-Label zurueck."""
    with ui.row().classes("items-center gap-3").style("padding:4px 8px"):
        ui.icon(icon).style(f"font-size:1rem;color:{color}")
        ui.label(label).classes("ds-file-tree-label")
        count_label = ui.label(str(count)).classes("ds-file-count-badge")
    return count_label


# ---------------------------------------------------------------------------
# Classic Sidebar (fuer Settings)
# ---------------------------------------------------------------------------

def _classic_sidebar(active_route: str) -> ui.left_drawer:
    """Klassische Sidebar fuer Einstellungen-Seite."""
    drawer = ui.left_drawer(value=True, bordered=False).classes("ds-sidebar").props("width=260 behavior=desktop")

    with drawer:
        _classic_nav_group("Dashboard", [
            ("Chat & Suche", "/", "forum", None),
            ("Kalender", "/calendar", "calendar_month", None),
            ("Mein Assistent", "/assistant", "smart_toy", None),
            ("Timeline", "/timeline", "timeline", None),
        ], active_route)
        _classic_nav_group("Einstellungen", [
            ("Einstellungen", "/config", "tune", None),
            ("Schlagwörter", "/keywords", "label", None),
            ("Mein Profil", "/profile", "account_circle", None),
            ("System & Lern-Engine", "/system", "memory", None),
        ], active_route)

    return drawer


def _classic_nav_group(label: str, items: list, active_route: str) -> None:
    """Eine Navigations-Gruppe fuer klassische Seiten."""
    if label:
        ui.label(label).style(
            "font-size:0.65rem;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.06em;color:#9CA3AF;padding:16px 20px 6px 20px"
        )

    for nav_label, route, icon, _ in items:
        is_active = active_route == route
        active_cls = " active" if is_active else ""

        with ui.link(target=route).style("text-decoration:none").classes("ds-nav-link"):
            with ui.row().classes(f"ds-nav-row items-center gap-3{active_cls}"):
                icon_color = "#3B82F6" if is_active else "#9CA3AF"
                ui.icon(icon).style(f"font-size:1.2rem;color:{icon_color}")
                label_color = "#111827" if is_active else "#4B5563"
                label_weight = "600" if is_active else "500"
                ui.label(nav_label).style(
                    f"font-size:0.85rem;font-weight:{label_weight};"
                    f"color:{label_color};flex:1"
                )


# ---------------------------------------------------------------------------
# In-App Update Dialog
# ---------------------------------------------------------------------------

def _show_update_dialog(info) -> None:
    """Prominenter Update-Modal mit Fortschrittsbalken und In-App-Installation."""
    import asyncio
    from ..updater import download_update, prepare_install

    progress: dict = {"bytes": 0, "total": 0, "done": False, "error": None, "path": None}
    _timer: list   = []   # mutable Ref damit poll() den Timer abbrechen kann

    with ui.dialog(value=True).props("persistent") as dlg, ui.card().style(
        "background:#0a1628;"
        "border:2px solid #3B82F6;"
        "border-radius:20px;"
        "padding:28px 32px;"
        "max-width:500px;"
        "width:100%;"
        "box-shadow:0 0 60px rgba(59,130,246,0.3);"
    ):
        # ── Kopfzeile ────────────────────────────────────────────────────────
        with ui.row().classes("items-center gap-4 w-full"):
            with ui.element("div").style(
                "background:rgba(59,130,246,0.18);border-radius:14px;"
                "width:52px;height:52px;display:flex;"
                "align-items:center;justify-content:center;flex-shrink:0"
            ):
                ui.icon("system_update").style("font-size:1.7rem;color:#60A5FA")

            with ui.column().classes("gap-0"):
                ui.label("Update verfügbar").style(
                    "font-size:1.25rem;font-weight:800;color:white;line-height:1.2"
                )
                with ui.row().classes("items-center gap-2 mt-1"):
                    ui.label(f"v{info.current_version}").style(
                        "font-size:0.78rem;color:#6B7280"
                    )
                    ui.icon("arrow_forward").style("font-size:0.9rem;color:#3B82F6")
                    ui.label(f"v{info.latest_version}").style(
                        "font-size:0.78rem;font-weight:700;color:#60A5FA"
                    )

        ui.separator().style("opacity:0.12;margin:16px 0")

        # ── Release-Notes ────────────────────────────────────────────────────
        if info.release_notes:
            with ui.element("div").style(
                "background:rgba(255,255,255,0.04);"
                "border-radius:10px;padding:12px 16px;margin-bottom:16px;"
                "border-left:3px solid #3B82F6"
            ):
                ui.label("Was ist neu?").style(
                    "font-size:0.62rem;font-weight:700;text-transform:uppercase;"
                    "letter-spacing:0.09em;color:#6B7280;margin-bottom:6px;display:block"
                )
                ui.label(info.release_notes).style(
                    "font-size:0.85rem;color:#E5E7EB;line-height:1.55"
                )

        # ── Fortschrittsbereich (erst sichtbar beim Download) ────────────────
        prog_wrap = ui.column().classes("w-full gap-2").style("display:none")
        with prog_wrap:
            with ui.row().classes("items-center justify-between w-full"):
                prog_label = ui.label("Vorbereitung...").style(
                    "font-size:0.78rem;color:#9CA3AF"
                )
                prog_pct = ui.label("").style(
                    "font-size:0.78rem;font-weight:700;color:#60A5FA"
                )
            prog_bar = ui.linear_progress(value=0).props("rounded color=blue").style(
                "height:8px;border-radius:4px;margin-bottom:4px"
            )

        # ── Fehleranzeige ─────────────────────────────────────────────────────
        err_label = ui.label("").style(
            "font-size:0.78rem;color:#F87171;margin-top:4px;display:none"
        )

        # ── Buttons ───────────────────────────────────────────────────────────
        with ui.row().classes("items-center justify-between w-full mt-5"):

            def _dismiss() -> None:
                app.storage.user["upd_dismissed_v"] = info.latest_version
                dlg.close()

            later_btn = ui.button(
                "Später", on_click=_dismiss
            ).props("flat no-caps").style("color:#6B7280;font-size:0.85rem")

            async def _start_update() -> None:
                upd_btn.disable()
                later_btn.disable()
                err_label.style("display:none")
                prog_wrap.style("display:block")
                prog_label.set_text("Verbinde mit Server...")
                prog_pct.set_text("")
                progress.update({"bytes": 0, "total": 0, "done": False, "error": None, "path": None})

                # Download im Hintergrund starten
                asyncio.ensure_future(run.io_bound(download_update, info, progress))

                # Fortschritt per Timer pollen
                async def _poll() -> None:
                    if progress.get("error"):
                        prog_label.set_text("Download fehlgeschlagen")
                        err_label.set_text(f"⚠ {progress['error']}")
                        err_label.style("display:block")
                        upd_btn.set_text("Erneut versuchen")
                        upd_btn.enable()
                        later_btn.enable()
                        progress["error"] = None
                        if _timer:
                            _timer[0].cancel()
                        return

                    total = progress.get("total", 0)
                    done  = progress.get("bytes", 0)
                    if total > 0:
                        pct = done / total
                        prog_bar.set_value(pct)
                        prog_pct.set_text(f"{pct:.0%}")
                        prog_label.set_text(
                            f"{done / 1_000_000:.1f} MB von {total / 1_000_000:.1f} MB"
                        )
                    elif done > 0:
                        prog_label.set_text(f"{done / 1_000_000:.1f} MB geladen...")

                    if progress.get("done") and progress.get("path"):
                        if _timer:
                            _timer[0].cancel()
                        prog_bar.set_value(1.0)
                        prog_pct.set_text("100%")
                        prog_label.set_text("Update wird installiert — App startet neu...")
                        upd_btn.set_text("Startet neu...")
                        await asyncio.sleep(0.8)
                        try:
                            await run.io_bound(prepare_install, progress["path"])
                            app.shutdown()
                        except Exception as exc:
                            err_label.set_text(f"⚠ Installation fehlgeschlagen: {exc}")
                            err_label.style("display:block")
                            prog_label.set_text("Fehler beim Installieren")
                            upd_btn.set_text("Erneut versuchen")
                            upd_btn.enable()
                            later_btn.enable()

                t = ui.timer(0.4, _poll)
                _timer.append(t)

            upd_btn = ui.button(
                "Jetzt aktualisieren", on_click=_start_update, icon="system_update"
            ).props("unelevated no-caps").style(
                "background:linear-gradient(135deg,#3B82F6,#2563EB);"
                "color:white;border-radius:10px;font-weight:700;"
                "font-size:0.9rem;padding:8px 22px;"
                "box-shadow:0 4px 18px rgba(59,130,246,0.45)"
            )


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def build_layout() -> None:
    """Alle Seiten-Routen registrieren."""

    # E-Mail Inbound Webhook registrieren
    from ..config import load_config as _load_cfg
    _register_email_webhook(app, _load_cfg)

    # Messenger Inbound Webhook registrieren (WhatsApp, Telegram, Generic)
    _register_messenger_webhook(app, _load_cfg)

    # Shutdown-Hook: Watcher stoppen wenn Server beendet wird
    def _shutdown_agents():
        for agent in _agent_store.values():
            agent.shutdown()
        for agent in _archive_agent_store.values():
            agent.shutdown()

    app.on_shutdown(_shutdown_agents)

    # Nachtarbeiter: faellige Jobs automatisch im Hintergrund ausfuehren
    async def _scheduler_loop() -> None:
        """Hintergrundschleife: prueft faellige Jobs alle 60 Sekunden.

        60-Sekunden-Takt erlaubt minutengenaue Tageszeit-Planung (schedule_type='daily').
        Die is_job_due()-Logik stellt sicher dass kein Job doppelt laeuft.
        """
        import asyncio
        import logging
        _log = logging.getLogger(__name__)
        # Kurz warten damit der Server komplett hochgefahren ist
        await asyncio.sleep(15)
        while True:
            try:
                from ..scheduler import run_due_jobs
                cfg = _load_cfg()
                results = await run.io_bound(run_due_jobs, cfg)
                if results:
                    _log.info(
                        "Nachtarbeiter: %d Job(s) ausgefuehrt: %s",
                        len(results),
                        ", ".join(r.get("job_id", r.get("job", "?")) for r in results),
                    )
            except Exception as exc:
                _log.warning("Nachtarbeiter Fehler: %s", exc)
            await asyncio.sleep(60)  # Jede Minute pruefen

    app.on_startup(_scheduler_loop)

    # ── Update-Check + prominenter In-App-Dialog ─────────────────────────────
    # Cache damit pro Stunde nur einmal Netz-Request
    _upd_cache: dict = {"info": None, "at": 0.0}

    async def _maybe_show_update() -> None:
        """Wird bei jeder neuen Client-Verbindung aufgerufen."""
        import asyncio, time
        await asyncio.sleep(3)   # kurz warten bis Seite geladen ist
        try:
            now = time.monotonic()
            if now - _upd_cache["at"] > 3600:  # maximal stündlich prüfen
                from ..updater import check_for_update
                _upd_cache["info"] = await run.io_bound(check_for_update)
                _upd_cache["at"]   = now

            info = _upd_cache["info"]
            if not (info and info.has_update):
                return

            # Pro Session nur einmal zeigen (nicht bei jeder Seiten-Navigation)
            dismissed = app.storage.user.get("upd_dismissed_v", "")
            shown     = app.storage.user.get("upd_shown_v", "")
            if dismissed == info.latest_version or shown == info.latest_version:
                return

            app.storage.user["upd_shown_v"] = info.latest_version
            _show_update_dialog(info)
        except Exception:
            pass   # Update-Check darf niemals die App crashen

    app.on_connect(_maybe_show_update)

    # =====================================================================
    # Kern-Routen: Input → Output → Profil
    # =====================================================================

    def _content(active: str):
        """Standard-Shell fuer alle Kern-Seiten: Header + zentrierter Container."""
        inject_theme()
        enable_scroll()
        _header(active=active)
        return ui.column().classes(
            "w-full px-6 py-8 mx-auto ds-animate-in"
        ).style("max-width:1200px;padding-top:80px")

    # ---- "/" → Login-Check + Redirect ----

    @ui.page("/")
    def page_root() -> None:
        if wizard.is_first_run() or not wizard.is_logged_in():
            ui.navigate.to("/landing")
            return
        ui.navigate.to("/input")

    # ---- Input ----

    @ui.page("/input")
    def page_input() -> None:
        if wizard.is_first_run() or not wizard.is_logged_in():
            ui.navigate.to("/landing")
            return
        with _content("/input"):
            input_page.build()

    # ---- Output ----

    @ui.page("/output")
    def page_output() -> None:
        if not wizard.is_logged_in():
            ui.navigate.to("/landing")
            return
        with _content("/output"):
            output_page.build()

    # ---- Einstellungen (neu, ueber Profil-Dropdown) ----

    @ui.page("/settings")
    def page_settings() -> None:
        if not wizard.is_logged_in():
            ui.navigate.to("/landing")
            return
        with _content(""):
            settings.build()

    # ---- Roadmap ----

    @ui.page("/roadmap")
    def page_roadmap() -> None:
        with _content(""):
            roadmap.build()

    # ---- Profil ----

    @ui.page("/profile")
    def page_profile() -> None:
        if not wizard.is_logged_in():
            ui.navigate.to("/landing")
            return
        with _content(""):
            profile_page.build()

    # ---- Landing ----

    @ui.page("/landing")
    def page_landing() -> None:
        if not wizard.is_first_run() and wizard.is_logged_in():
            ui.navigate.to("/input")
            return
        inject_theme()
        landing.build()

    @ui.page("/login")
    def page_login() -> None:
        ui.navigate.to("/landing")

    @ui.page("/logout")
    def page_logout() -> None:
        app.storage.user["logged_in"] = False
        app.storage.user.pop("username", None)
        ui.navigate.to("/landing")

    # ---- Wizard (Ersteinrichtung) — Fullscreen, kein Header/Sidebar ----

    @ui.page("/wizard")
    def page_wizard() -> None:
        inject_theme()
        enable_scroll()
        with ui.column().classes("w-full mx-auto ds-animate-in").style(
            "max-width:1200px;padding:32px 24px"
        ):
            wizard.build()

    # =====================================================================
    # Interne / verlinkte Seiten (nicht in Hauptnavigation)
    # =====================================================================

    # Legacy YAML-Editor (verlinkt aus Settings → "Erweiterte Konfiguration")
    @ui.page("/config")
    def page_config() -> None:
        if not wizard.is_logged_in():
            ui.navigate.to("/landing")
            return
        with _content(""):
            config_editor.build()

    # Schlagwoerter-Hub (verlinkt aus Settings)
    @ui.page("/keywords")
    def page_keywords() -> None:
        if not wizard.is_logged_in():
            ui.navigate.to("/landing")
            return
        with _content(""):
            keywords_hub_page.build()

    # System-Status (verlinkt aus Settings)
    @ui.page("/system")
    def page_system() -> None:
        if not wizard.is_logged_in():
            ui.navigate.to("/landing")
            return
        with _content(""):
            system_page.build()
