"""Unified Chat — kombinierter Archiv-Chat und Such-Chat.

Vereint:
- KI-Agent (Dokumente sortieren, Review, Upload, Action-Buttons) aus Archiv-Chat
- Konversations- und Such-Funktion (Begruessung, Statistiken, Timeline, Dateiinhalt) aus Such-Chat
- Linke Spalte: Chat-Interface
- Rechte Spalte: Eingangs-Feed (alle Kanaele + unsichere Dateien + Datei-History)

Ersetzt /  (Such-Chat) und /archive-chat (Archiv-Chat).
"""

from __future__ import annotations

import random as _random
from datetime import datetime
from pathlib import Path

from nicegui import events, run, ui

from ..agent import Action, ChatMessage, DocSorterAgent, FileRef, MsgRole, MsgType

# Konversations- und Such-Helfer aus Such-Chat
from .search_chat import (
    _chat_response,
    _search_all,
    _render_user_msg,
    _render_agent_msg,
    _render_chart_msg,
    _render_results,
    _scroll_down,
    _help_html,
)

# ---------------------------------------------------------------------------
# CSS-Klassen / Icons (identisch mit chat.py)
# ---------------------------------------------------------------------------

_MSG_CLASSES: dict[MsgType, str] = {
    MsgType.SUGGESTION:   "ds-msg ds-msg-suggestion",
    MsgType.RESULT:       "ds-msg ds-msg-result",
    MsgType.ERROR:        "ds-msg ds-msg-error",
    MsgType.WELCOME:      "ds-msg ds-msg-welcome",
    MsgType.INFO:         "ds-msg ds-msg-agent",
    MsgType.TEXT:         "ds-msg ds-msg-agent",
    MsgType.QUESTION:     "ds-msg ds-msg-question",
    MsgType.FILE_PREVIEW: "ds-msg ds-msg-agent",
    MsgType.INSIGHT:      "ds-msg ds-msg-suggestion",
    MsgType.CHART:        "ds-msg ds-msg-chart",
    MsgType.TABLE:        "ds-msg ds-msg-agent",
    MsgType.FILE_LIST:    "ds-msg ds-msg-file-list",
    MsgType.HISTORY:      "ds-msg ds-msg-history",
    MsgType.SYSTEM_INFO:  "ds-msg ds-msg-system-info",
    MsgType.ONBOARDING:   "ds-msg ds-msg-onboarding",
    MsgType.CONNECTOR:    "ds-msg ds-msg-agent",
}

_MSG_ICONS: dict[MsgType, tuple[str, str]] = {
    MsgType.SUGGESTION:   ("auto_awesome",  "#00d4ff"),
    MsgType.RESULT:       ("check_circle",  "#00e87d"),
    MsgType.ERROR:        ("error",          "#ff3366"),
    MsgType.WELCOME:      ("waving_hand",    "#a78bfa"),
    MsgType.INFO:         ("info",           "var(--ds-text-3)"),
    MsgType.INSIGHT:      ("lightbulb",      "#ff9f0a"),
    MsgType.FILE_PREVIEW: ("description",    "#00d4ff"),
    MsgType.QUESTION:     ("help",           "#00d4ff"),
    MsgType.CHART:        ("bar_chart",      "#00d4ff"),
    MsgType.TABLE:        ("table_chart",    "#a78bfa"),
    MsgType.FILE_LIST:    ("folder_open",    "#ff9f0a"),
    MsgType.HISTORY:      ("history",        "#a78bfa"),
    MsgType.SYSTEM_INFO:  ("memory",         "var(--ds-text-3)"),
    MsgType.ONBOARDING:   ("rocket_launch",  "#00d4ff"),
    MsgType.CONNECTOR:    ("extension",      "#00e87d"),
}

_BTN_CLASSES: dict[str, str] = {
    "primary":   "ds-btn-primary",
    "success":   "ds-btn-success",
    "danger":    "ds-btn-danger",
    "secondary": "ds-btn-secondary",
    "ghost":     "ds-btn-ghost",
}


# ---------------------------------------------------------------------------
# File Card / Tag / Review Widget (aus chat.py uebernommen)
# ---------------------------------------------------------------------------

def _tag(text: str, color: str, bg: str) -> None:
    ui.label(text).style(
        f"font-size:0.65rem;font-weight:600;padding:2px 8px;"
        f"border-radius:4px;background:{bg};color:{color};"
        f"border:1px solid {color}40"
    )


def _render_file_card(fref: FileRef) -> None:
    conf_pct = f"{fref.confidence:.0%}"
    if fref.confidence >= 0.7:
        conf_color, conf_bg = "#00e87d", "rgba(0,232,125,0.12)"
    elif fref.confidence >= 0.4:
        conf_color, conf_bg = "#ff9f0a", "rgba(255,159,10,0.12)"
    else:
        conf_color, conf_bg = "#ff3366", "rgba(255,51,102,0.12)"

    with ui.card().classes("ds-file-card"):
        with ui.row().classes("items-center gap-3 w-full"):
            ui.icon("description").style("font-size:1.3rem;color:var(--ds-text-2)")
            with ui.column().classes("gap-0 flex-1 min-w-0"):
                ui.label(fref.name).style(
                    "font-size:0.8rem;font-weight:600;overflow:hidden;"
                    "text-overflow:ellipsis;white-space:nowrap"
                )
                ui.label(fref.size_str).style("font-size:0.65rem;color:var(--ds-text-2)")
            ui.label(conf_pct).style(
                f"font-size:0.7rem;font-weight:700;padding:2px 10px;"
                f"border-radius:99px;background:{conf_bg};color:{conf_color}"
            )
        with ui.row().classes("gap-2 flex-wrap mt-1"):
            if fref.doc_type != "unbekannt":
                _tag(fref.doc_type, "#00d4ff", "rgba(0,212,255,0.1)")
            if fref.customer != "unbekannt":
                _tag(fref.customer, "#a78bfa", "rgba(124,58,237,0.1)")
            if fref.country != "unbekannt":
                _tag(fref.country, "#00d4ff", "rgba(0,212,255,0.08)")
            if fref.datum:
                _tag(fref.datum, "var(--ds-text-2)", "rgba(148,163,184,0.1)")


def _render_review_widget(fref: FileRef, agent: DocSorterAgent, messages_container) -> None:
    try:
        from ...config import get_document_type_keywords, get_known_customers, get_country_keywords
        cfg = agent._cfg()
        doc_types = list(get_document_type_keywords(cfg).keys()) + ["unbekannt"]
        customers  = [c["name"] for c in get_known_customers(cfg)] + ["unbekannt"]
        countries  = list(get_country_keywords(cfg).keys()) + ["unbekannt"]
    except Exception:
        doc_types = [fref.doc_type]
        customers  = [fref.customer]
        countries  = [fref.country]

    with ui.card().classes("ds-file-card ds-review-card"):
        with ui.row().classes("items-center gap-3 w-full"):
            ui.icon("rate_review").style("font-size:1.3rem;color:#F59E0B")
            with ui.column().classes("gap-0 flex-1 min-w-0"):
                ui.label(fref.name).style(
                    "font-size:0.8rem;font-weight:600;overflow:hidden;"
                    "text-overflow:ellipsis;white-space:nowrap"
                )
                reasons = ", ".join(fref.reasons) if fref.reasons else "niedrige Sicherheit"
                ui.label(reasons).style("font-size:0.65rem;color:#F59E0B")

        art_val   = fref.doc_type if fref.doc_type in doc_types else "unbekannt"
        kunde_val = fref.customer if fref.customer in customers  else "unbekannt"
        land_val  = fref.country  if fref.country  in countries  else "unbekannt"

        with ui.row().classes("gap-2 w-full mt-2"):
            sel_art   = ui.select(doc_types, value=art_val,   label="Dokumentenart").classes("flex-1").props("dense outlined")
            sel_kunde = ui.select(customers,  value=kunde_val, label="Kunde").classes("flex-1").props("dense outlined")
            sel_land  = ui.select(countries,  value=land_val,  label="Land").classes("flex-1").props("dense outlined")

        with ui.row().classes("gap-2 mt-2"):
            def make_review_handler(f=fref, sa=sel_art, sk=sel_kunde, sl=sel_land):
                async def handler():
                    await run.io_bound(
                        agent.review_file,
                        file_path=f.path, doc_type=sa.value,
                        customer=sk.value, country=sl.value,
                    )
                    _refresh_chat(agent, messages_container)
                return handler

            ui.button(
                "Bestätigen & Archivieren", on_click=make_review_handler(), icon="archive",
            ).classes("ds-btn-success").props("dense").tooltip("Angaben bestätigen und Datei ins Archiv verschieben")

            def make_back_handler(f=fref):
                async def handler():
                    await run.io_bound(agent.move_to_inbox, f.path)
                    _refresh_chat(agent, messages_container)
                return handler

            ui.button(
                "Zurück in Inbox", on_click=make_back_handler(), icon="undo",
            ).classes("ds-btn-ghost").props("dense").tooltip("Datei zurück in die Inbox legen")


# ---------------------------------------------------------------------------
# Chart / Table / File-List / History (aus chat.py)
# ---------------------------------------------------------------------------

def _render_chart(msg: ChatMessage) -> None:
    config = msg.metadata.get("highchart_config")
    if config:
        ui.highchart(config).classes("w-full ds-chart-container")


def _render_table(msg: ChatMessage) -> None:
    columns = msg.metadata.get("columns", [])
    rows    = msg.metadata.get("rows", [])
    if columns and rows:
        ui.table(columns=columns, rows=rows).classes("w-full ds-chat-table")


def _render_file_list(msg: ChatMessage) -> None:
    files        = msg.metadata.get("files", [])
    if not files:
        return
    with ui.column().classes("gap-0 w-full mt-2"):
        for f in files[:20]:
            ext = f.get("suffix", "")
            file_icon = "picture_as_pdf" if ext == ".pdf" else "description"
            with ui.row().classes("ds-file-list-item"):
                ui.icon(file_icon).style("font-size:0.9rem;color:var(--ds-text-2)")
                with ui.column().classes("gap-0 flex-1 min-w-0"):
                    ui.label(f.get("name", "")).style(
                        "font-size:0.75rem;font-weight:500;overflow:hidden;"
                        "text-overflow:ellipsis;white-space:nowrap"
                    )
                    rel = f.get("relative", "")
                    if rel and rel != f.get("name", ""):
                        ui.label(rel).style("font-size:0.6rem;color:var(--ds-text-2)")
                ui.label(f.get("size", "")).style(
                    "font-size:0.65rem;color:var(--ds-text-2);white-space:nowrap"
                )
        if len(files) > 20:
            ui.label(f"... und {len(files) - 20} weitere Dateien").style(
                "font-size:0.7rem;color:#9CA3AF;font-style:italic;padding:8px 0"
            )


def _render_history_msg(msg: ChatMessage) -> None:
    entries = msg.metadata.get("entries", [])
    if not entries:
        return
    with ui.column().classes("gap-0 w-full mt-2"):
        for entry in entries:
            ts = entry.get("timestamp", "")
            time_str = ""
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    time_str = dt.strftime("%d.%m. %H:%M")
                except Exception:
                    time_str = ts[:16]
            with ui.row().classes("ds-file-list-item"):
                ui.icon("check_circle").style("font-size:0.8rem;color:#22C55E")
                with ui.column().classes("gap-0 flex-1 min-w-0"):
                    ui.label(entry.get("source", "?")).style(
                        "font-size:0.75rem;font-weight:500;overflow:hidden;"
                        "text-overflow:ellipsis;white-space:nowrap"
                    )
                    ui.label(
                        f"{entry.get('doc_type', '?')} / {entry.get('customer', '?')}"
                    ).style("font-size:0.6rem;color:var(--ds-text-3)")
                if time_str:
                    ui.label(time_str).style(
                        "font-size:0.6rem;color:#9CA3AF;white-space:nowrap"
                    )


# ---------------------------------------------------------------------------
# Message Rendering (Agent-Nachrichten, aus chat.py)
# ---------------------------------------------------------------------------

def _render_agent_message(msg: ChatMessage, agent: DocSorterAgent, messages_container) -> None:
    """Eine Agent-ChatMessage rendern (Review-Widgets, Charts, Tables etc.)."""
    if msg.role == MsgRole.USER:
        with ui.row().classes("w-full justify-end"):
            with ui.column().classes("ds-msg ds-msg-user").style("max-width:88%"):
                ui.html(f'<span style="font-size:0.875rem">{msg.content}</span>', sanitize=False)
                ui.label(msg.timestamp).style(
                    "font-size:0.65rem;opacity:0.7;align-self:flex-end;margin-top:4px"
                )
        return

    css_class = _MSG_CLASSES.get(msg.type, "ds-msg ds-msg-agent")
    icon_name, icon_color = _MSG_ICONS.get(msg.type, ("smart_toy", "#6B7280"))

    with ui.column().classes("w-full").style("max-width:92%"):
        with ui.column().classes(css_class).style("width:100%"):
            with ui.row().classes("items-center gap-2 mb-1"):
                ui.icon(icon_name).style(f"font-size:1rem;color:{icon_color}")
                ui.label(msg.timestamp).style("font-size:0.65rem;color:var(--ds-text-2)")

            ui.html(
                f'<div style="font-size:0.875rem;line-height:1.65">{msg.content}</div>',
                sanitize=False,
            )

            if msg.type == MsgType.CHART:
                _render_chart(msg)
            elif msg.type == MsgType.TABLE:
                _render_table(msg)
            elif msg.type == MsgType.FILE_LIST:
                _render_file_list(msg)
            elif msg.type == MsgType.HISTORY:
                _render_history_msg(msg)
            elif msg.files:
                with ui.column().classes("gap-2 mt-2 w-full"):
                    if msg.type == MsgType.QUESTION:
                        for fref in msg.files:
                            _render_review_widget(fref, agent, messages_container)
                    else:
                        for fref in msg.files:
                            _render_file_card(fref)

            if msg.actions:
                with ui.row().classes("ds-msg-actions"):
                    for action in msg.actions:
                        btn_class = _BTN_CLASSES.get(action.variant, "ds-btn-secondary")

                        def make_handler(a=action):
                            async def handler():
                                if a.callback_key == "navigate_config":
                                    ui.navigate.to("/config")
                                elif a.callback_key == "onboard_open_config":
                                    ui.navigate.to("/config")
                                elif a.callback_key.startswith("undo_"):
                                    undo_id = a.callback_key.replace("undo_", "")
                                    await run.io_bound(agent.undo_last, undo_id)
                                elif a.callback_key == "navigate_review":
                                    await run.io_bound(agent._show_uncertain)
                                elif a.callback_key == "navigate_analytics":
                                    await run.io_bound(agent._show_chart, "timeline")
                                else:
                                    await run.io_bound(agent.execute_action, a.callback_key)
                                _refresh_chat(agent, messages_container)
                            return handler

                        ui.button(
                            action.label, on_click=make_handler(), icon=action.icon,
                        ).classes(btn_class).props("dense")


# ---------------------------------------------------------------------------
# Chips
# ---------------------------------------------------------------------------

def _get_contextual_chips(agent: DocSorterAgent) -> list[tuple[str, str, str]]:
    chips = []
    stats = agent.get_stats()

    if stats["inbox"] > 0:
        chips.append(("Inbox scannen", "search", "rescan"))

    if agent._pending_files:
        sure = [f for f in agent._pending_files if f.confidence >= 0.4 and f.doc_type != "unbekannt"]
        if sure:
            chips.append((f"Sortieren ({len(sure)})", "auto_awesome", "sort_sure"))
        chips.append(("Vorschau", "visibility", "preview"))

    uncertain = [f for f in agent._pending_files if f.confidence < 0.4 or f.doc_type == "unbekannt"]
    if uncertain:
        chips.append((f"Unsichere ({len(uncertain)})", "rate_review", "show_uncertain"))

    chips.append(("Rechnungen", "receipt", "__search_rechnung"))
    chips.append(("Verträge",   "gavel",   "__search_vertrag"))
    chips.append(("Statistiken","analytics","__stats"))
    chips.append(("Timeline",   "timeline", "__timeline"))
    chips.append(("Dateien",    "folder_open", "__files"))
    chips.append(("Hilfe",      "help_outline","__help"))

    return chips[:9]


# ---------------------------------------------------------------------------
# Refresh (Chat-Nachrichten-Bereich)
# ---------------------------------------------------------------------------

def _render_welcome_state(messages_container) -> None:
    """Willkommens-Karte wenn keine Nachrichten vorhanden sind."""
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Guten Morgen"
    elif hour < 18:
        greeting = "Guten Tag"
    else:
        greeting = "Guten Abend"

    with messages_container:
        with ui.element("div").style(
            "max-width:640px;margin:40px auto 0;padding:0 8px;width:100%"
        ):
            # Hauptkarte
            with ui.element("div").style(
                "border-radius:20px;border:1px solid rgba(0,212,255,0.18);"
                "background:rgba(0,212,255,0.04);padding:32px;margin-bottom:20px"
            ):
                with ui.row().classes("items-center gap-3 mb-4"):
                    with ui.element("div").style(
                        "width:48px;height:48px;border-radius:14px;"
                        "background:rgba(0,212,255,0.12);border:1px solid rgba(0,212,255,0.3);"
                        "display:flex;align-items:center;justify-content:center;flex-shrink:0"
                    ):
                        ui.icon("waving_hand").style("font-size:1.6rem;color:#00d4ff")
                    with ui.column().classes("gap-0"):
                        ui.label(f"{greeting}! Ich bin dein Doc-Sorter Assistent.").style(
                            "font-size:1.1rem;font-weight:700;color:var(--ds-text)"
                        )
                        ui.label("Frag mich etwas, lade ein Dokument hoch oder such nach Dateien.").style(
                            "font-size:0.82rem;color:var(--ds-text-2)"
                        )

                ui.label("Was kann ich für dich tun?").style(
                    "font-size:0.72rem;font-weight:700;color:#00d4ff;"
                    "text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px"
                )

                _examples = [
                    ("search",          "#00d4ff",  "Inbox scannen",            "Alle neuen Dokumente in der Inbox erkennen und sortieren"),
                    ("history",         "#a78bfa",  "Zeige meine letzten Dateien", "Übersicht über zuletzt archivierte Dokumente"),
                    ("bar_chart",       "#ff9f0a",  "Statistiken anzeigen",     "Wie viele Dokumente habe ich? Was wurde sortiert?"),
                    ("help_outline",    "#00e87d",  "Was kannst du?",           "Alle Funktionen und Befehle auf einen Blick"),
                ]
                with ui.element("div").style(
                    "display:grid;grid-template-columns:1fr 1fr;gap:10px"
                ):
                    for icon, color, title, desc in _examples:
                        with ui.element("div").style(
                            f"border-radius:12px;border:1px solid {color}20;"
                            f"background:{color}08;padding:12px;cursor:pointer;"
                            f"transition:all 0.2s"
                        ).on("click", lambda t=title: ui.run_javascript(
                            f"document.querySelector('.q-field__native, input[placeholder]').value='{t}';"
                            f"document.querySelector('.q-field__native, input[placeholder]').dispatchEvent(new Event('input'));"
                        )):
                            with ui.row().classes("items-center gap-2 mb-1"):
                                ui.icon(icon).style(f"font-size:1rem;color:{color}")
                                ui.label(title).style(
                                    f"font-size:0.82rem;font-weight:700;color:{color}"
                                )
                            ui.label(desc).style(
                                "font-size:0.72rem;color:var(--ds-text-2);line-height:1.4"
                            )

            # Upload-Hinweis
            with ui.element("div").style(
                "border-radius:12px;border:1px dashed rgba(167,139,250,0.3);"
                "background:rgba(167,139,250,0.04);padding:16px;"
                "display:flex;align-items:center;gap:12px"
            ):
                ui.icon("cloud_upload").style("font-size:1.4rem;color:#a78bfa;flex-shrink:0")
                with ui.column().classes("gap-0"):
                    ui.label("Dokument hochladen").style(
                        "font-size:0.85rem;font-weight:700;color:var(--ds-text)"
                    )
                    ui.label(
                        "Klicke auf 📎 unten links oder ziehe eine Datei ins Fenster — "
                        "PDF, Word, Bild werden automatisch erkannt und sortiert."
                    ).style("font-size:0.75rem;color:var(--ds-text-2);line-height:1.5")


def _refresh_chat(agent: DocSorterAgent, messages_container, chips_container=None) -> None:
    """Chat-Nachrichten und Chips neu rendern.

    chips_container wird als Parameter übergeben (kein globaler State)
    damit mehrere Browser-Sessions unabhängig voneinander funktionieren.
    """
    messages_container.clear()
    with messages_container:
        if not agent.messages:
            _render_welcome_state(messages_container)
        for msg in agent.messages:
            _render_agent_message(msg, agent, messages_container)

    if chips_container is not None:
        chips_container.clear()
        with chips_container:
            _build_chips(agent, messages_container, chips_container)

    _scroll_down()


def _build_chips(agent: DocSorterAgent, messages_container, chips_container=None) -> None:
    chips = _get_contextual_chips(agent)
    for label, icon, key in chips:
        def make_chip_handler(k=key, lbl=label):
            async def handler():
                if k == "__help":
                    agent._show_help()
                elif k == "__files":
                    await run.io_bound(agent._show_files, "inbox")
                elif k == "__stats":
                    from .search_chat import _stats_html
                    html = await run.io_bound(_stats_html, agent, "")
                    _render_user_msg(messages_container, lbl)
                    _render_agent_msg(messages_container, html, icon="analytics", color="#00e87d")
                    _scroll_down()
                    return
                elif k == "__timeline":
                    from .search_chat import _timeline_html
                    html = await run.io_bound(_timeline_html, agent, "timeline", None)
                    _render_user_msg(messages_container, lbl)
                    _render_agent_msg(messages_container, html, icon="timeline", color="#ff9f0a")
                    _scroll_down()
                    return
                elif k.startswith("__search_"):
                    query = k.replace("__search_", "")
                    results = await run.io_bound(_search_all, agent, query)
                    if results:
                        _render_results(messages_container, results, query)
                    else:
                        _render_agent_msg(
                            messages_container,
                            f'Keine Treffer für <b>„{query}"</b>.',
                            icon="search_off",
                            color="var(--ds-text-2)",
                        )
                    _scroll_down()
                    return
                elif k == "__analytics":
                    await run.io_bound(agent._show_analytics_summary)
                elif k == "__history":
                    await run.io_bound(agent._show_history)
                else:
                    await run.io_bound(agent.execute_action, k)
                _refresh_chat(agent, messages_container, chips_container)
            return handler

        ui.button(label, on_click=make_chip_handler(), icon=icon).classes(
            "ds-suggestion-chip"
        ).props("dense unelevated no-caps")


# ---------------------------------------------------------------------------
# Feed-Panel: Unsichere Dateien + Datei-History + Live-Feed
# ---------------------------------------------------------------------------

def _render_uncertain_section(agent: DocSorterAgent, container) -> None:
    """Abschnitt mit unsicheren Dateien im Feed-Panel."""
    try:
        uncertain = [f for f in agent._pending_files if f.confidence < 0.4 or f.doc_type == "unbekannt"]
    except Exception:
        uncertain = []

    if not uncertain:
        return

    with container:
        with ui.element("div").style(
            "padding:8px 12px 4px;border-bottom:1px solid rgba(255,159,10,0.2);"
            "background:rgba(255,159,10,0.04)"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("rate_review").style("font-size:0.85rem;color:#ff9f0a")
                ui.label(f"Prüfung erforderlich ({len(uncertain)})").style(
                    "font-size:0.68rem;font-weight:700;color:#ff9f0a;"
                    "text-transform:uppercase;letter-spacing:0.04em"
                ).tooltip("Diese Dateien konnten nicht eindeutig erkannt werden — bitte manuell prüfen")

        for fref in uncertain[:5]:
            conf_pct = f"{fref.confidence:.0%}"
            with ui.element("div").style(
                "padding:8px 12px;border-bottom:1px solid rgba(255,159,10,0.08);"
                "background:rgba(255,159,10,0.03)"
            ):
                with ui.row().classes("items-center gap-2 w-full"):
                    ui.icon("warning_amber").style("font-size:0.85rem;color:#ff9f0a;flex-shrink:0")
                    with ui.column().classes("gap-0 flex-1 min-w-0"):
                        ui.label(fref.name).style(
                            "font-size:0.72rem;font-weight:600;color:var(--ds-text);"
                            "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                        )
                        ui.label(f"{fref.doc_type} · {conf_pct} Sicherheit").style(
                            "font-size:0.62rem;color:#ff9f0a"
                        )

        if len(uncertain) > 5:
            with ui.element("div").style("padding:4px 12px 8px"):
                ui.label(f"… und {len(uncertain)-5} weitere").style(
                    "font-size:0.65rem;color:var(--ds-text-3);font-style:italic"
                )


def _render_history_section(container) -> None:
    """Abschnitt mit zuletzt archivierten Dateien im Feed-Panel."""
    try:
        from ...config import load_config
        from ...logger import LogManager
        cfg = load_config()
        logs_dir = Path(cfg["paths"]["logs"])
        if not logs_dir.exists():
            return
        log_mgr = LogManager(logs_dir)
        recent = sorted(
            log_mgr.get_all_logs(),
            key=lambda x: x.get("timestamp", ""),
            reverse=True,
        )[:6]
    except Exception:
        return

    if not recent:
        return

    with container:
        with ui.element("div").style(
            "padding:8px 12px 4px;border-bottom:1px solid rgba(0,232,125,0.15);"
            "background:rgba(0,232,125,0.04)"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("history").style("font-size:0.85rem;color:#00e87d")
                ui.label("Zuletzt archiviert").style(
                    "font-size:0.68rem;font-weight:700;color:#00e87d;"
                    "text-transform:uppercase;letter-spacing:0.04em"
                )

        for lg in recent:
            ts = lg.get("timestamp", "")
            try:
                ts_str = datetime.fromisoformat(ts).strftime("%d.%m. %H:%M")
            except Exception:
                ts_str = ts[:16]
            src = Path(lg.get("source", "")).name if lg.get("source") else "?"
            dtype   = lg.get("dokumentenart", "?")
            customer = lg.get("kunde", "?")

            with ui.element("div").style(
                "padding:7px 12px;border-bottom:1px solid rgba(0,232,125,0.06);"
                "background:rgba(0,232,125,0.02)"
            ):
                with ui.row().classes("items-center gap-2 w-full"):
                    ui.icon("check_circle").style("font-size:0.8rem;color:#00e87d;flex-shrink:0")
                    with ui.column().classes("gap-0 flex-1 min-w-0"):
                        ui.label(src).style(
                            "font-size:0.72rem;font-weight:600;color:var(--ds-text);"
                            "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                        )
                        ui.label(f"{dtype} · {customer}").style(
                            "font-size:0.62rem;color:var(--ds-text-2)"
                        )
                    ui.label(ts_str).style(
                        "font-size:0.6rem;color:#9CA3AF;white-space:nowrap;flex-shrink:0"
                    )


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(agent: DocSorterAgent) -> None:
    """Unified Chat aufbauen."""

    with ui.column().classes("ds-chat-container").style("padding:0;margin:0"):

        # ---- Header ----
        with ui.element("div").style(
            "padding:14px 24px 12px;border-bottom:1px solid rgba(0,212,255,0.2);"
            "flex-shrink:0;background:rgba(0,212,255,0.04)"
        ):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").style(
                    "width:36px;height:36px;border-radius:10px;"
                    "background:rgba(0,212,255,0.12);border:1px solid rgba(0,212,255,0.4);"
                    "display:flex;align-items:center;justify-content:center;flex-shrink:0"
                ):
                    ui.icon("forum").style("font-size:1.2rem;color:#00d4ff")
                with ui.column().classes("gap-0 flex-1"):
                    ui.label("Chat & Suche").style(
                        "font-size:1rem;font-weight:700;color:var(--ds-text);line-height:1.2"
                    )
                    ui.label(
                        "Dokumente sortieren, suchen und Fragen stellen — dein intelligenter Assistent"
                    ).style("font-size:0.7rem;color:var(--ds-text-2)")
                feed_badge = ui.label("").style(
                    "font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:99px;"
                    "background:rgba(0,212,255,0.15);color:#00d4ff;"
                    "border:1px solid rgba(0,212,255,0.3);white-space:nowrap;display:none"
                )

        # ---- Hauptbereich: CSS-Grid (Chat | Feed) ----
        _seen_feed_ids: set[str] = set()

        with ui.element("div").style(
            "flex:1 1 0;min-height:0;overflow:hidden;"
            "display:grid;grid-template-columns:1fr 340px;grid-template-rows:1fr;"
            "align-items:stretch;width:100%"
        ):

            # ── Linke Spalte: Chat ───────────────────────────────────────────
            with ui.element("div").style(
                "min-height:0;overflow:hidden;display:flex;flex-direction:column"
            ):

                # Messages Scroll Area
                with ui.element("div").style(
                    "flex:1 1 0;min-height:0;overflow:hidden;width:100%"
                ):
                    _unified_scroll = ui.scroll_area().style(
                        "height:100%;width:100%"
                    ).props('id="ds-unified-scroll"')
                    with _unified_scroll:
                        messages_container = ui.column().classes(
                            "ds-chat-messages gap-4"
                        ).style("width:100%;max-width:860px;margin:0 auto")

                # Suggestion Chips
                chips_container = ui.row().classes("ds-chip-row")
                with chips_container:
                    _build_chips(agent, messages_container, chips_container)

                # Upload Area
                upload_container = ui.column().classes("ds-upload-area")
                upload_visible = {"value": False}

                with upload_container:
                    async def handle_upload(e: events.UploadEventArguments) -> None:
                        try:
                            _inbox_path = Path(agent._cfg()["paths"]["inbox"]).expanduser()
                        except Exception:
                            agent._emit(ChatMessage(
                                id="", role=MsgRole.AGENT, type=MsgType.ERROR,
                                content="Inbox-Pfad nicht konfiguriert.",
                            ))
                            _refresh_chat(agent, messages_container, chips_container)
                            return
                        _inbox_path.mkdir(parents=True, exist_ok=True)
                        try:
                            filename = e.file.name
                            content_bytes = await e.file.read()
                        except AttributeError:
                            filename = e.name  # type: ignore[attr-defined]
                            content_bytes = e.content.read()  # type: ignore[attr-defined]
                        target = _inbox_path / filename
                        if target.exists():
                            stamp = datetime.now().strftime("%H%M%S")
                            target = _inbox_path / f"{target.stem}_{stamp}{target.suffix}"
                        target.write_bytes(content_bytes)
                        await run.io_bound(agent.handle_file_upload, [target])
                        _refresh_chat(agent, messages_container, chips_container)

                    ui.upload(
                        label="Dokumente hierher ziehen oder klicken zum Hochladen (PDF, Word, Bilder)",
                        on_upload=handle_upload,
                        auto_upload=True,
                        multiple=True,
                    ).classes("w-full").props(
                        "accept='.pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.tif,.tiff'"
                    ).style("max-width:860px;margin:0 auto")

                upload_container.set_visibility(False)

                # Input Area
                with ui.element("div").classes("ds-chat-input-area"):
                    with ui.row().classes("items-center gap-3").style(
                        "max-width:860px;margin:0 auto;width:100%"
                    ):
                        def toggle_upload():
                            upload_visible["value"] = not upload_visible["value"]
                            upload_container.set_visibility(upload_visible["value"])

                        ui.button(
                            icon="attach_file", on_click=toggle_upload,
                        ).props("round dense flat").style(
                            "width:40px;height:40px;min-width:40px;color:var(--ds-text-2)"
                        ).tooltip("Dokument hochladen (PDF, Word, Bild)")

                        text_input = ui.input(
                            placeholder="Frage stellen oder Befehl eingeben — z.B. 'Inbox scannen' oder 'Zeige alle Rechnungen'"
                        ).classes("flex-1").props("outlined dense rounded").style(
                            "font-size:0.875rem"
                        )

                        async def send_message():
                            val = text_input.value
                            if not val or not val.strip():
                                return
                            val = val.strip()
                            text_input.value = ""

                            # 1. Konversationellen Intent pruefen (Begruessung, Stats, Timeline etc.)
                            convo = await run.io_bound(_chat_response, agent, val)
                            if convo:
                                _render_user_msg(messages_container, val)
                                if convo.get("chart"):
                                    _render_chart_msg(messages_container, convo.get("chart_type", "timeline"))
                                else:
                                    _render_agent_msg(
                                        messages_container,
                                        convo.get("html", ""),
                                        icon=convo.get("icon", "smart_toy"),
                                        color=convo.get("color", "#00d4ff"),
                                    )
                                _scroll_down()
                                # Lernfunktion: User-Profil aktualisieren
                                try:
                                    from ...user_profile import learn_from_email
                                    learn_from_email(subject=val, sender="user", content=val)
                                except Exception:
                                    pass
                                return

                            # 2. Suche ueber alle Datenquellen
                            search_results = await run.io_bound(_search_all, agent, val)
                            if search_results:
                                _render_user_msg(messages_container, val)
                                _render_results(messages_container, search_results, val)
                                _scroll_down()
                                # Lernfunktion
                                try:
                                    from ...user_profile import learn_from_email
                                    learn_from_email(subject=val, sender="user", content=val)
                                except Exception:
                                    pass
                                return

                            # 3. Voller Agent-Lauf (Dokument-Sortierung, Aktionen, Hilfe …)
                            await run.io_bound(agent.handle_user_message, val)
                            _refresh_chat(agent, messages_container, chips_container)

                        text_input.on("keydown.enter", send_message)

                        ui.button(
                            icon="send", on_click=send_message,
                        ).props("round dense").classes("ds-btn-primary").style(
                            "width:40px;height:40px;min-width:40px"
                        ).tooltip("Nachricht senden (Enter)")

            # ── Rechte Spalte: Feed + History + Unsichere Dateien ───────────
            with ui.element("div").style(
                "min-height:0;overflow:hidden;display:flex;flex-direction:column;"
                "border-left:1px solid rgba(0,212,255,0.12);"
                "background:rgba(10,20,36,0.6)"
            ):
                # Feed-Header
                with ui.element("div").style(
                    "padding:10px 14px;background:rgba(0,212,255,0.05);"
                    "border-bottom:1px solid rgba(0,212,255,0.12);flex-shrink:0"
                ):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("stream").style("font-size:0.95rem;color:#00d4ff")
                        ui.label("Live-Feed").style(
                            "font-size:0.72rem;font-weight:700;color:#00d4ff;flex:1;"
                            "text-transform:uppercase;letter-spacing:0.05em"
                        ).tooltip("Alle aktuellen Aktivitäten — Neue Dokumente, E-Mails, Aufgaben")
                        feed_count_label = ui.label("Neue Ereignisse").style(
                            "font-size:0.65rem;color:var(--ds-text-3)"
                        )

                # Scrollbarer Feed-Inhalt
                with ui.scroll_area().style("flex:1 1 0;min-height:0"):
                    feed_inner = ui.column().classes("gap-0").style("width:100%")

                    # Unsichere Dateien (initial rendern)
                    _render_uncertain_section(agent, feed_inner)

                    # Zuletzt archivierte Dateien
                    _render_history_section(feed_inner)

                    # Live-Feed-Items
                    feed_container = ui.column().classes("gap-0").style("width:100%")

        # ---- Feed-Render-Funktionen ----

        def _render_feed_item(item: dict) -> None:
            from datetime import datetime as _dt
            from ...feed_store import SOURCE_META
            src = SOURCE_META.get(
                item["source"],
                {"icon": "inbox", "color": "#00d4ff", "label": item["source"].capitalize()},
            )
            try:
                ts = _dt.fromisoformat(item["timestamp"]).strftime("%d.%m. %H:%M")
            except Exception:
                ts = ""

            with ui.element("div").style(
                "padding:10px 12px;border-bottom:1px solid rgba(255,255,255,0.04);"
                "background:rgba(10,22,40,0.5)"
            ):
                with ui.column().classes("gap-1 w-full"):
                    with ui.row().classes("items-center gap-2 w-full"):
                        with ui.element("div").style(
                            f"width:22px;height:22px;border-radius:6px;flex-shrink:0;"
                            f"background:{src['color']}15;border:1px solid {src['color']}30;"
                            f"display:flex;align-items:center;justify-content:center"
                        ):
                            ui.icon(src["icon"]).style(f"font-size:0.75rem;color:{src['color']}")
                        ui.label(src["label"]).style(
                            f"font-size:0.58rem;font-weight:700;padding:1px 5px;border-radius:3px;"
                            f"background:{src['color']}10;color:{src['color']};"
                            f"border:1px solid {src['color']}20;white-space:nowrap"
                        )
                        ui.label(ts).style(
                            "font-size:0.6rem;color:var(--ds-text-3);white-space:nowrap;margin-left:auto"
                        )
                    ui.label(item["title"]).style(
                        "font-size:0.76rem;font-weight:600;color:var(--ds-text);"
                        "word-break:break-word;line-height:1.3"
                    )
                    if item.get("content"):
                        preview = item["content"][:90] + ("…" if len(item["content"]) > 90 else "")
                        ui.label(preview).style(
                            "font-size:0.7rem;color:var(--ds-text-2);line-height:1.4"
                        )

                    def _make_forward(it=item):
                        async def _do():
                            from ...feed_store import SOURCE_META as _SM
                            txt = (
                                f"[{_SM.get(it['source'],{}).get('label', it['source'])}]"
                                f" {it['title']}\n\n{it['content']}"
                            )
                            await run.io_bound(agent.handle_user_message, txt)
                            _refresh_chat(agent, messages_container, chips_container)
                        return _do

                    ui.button(
                        "Im Chat bearbeiten →", on_click=_make_forward(), icon="send"
                    ).props("flat no-caps dense").style(
                        f"font-size:0.64rem;color:{src['color']};padding:1px 4px;margin-top:2px"
                    )

        def _poll_feed():
            try:
                from ...feed_store import get_new_items
                new_items = get_new_items(_seen_feed_ids)
                if not new_items:
                    return
                feed_container.clear()
                with feed_container:
                    for item in new_items[:20]:
                        _render_feed_item(item)
                        _seen_feed_ids.add(item["id"])
                feed_count_label.set_text(f"{len(new_items)} Einträge")
                feed_badge.style("display:inline-block")
                feed_badge.set_text(f"{len(new_items)} neu")
            except Exception:
                pass

        ui.timer(4.0, _poll_feed)
        _poll_feed()

    # ---- Agent initialisieren ----
    async def _init_agent():
        await run.io_bound(agent.initialize)
        _refresh_chat(agent, messages_container, chips_container)

    ui.timer(0.3, _init_agent, once=True)

    # ---- Dirty-Flag Polling ----
    def _poll_dirty():
        try:
            if agent._dirty:
                agent._dirty = False
                _refresh_chat(agent, messages_container, chips_container)
        except Exception:
            pass

    ui.timer(0.5, _poll_dirty)
