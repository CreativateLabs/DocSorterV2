"""Assistent-Seite: Morgen, Todos, Ausgaben, Auswertung, Abos."""

from __future__ import annotations

from datetime import date

from nicegui import ui

from ...assistant_store import (
    get_todos, add_todo, toggle_todo, delete_todo,
    get_expenses, add_expense, delete_expense,
    get_subscriptions, add_subscription, review_subscription, delete_subscription,
    get_last_sub_check, mark_sub_check_done,
    link_todo_doc, unlink_todo_doc, link_invoice_todo, unlink_invoice_todo,
    get_linked_docs, get_linked_todos_for_invoice, get_invoices,
)
from ..theme import callout, enable_scroll, page_header, section_title, empty_state, status_badge

# Priority color mapping
_PRIORITY_COLORS = {
    "hoch": "#EF4444",
    "normal": "#3B82F6",
    "niedrig": "#9CA3AF",
}

_PRIORITY_LABELS = {
    "hoch": "Hoch",
    "normal": "Normal",
    "niedrig": "Niedrig",
}


def _card_classes() -> str:
    return "w-full rounded-xl border border-gray-100 p-4 shadow-sm mb-3"


# ---------------------------------------------------------------------------
# TAB 0: Morgen — Hilfsfunktionen
# ---------------------------------------------------------------------------

def _morning_stat(icon: str, label: str, value: str, color: str, sub: str, sub_color: str) -> None:
    with ui.card().classes("ds-stat-card flex-1").style("min-width:160px"):
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.icon(icon).style(f"color:{color};font-size:1.1rem")
            ui.label(label).style(
                "font-size:0.72rem;font-weight:700;color:var(--ds-text-2);"
                "text-transform:uppercase;letter-spacing:0.05em"
            )
        ui.label(value).style("font-size:2.2rem;font-weight:800;color:var(--ds-text);line-height:1")
        ui.label(sub).style(f"font-size:0.72rem;color:{sub_color};margin-top:3px")


def _build_email_todo_extractor(cfg: dict) -> None:
    """Abschnitt: E-Mail-Inhalte analysieren und Todos extrahieren."""
    from ...email_connector import load_emails, extract_action_items
    from ...assistant_store import add_todo, get_todos
    from nicegui import run

    # Schlagwörter für eigene Suche (zusätzlich zu Defaults)
    _DEFAULT_KEYWORDS = ["bitte", "frist", "erledige", "deadline", "action required",
                         "dringend", "zahlen", "antworten", "bestätigen", "unterschreiben"]

    with ui.element("div").style(
        "background:rgba(10,22,40,0.85);border:1px solid rgba(167,139,250,0.2);"
        "border-radius:12px;padding:16px;width:100%"
    ):
        with ui.row().classes("items-center gap-2 mb-1"):
            ui.icon("auto_awesome").style("color:#a78bfa;font-size:1.1rem")
            ui.label("E-Mails → Todos").style(
                "font-size:0.78rem;font-weight:700;color:var(--ds-text-2);"
                "text-transform:uppercase;letter-spacing:0.05em"
            )

        ui.label("Analysiert den Posteingang nach Aktionspunkten und schlägt Todos vor.").style(
            "font-size:0.78rem;color:var(--ds-text-3);margin-bottom:12px"
        )

        # Eigene Schlagwörter konfigurieren
        with ui.row().classes("items-center gap-3 mb-3 flex-wrap"):
            kw_input = ui.input(
                label="Eigene Schlagwörter (kommagetrennt)",
                placeholder="angebot, kündigung, termin",
            ).classes("flex-1 ds-input").style("min-width:220px")
            ui.label("Standard: " + ", ".join(_DEFAULT_KEYWORDS[:6]) + "…").style(
                "font-size:0.68rem;color:var(--ds-text-3)"
            )

        results_col = ui.column().classes("w-full gap-2")
        selected: dict[str, dict] = {}  # id -> item

        async def do_extract():
            results_col.clear()
            selected.clear()

            emails = await run.io_bound(load_emails, cfg)
            if not emails:
                with results_col:
                    ui.label("Keine E-Mails geladen. Zuerst unter E-Mail → Posteingang abrufen.").style(
                        "font-size:0.78rem;color:var(--ds-text-3);font-style:italic"
                    )
                return

            # Eigene Schlagwörter in extract_action_items nicht direkt injizierbar —
            # wir führen eigene Keyword-Suche durch
            items = await run.io_bound(extract_action_items, emails)

            # Eigene Schlagwörter: zusätzliche Treffer
            extra_kws = [k.strip().lower() for k in (kw_input.value or "").split(",") if k.strip()]
            if extra_kws:
                existing_ids = {i["msg_id"] for i in items}
                for msg in emails:
                    if msg.id in existing_ids:
                        continue
                    combined = (msg.subject + " " + msg.snippet + " " + msg.body[:300]).lower()
                    matched = [k for k in extra_kws if k in combined]
                    if matched:
                        items.append({
                            "subject": msg.subject,
                            "sender_email": msg.sender_email,
                            "action": f"E-Mail prüfen (Schlagwort: {matched[0]}): {msg.subject[:50]}",
                            "priority": "medium",
                            "date": msg.date,
                            "msg_id": msg.id,
                        })

            if not items:
                with results_col:
                    ui.label("Keine Aktionspunkte gefunden.").style(
                        "font-size:0.78rem;color:var(--ds-text-3);font-style:italic"
                    )
                return

            _PRIO = {"high": ("#ff3366", "Hoch"), "medium": ("#ff9f0a", "Mittel"), "low": ("#00e87d", "Niedrig")}

            with results_col:
                ui.label(f"{len(items)} Aktionspunkte erkannt — Auswahl treffen:").style(
                    "font-size:0.8rem;font-weight:600;color:var(--ds-text);margin-bottom:4px"
                )
                for item in items:
                    item_id = item["msg_id"]
                    color, prio_label = _PRIO.get(item["priority"], ("#00d4ff", "Normal"))

                    with ui.row().classes("items-start gap-3").style(
                        "padding:8px 10px;border-radius:8px;background:rgba(255,255,255,0.02);"
                        "border:1px solid rgba(255,255,255,0.05)"
                    ):
                        def make_cb(iid=item_id, idata=item):
                            def on_change(e):
                                if e.value:
                                    selected[iid] = idata
                                else:
                                    selected.pop(iid, None)
                            return on_change

                        cb = ui.checkbox(value=True, on_change=make_cb()).style("flex-shrink:0")
                        selected[item_id] = item  # default: alle ausgewählt

                        with ui.column().classes("gap-0 flex-1 min-w-0"):
                            ui.label(item["action"]).style(
                                "font-size:0.8rem;font-weight:600;color:var(--ds-text);"
                                "word-break:break-word"
                            )
                            with ui.row().classes("items-center gap-2 mt-1"):
                                ui.label(item["sender_email"]).style("font-size:0.65rem;color:var(--ds-text-3)")
                                ui.label("·").style("color:var(--ds-text-3)")
                                ui.label(item["date"]).style("font-size:0.65rem;color:var(--ds-text-3)")

                        ui.label(prio_label).style(
                            f"font-size:0.6rem;font-weight:700;padding:2px 7px;border-radius:4px;"
                            f"background:{color}15;color:{color};border:1px solid {color}30;white-space:nowrap;flex-shrink:0"
                        )

        async def do_save_todos():
            if not selected:
                ui.notify("Keine Elemente ausgewählt.", type="warning")
                return
            count = 0
            for item in selected.values():
                await run.io_bound(add_todo, item["action"], item["priority"])
                count += 1
            ui.notify(f"{count} Todo(s) gespeichert!", type="positive")
            results_col.clear()
            selected.clear()

        with ui.row().classes("gap-2"):
            ui.button("Analysieren", on_click=do_extract, icon="search").classes("ds-btn-primary").props("dense")
            ui.button("Auswahl als Todos speichern", on_click=do_save_todos, icon="add_task").classes(
                "ds-btn-secondary"
            ).props("dense")


# ---------------------------------------------------------------------------
# Gehirn-Feed: Live-Ereignisstream im Assistenten
# ---------------------------------------------------------------------------

def _build_brain_feed() -> None:
    """Live-Feed aller Gehirn-Ereignisse (Dokumente, E-Mails, Scheduler, System)."""
    from ...feed_store import SOURCE_META, get_items, mark_seen
    from datetime import datetime as _dt

    items = get_items(limit=15)
    if not items:
        return

    with ui.element("div").style(
        "background:rgba(10,22,40,0.85);border:1px solid rgba(168,85,247,0.2);"
        "border-radius:12px;padding:16px;margin-top:4px"
    ):
        with ui.row().classes("items-center gap-2 mb-3"):
            ui.icon("hub").style("color:#a855f7;font-size:1.1rem")
            ui.label("Gehirn-Feed — alle Eingangskanäle").style(
                "font-size:0.78rem;font-weight:700;color:var(--ds-text-2);"
                "text-transform:uppercase;letter-spacing:0.05em;flex:1"
            )
            unread = sum(1 for i in items if not i.get("seen"))
            if unread:
                ui.label(f"{unread} neu").style(
                    "font-size:0.6rem;font-weight:700;padding:2px 8px;border-radius:99px;"
                    "background:rgba(168,85,247,0.2);color:#a855f7;"
                    "border:1px solid rgba(168,85,247,0.3)"
                )

        seen_ids: list[str] = []
        for item in items:
            src = SOURCE_META.get(item.get("source", "system"),
                                  {"icon": "circle", "color": "#6b7280", "label": item.get("source", "?")})
            try:
                ts = _dt.fromisoformat(item["timestamp"]).strftime("%d.%m. %H:%M")
            except Exception:
                ts = ""

            is_new = not item.get("seen", False)
            row_bg = "rgba(168,85,247,0.04)" if is_new else "transparent"

            with ui.row().classes("items-start gap-3 w-full").style(
                f"padding:8px 6px;border-bottom:1px solid rgba(255,255,255,0.04);"
                f"background:{row_bg};border-radius:6px"
            ):
                with ui.element("div").style(
                    f"width:28px;height:28px;border-radius:7px;flex-shrink:0;margin-top:1px;"
                    f"background:{src['color']}15;border:1px solid {src['color']}25;"
                    "display:flex;align-items:center;justify-content:center"
                ):
                    ui.icon(src["icon"]).style(f"font-size:0.85rem;color:{src['color']}")

                with ui.column().classes("gap-0 flex-1 min-w-0"):
                    with ui.row().classes("items-center gap-2"):
                        ui.label(src["label"]).style(
                            f"font-size:0.6rem;font-weight:700;padding:1px 5px;border-radius:4px;"
                            f"background:{src['color']}10;color:{src['color']};"
                            f"border:1px solid {src['color']}20"
                        )
                        ui.label(item.get("title", "")[:70]).style(
                            "font-size:0.78rem;font-weight:600;color:var(--ds-text);"
                            "overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1"
                        )
                        ui.label(ts).style("font-size:0.63rem;color:var(--ds-text-3);white-space:nowrap")

                    if item.get("content"):
                        snippet = item["content"][:100] + ("…" if len(item["content"]) > 100 else "")
                        ui.label(snippet).style(
                            "font-size:0.72rem;color:var(--ds-text-2);line-height:1.4;margin-top:1px"
                        )

            if is_new:
                seen_ids.append(item["id"])

        # Alle angezeigten als gesehen markieren
        if seen_ids:
            try:
                mark_seen(seen_ids)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# TAB 0: Morgen (Morgenübersicht)
# ---------------------------------------------------------------------------

def _build_morning(cfg: dict) -> None:
    from ...assistant_store import get_todos, get_expenses, get_subscriptions
    from ...email_connector import load_emails, prioritize_emails
    from ...brain import get_briefing
    from datetime import date, datetime, timedelta
    from pathlib import Path
    from nicegui import run

    today = date.today()
    now_hour = datetime.now().hour
    if now_hour < 12:
        _greeting = "Guten Morgen"
    elif now_hour < 18:
        _greeting = "Guten Tag"
    elif now_hour < 22:
        _greeting = "Guten Abend"
    else:
        _greeting = "Gute Nacht"

    briefing = get_briefing()

    # Load all data
    todos_all = get_todos()
    todos_open = [t for t in todos_all if not t.get("done")]
    todos_today = [t for t in todos_open
                   if t.get("priority") == "hoch"
                   or (t.get("due") or "")[:10] == today.isoformat()]

    try:
        from ...calendar_connector import get_today_events
        cal_events = get_today_events(cfg)
    except Exception:
        cal_events = []

    try:
        emails_raw = load_emails(cfg)
        emails_prio = prioritize_emails(emails_raw)
        emails_unread = [e for e in emails_prio if not e["message"].read][:5]
    except Exception:
        emails_unread = []

    inbox_path = Path(cfg.get("paths", {}).get("inbox", "~/Documents/DocSorter/input")).expanduser()
    inbox_count = len(list(inbox_path.glob("*"))) if inbox_path.exists() else 0

    expenses = get_expenses()
    this_month = today.strftime("%Y-%m")
    month_total = sum(
        float(e.get("amount", 0))
        for e in expenses
        if (e.get("date", "") or "")[:7] == this_month or e.get("cycle") == "monatlich"
    )

    subs = get_subscriptions()
    due_subs = [s for s in subs if s.get("active", True) and not s.get("last_review")]

    with ui.column().classes("w-full gap-5"):

        # ── Datum + Briefing-Header ──────────────────────────────────────────
        with ui.row().classes("items-end gap-4 flex-wrap"):
            with ui.column().classes("gap-0"):
                ui.label(today.strftime("%A, %d. %B %Y")).style(
                    "font-size:1.6rem;font-weight:800;letter-spacing:-0.02em;"
                    "background:linear-gradient(135deg,#00d4ff,#a78bfa);"
                    "-webkit-background-clip:text;-webkit-text-fill-color:transparent"
                )
                parts = []
                if todos_today:
                    parts.append(f"⚡ {len(todos_today)} dringende Todos")
                if cal_events:
                    parts.append(f"📅 {len(cal_events)} Termine")
                if emails_unread:
                    parts.append(f"✉️ {len(emails_unread)} neue E-Mails")
                if inbox_count:
                    parts.append(f"📥 {inbox_count} Dokumente warten")
                subtitle = f"{_greeting}! " + (" · ".join(parts) if parts else "Alles erledigt — kein Handlungsbedarf.")
                ui.label(subtitle).style("font-size:0.85rem;color:var(--ds-text-2)")

        # ── Stat-Kacheln ────────────────────────────────────────────────────
        with ui.row().classes("gap-3 flex-wrap w-full"):
            _morning_stat("check_box", "Offene Todos", str(len(todos_open)), "#a78bfa",
                          f"{len(todos_today)} dringend" if todos_today else "Alles erledigt",
                          "#ff3366" if todos_today else "#00e87d")
            _morning_stat("inbox", "Dokument-Inbox", str(inbox_count), "#00d4ff",
                          "Dateien warten" if inbox_count else "Leer",
                          "#ff9f0a" if inbox_count else "#00e87d")
            _morning_stat("euro", "Ausgaben (Monat)", f"{month_total:.0f} €", "#ff9f0a",
                          f"{len(expenses)} Einträge", "var(--ds-text-2)")
            _morning_stat("repeat", "Abos prüfen", str(len(due_subs)), "#00e87d",
                          "fällig" if due_subs else "Alle geprüft",
                          "#ff9f0a" if due_subs else "#00e87d")
            _morning_stat("mail", "Neue E-Mails", str(len(emails_unread)), "#00d4ff",
                          "ungelesen" if emails_unread else "Postfach leer",
                          "#ff9f0a" if emails_unread else "var(--ds-text-2)")
            unread_feed = briefing.get("unread_feed", 0)
            _morning_stat("hub", "Gehirn-Feed", str(unread_feed), "#a855f7",
                          "neue Ereignisse" if unread_feed else "Alles gelesen",
                          "#ff9f0a" if unread_feed else "var(--ds-text-2)")

        # ── Tagesplan: Todos + Termine in einer Timeline ─────────────────────
        with ui.row().classes("gap-4 w-full flex-wrap"):

            # Linke Spalte: Tagesplan
            with ui.column().classes("flex-1 gap-3").style("min-width:280px"):
                with ui.element("div").style(
                    "background:rgba(10,22,40,0.85);border:1px solid rgba(167,139,250,0.2);"
                    "border-radius:12px;padding:16px"
                ):
                    with ui.row().classes("items-center gap-2 mb-3"):
                        ui.icon("today").style("color:#a78bfa;font-size:1.1rem")
                        ui.label("Tagesplan").style(
                            "font-size:0.78rem;font-weight:700;color:var(--ds-text-2);"
                            "text-transform:uppercase;letter-spacing:0.05em"
                        )

                    # Termine (sortiert nach Uhrzeit)
                    if cal_events:
                        for ev in sorted(cal_events, key=lambda e: e.start):
                            time_str = "Ganztägig" if ev.all_day else ev.start.strftime("%H:%M")
                            with ui.row().classes("items-start gap-3").style(
                                f"padding:7px 10px;border-left:3px solid {ev.color};"
                                "border-radius:0 8px 8px 0;background:rgba(255,255,255,0.02);margin-bottom:4px"
                            ):
                                ui.label(time_str).style(
                                    "font-size:0.72rem;font-weight:700;color:#00d4ff;"
                                    "font-family:monospace;min-width:52px;flex-shrink:0;padding-top:1px"
                                )
                                with ui.column().classes("gap-0 flex-1"):
                                    ui.label(ev.title).style("font-size:0.8rem;font-weight:600;color:var(--ds-text)")
                                    if ev.location:
                                        ui.label(ev.location).style("font-size:0.68rem;color:var(--ds-text-3)")
                    else:
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("event_available").style("font-size:0.9rem;color:var(--ds-text-3)")
                            ui.label("Keine Termine heute").style("font-size:0.78rem;color:var(--ds-text-3)")

                    if cal_events and todos_today:
                        ui.separator().style("margin:8px 0;opacity:0.3")

                    # Dringende Todos
                    if todos_today:
                        for t in sorted(todos_today, key=lambda x: {"hoch": 0, "normal": 1, "niedrig": 2}.get(x.get("priority", "normal"), 1)):
                            prio_color = {"hoch": "#ff3366", "normal": "#00d4ff", "niedrig": "var(--ds-text-3)"}.get(t.get("priority", "normal"), "#00d4ff")
                            with ui.row().classes("items-center gap-3").style(
                                "padding:6px 8px;border-radius:6px;"
                                "background:rgba(255,255,255,0.02);margin-bottom:3px"
                            ):
                                ui.element("div").style(
                                    f"width:8px;height:8px;border-radius:50%;background:{prio_color};flex-shrink:0"
                                )
                                ui.label(t.get("text", "")[:55]).style(
                                    "font-size:0.8rem;color:var(--ds-text);flex:1"
                                )
                                if t.get("due"):
                                    ui.label(t["due"]).style("font-size:0.65rem;color:var(--ds-text-3);white-space:nowrap")
                    elif not cal_events:
                        ui.label("Heute keine dringenden Aufgaben.").style(
                            "font-size:0.78rem;color:var(--ds-text-3);font-style:italic"
                        )

            # Rechte Spalte: E-Mails
            with ui.column().classes("flex-1 gap-3").style("min-width:280px"):
                with ui.element("div").style(
                    "background:rgba(10,22,40,0.85);border:1px solid rgba(0,212,255,0.2);"
                    "border-radius:12px;padding:16px"
                ):
                    with ui.row().classes("items-center gap-2 mb-3"):
                        ui.icon("mail").style("color:#00d4ff;font-size:1.1rem")
                        ui.label("Posteingang").style(
                            "font-size:0.78rem;font-weight:700;color:var(--ds-text-2);"
                            "text-transform:uppercase;letter-spacing:0.05em"
                        )
                        if emails_unread:
                            ui.label(str(len(emails_unread))).style(
                                "font-size:0.6rem;font-weight:700;padding:1px 6px;border-radius:10px;"
                                "background:rgba(0,212,255,0.15);color:#00d4ff;margin-left:auto"
                            )

                    if not emails_unread:
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("mark_email_read").style("font-size:0.9rem;color:var(--ds-text-3)")
                            ui.label("Keine neuen E-Mails").style("font-size:0.78rem;color:var(--ds-text-3)")
                    else:
                        _PRIO_COLOR = {"high": "#ff3366", "medium": "#ff9f0a", "low": "var(--ds-text-2)"}
                        for item in emails_unread:
                            msg = item["message"]
                            pc = _PRIO_COLOR.get(item["priority"], "var(--ds-text-2)")
                            with ui.row().classes("items-start gap-3").style(
                                "padding:6px 0;border-bottom:1px solid rgba(0,212,255,0.06)"
                            ):
                                ui.element("div").style(
                                    f"width:6px;height:6px;border-radius:50%;background:{pc};"
                                    "flex-shrink:0;margin-top:5px"
                                )
                                with ui.column().classes("gap-0 flex-1 min-w-0"):
                                    ui.label(msg.subject[:50]).style(
                                        "font-size:0.78rem;font-weight:600;color:var(--ds-text);"
                                        "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                                    )
                                    ui.label(msg.sender_email).style(
                                        "font-size:0.65rem;color:var(--ds-text-3)"
                                    )

        # ── Gehirn-Feed: Letzte Ereignisse aus allen Quellen ────────────────
        _build_brain_feed()

        # ── E-Mail → Todos Extractor ─────────────────────────────────────────
        _build_email_todo_extractor(cfg)


# ---------------------------------------------------------------------------
# Verknüpfungs-Dialog
# ---------------------------------------------------------------------------

def _show_link_dialog(todo_id: str, todo_text: str, refresh_cb) -> None:
    """Dialog: Dokument oder Rechnung an ein Todo verknüpfen."""
    from ...config import load_config
    from pathlib import Path

    cfg = load_config()
    archive = Path(cfg.get("paths", {}).get("archive", "")).expanduser()
    inbox   = Path(cfg.get("paths", {}).get("inbox", "")).expanduser()

    # Alle verfügbaren Dateien sammeln
    all_files: list[tuple[str, str]] = []  # (path_str, label)
    for folder in [archive, inbox]:
        if folder.exists():
            for f in sorted(folder.rglob("*"))[:200]:
                if f.is_file() and not f.name.startswith("_"):
                    rel = str(f.relative_to(folder.parent)) if folder.parent != Path("/") else f.name
                    all_files.append((str(f), f.name))

    with ui.dialog() as dlg, ui.card().style(
        "min-width:480px;max-width:620px;background:rgba(10,22,40,0.97);"
        "border:1px solid rgba(167,139,250,0.25)"
    ):
        with ui.column().classes("gap-3 w-full").style("padding:20px"):
            ui.label("Dokument verknüpfen").style(
                "font-size:1rem;font-weight:700;color:var(--ds-text)"
            )
            ui.label(f"Todo: {todo_text[:60]}").style(
                "font-size:0.78rem;color:var(--ds-text-2);font-style:italic"
            )

            search_inp = ui.input(label="Datei suchen", placeholder="Rechnung, Kosovo…").classes("w-full ds-input")
            file_list = ui.column().classes("w-full gap-1").style("max-height:300px;overflow-y:auto")

            def _filter(ev=None):
                file_list.clear()
                kw = search_inp.value.lower().strip()
                shown = [(p, l) for p, l in all_files if not kw or kw in l.lower()][:30]
                with file_list:
                    if not shown:
                        ui.label("Keine Dateien gefunden.").style("font-size:0.75rem;color:var(--ds-text-3)")
                        return
                    for path_str, label in shown:
                        def make_select(ps=path_str, lb=label):
                            def handler():
                                link_todo_doc(todo_id, ps, lb)
                                ui.notify(f"Verknüpft: {lb[:40]}", type="positive")
                                dlg.close()
                                refresh_cb()
                            return handler
                        with ui.row().classes("items-center gap-2 w-full").style(
                            "padding:5px 8px;border-radius:6px;cursor:pointer;"
                            "background:rgba(255,255,255,0.02)"
                        ).on("click", make_select()):
                            ui.icon("description").style("font-size:0.85rem;color:#00d4ff;flex-shrink:0")
                            ui.label(label).style(
                                "font-size:0.78rem;color:var(--ds-text);flex:1;"
                                "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                            )

            search_inp.on_value_change(lambda _: _filter())
            _filter()

            # Rechnungen verknüpfen
            invoices = get_invoices()
            if invoices:
                ui.separator().style("margin:4px 0")
                ui.label("Rechnung verknüpfen:").style("font-size:0.72rem;color:var(--ds-text-2)")
                with ui.column().classes("gap-1").style("max-height:120px;overflow-y:auto"):
                    for inv in invoices[:10]:
                        inv_label = f"{inv.get('vendor','?')} {inv.get('amount',0):.0f}€ ({inv.get('date','')})"
                        def make_inv_link(iid=inv["id"], ilabel=inv_label, ttid=todo_id, ttlabel=todo_text):
                            def handler():
                                link_invoice_todo(iid, ttid, ttlabel)
                                link_todo_doc(ttid, f"invoice:{iid}", ilabel)
                                ui.notify(f"Rechnung verknüpft", type="positive")
                                dlg.close()
                                refresh_cb()
                            return handler
                        with ui.row().classes("items-center gap-2").style(
                            "padding:4px 8px;border-radius:6px;cursor:pointer;"
                            "background:rgba(0,232,125,0.04)"
                        ).on("click", make_inv_link()):
                            ui.icon("receipt_long").style("font-size:0.8rem;color:#00e87d")
                            ui.label(inv_label[:55]).style("font-size:0.75rem;color:var(--ds-text-2)")

            with ui.row().classes("justify-end w-full"):
                ui.button("Abbrechen", on_click=dlg.close).props("flat").style("color:var(--ds-text-2)")

    dlg.open()


# ---------------------------------------------------------------------------
# TAB 1: Heute (Todos)
# ---------------------------------------------------------------------------

def _build_todos_tab() -> None:
    container = ui.column().classes("w-full gap-2")

    # --- Add Form ---
    with ui.card().classes("w-full rounded-xl border border-blue-100 p-4 shadow-sm mb-4"):
        section_title("Neue Aufgabe", "add_task")
        with ui.row().classes("w-full gap-3 items-end flex-wrap"):
            todo_input = ui.input(
                placeholder="z.B. Rechnung GASAG bis Freitag prüfen",
            ).classes("flex-1 min-w-48")

            priority_select = ui.select(
                options={"hoch": "Hoch", "normal": "Normal", "niedrig": "Niedrig"},
                value="normal",
                label="Priorität",
            ).classes("w-32")

            due_input = ui.input(
                placeholder="z.B. 2026-04-15",
                label="Fälligkeit (optional)",
            ).classes("w-40")

            def _add_todo():
                text = todo_input.value.strip()
                if not text:
                    ui.notify("Bitte Aufgabe eingeben", type="warning")
                    return
                add_todo(text, priority_select.value or "normal", due_input.value or "")
                todo_input.set_value("")
                due_input.set_value("")
                _refresh_todos()
                ui.notify("Aufgabe hinzugefügt", type="positive")

            ui.button("Aufgabe hinzufügen", icon="add", on_click=_add_todo).props(
                "unelevated color=primary"
            ).tooltip("Neue Aufgabe speichern")

    def _refresh_todos():
        container.clear()
        todos = get_todos()

        if not todos:
            with container:
                empty_state("task_alt", "Noch keine Aufgaben", "Trage oben deine erste Aufgabe ein — z.B. eine Rechnung prüfen oder einen Termin vorbereiten.")
            return

        # Group by priority
        groups = {"hoch": [], "normal": [], "niedrig": []}
        for t in todos:
            p = t.get("priority", "normal").lower()
            if p in groups:
                groups[p].append(t)
            else:
                groups["normal"].append(t)

        with container:
            for prio_key in ["hoch", "normal", "niedrig"]:
                items = groups[prio_key]
                if not items:
                    continue
                color = _PRIORITY_COLORS[prio_key]
                label = _PRIORITY_LABELS[prio_key]

                ui.label(label).style(
                    f"font-size:0.75rem;font-weight:700;text-transform:uppercase;"
                    f"letter-spacing:0.06em;color:{color};margin-top:8px;margin-bottom:4px"
                )

                for todo in items:
                    tid = todo["id"]
                    done = todo.get("done", False)
                    text = todo.get("text", "")
                    due = todo.get("due", "")

                    with ui.card().classes(_card_classes()):
                        with ui.column().classes("w-full gap-2"):
                            with ui.row().classes("w-full items-center gap-3"):
                                # Priority dot
                                ui.element("div").style(
                                    f"width:10px;height:10px;border-radius:50%;"
                                    f"background:{color};flex-shrink:0"
                                )

                                # Done checkbox
                                def make_toggle(t_id=tid):
                                    def _toggle():
                                        toggle_todo(t_id)
                                        _refresh_todos()
                                    return _toggle

                                ui.checkbox(value=done, on_change=make_toggle()).classes("flex-shrink-0")

                                # Text
                                text_style = (
                                    "flex:1;font-size:0.9rem;text-decoration:line-through;color:#9CA3AF"
                                    if done else
                                    "flex:1;font-size:0.9rem"
                                )
                                ui.label(text).style(text_style)

                                # Due date
                                if due:
                                    ui.label(due).style(
                                        "font-size:0.75rem;color:#9CA3AF;white-space:nowrap"
                                    )

                                # Link button
                                def make_link_dialog(t_id=tid, t_text=text):
                                    def open_link():
                                        _show_link_dialog(t_id, t_text, _refresh_todos)
                                    return open_link

                                ui.button(
                                    icon="link",
                                    on_click=make_link_dialog(),
                                ).props("flat round dense size=sm").style("color:#a78bfa").tooltip("Dokument verknüpfen")

                                # Delete button
                                def make_delete(t_id=tid):
                                    def _del():
                                        delete_todo(t_id)
                                        _refresh_todos()
                                        ui.notify("Aufgabe gelöscht", type="negative")
                                    return _del

                                ui.button(
                                    icon="delete_outline",
                                    on_click=make_delete(),
                                ).props("flat round dense color=negative size=sm").tooltip("Aufgabe entfernen")

                            # Verknüpfte Dokumente anzeigen
                            linked_docs = get_linked_docs(tid)
                            if linked_docs:
                                with ui.row().classes("gap-2 flex-wrap"):
                                    for doc_ref in linked_docs:
                                        def make_unlink(t_id=tid, dpath=doc_ref["path"]):
                                            def handler():
                                                unlink_todo_doc(t_id, dpath)
                                                _refresh_todos()
                                            return handler
                                        with ui.row().classes("items-center gap-1").style(
                                            "padding:2px 8px;border-radius:4px;"
                                            "background:rgba(0,212,255,0.08);border:1px solid rgba(0,212,255,0.2)"
                                        ):
                                            ui.icon("description").style("font-size:0.7rem;color:#00d4ff")
                                            ui.label(doc_ref["label"][:35]).style(
                                                "font-size:0.65rem;color:var(--ds-text-2)"
                                            )
                                            ui.button(
                                                icon="close", on_click=make_unlink()
                                            ).props("flat round dense").style(
                                                "font-size:0.5rem;color:var(--ds-text-3);width:16px;height:16px;min-width:16px"
                                            )

    _refresh_todos()


# ---------------------------------------------------------------------------
# TAB 2: Ausgaben (Expenses)
# ---------------------------------------------------------------------------

def _build_expenses_tab() -> None:
    container = ui.column().classes("w-full gap-2")
    summary_label = ui.label("").style(
        "font-size:1.5rem;font-weight:700;color:#3B82F6"
    )

    def _calc_monthly(expenses: list[dict]) -> float:
        total = 0.0
        for e in expenses:
            if not e.get("active", True):
                continue
            amt = float(e.get("amount", 0))
            cycle = e.get("cycle", "monatlich").lower()
            if cycle == "jährlich":
                total += amt / 12
            elif cycle == "quartalsweise":
                total += amt / 3
            elif cycle == "wöchentlich":
                total += amt * 4.33
            else:
                total += amt
        return total

    def _refresh_expenses():
        container.clear()
        expenses = get_expenses()
        monthly = _calc_monthly(expenses)
        summary_label.set_text(f"€ {monthly:.2f} / Monat")

        if not expenses:
            with container:
                empty_state("euro_symbol", "Noch keine Ausgaben erfasst", "Trage unten wiederkehrende Kosten ein — z.B. Abonnements, Miete oder Softwarelizenzen.")
            return

        with container:
            for exp in expenses:
                eid = exp["id"]
                name = exp.get("name", "")
                amount = float(exp.get("amount", 0))
                cycle = exp.get("cycle", "monatlich")
                category = exp.get("category", "")

                with ui.card().classes(_card_classes()):
                    with ui.row().classes("w-full items-center gap-3"):
                        ui.icon("receipt_long").style("font-size:1.2rem;color:#3B82F6;flex-shrink:0")

                        with ui.column().classes("flex-1 gap-0"):
                            ui.label(name).style("font-size:0.9rem;font-weight:600")
                            cat_cycle = f"{category} · {cycle}" if category else cycle
                            ui.label(cat_cycle).style("font-size:0.75rem;color:#9CA3AF")

                        ui.label(f"€ {amount:.2f}").style(
                            "font-size:0.95rem;font-weight:700;color:#111827;white-space:nowrap"
                        )

                        def make_delete_exp(e_id=eid):
                            def _del():
                                delete_expense(e_id)
                                _refresh_expenses()
                                ui.notify("Ausgabe gelöscht", type="negative")
                            return _del

                        ui.button(
                            icon="delete_outline",
                            on_click=make_delete_exp(),
                        ).props("flat round dense color=negative size=sm").tooltip("Ausgabe entfernen")

    # Summary card
    with ui.card().classes("w-full rounded-xl border border-blue-100 p-4 shadow-sm mb-4"):
        with ui.row().classes("items-center gap-4"):
            ui.icon("account_balance_wallet").style("font-size:2rem;color:#3B82F6")
            with ui.column().classes("gap-0"):
                ui.label("Monatliche Gesamtkosten").style(
                    "font-size:0.75rem;font-weight:500;color:#6B7280;text-transform:uppercase;letter-spacing:0.04em"
                )
                summary_label

    # Add Form
    with ui.card().classes("w-full rounded-xl border border-gray-100 p-4 shadow-sm mb-4"):
        section_title("Neue Ausgabe", "add")
        with ui.row().classes("w-full gap-3 items-end flex-wrap"):
            name_input = ui.input(placeholder="z.B. Adobe Acrobat, GASAG, Miete", label="Bezeichnung").classes("flex-1 min-w-40")
            amount_input = ui.number(placeholder="0.00", label="Betrag (€)", format="%.2f", min=0).classes("w-32")
            cycle_select = ui.select(
                options=["monatlich", "quartalsweise", "jährlich", "wöchentlich"],
                value="monatlich",
                label="Zyklus",
            ).classes("w-36")
            category_input = ui.input(placeholder="Kategorie (optional)", label="Kategorie").classes("w-36")

            def _add_expense():
                name = name_input.value.strip()
                if not name:
                    ui.notify("Bitte Bezeichnung eingeben", type="warning")
                    return
                try:
                    amt = float(amount_input.value or 0)
                except (ValueError, TypeError):
                    ui.notify("Ungültiger Betrag", type="warning")
                    return
                add_expense(name, amt, cycle_select.value or "monatlich", category_input.value or "")
                name_input.set_value("")
                amount_input.set_value(None)
                category_input.set_value("")
                _refresh_expenses()
                ui.notify("Ausgabe hinzugefügt", type="positive")

            ui.button("Hinzufügen", icon="add", on_click=_add_expense).props(
                "unelevated color=primary"
            )

    _refresh_expenses()


# ---------------------------------------------------------------------------
# TAB 3: Abos (Subscriptions)
# ---------------------------------------------------------------------------

def _build_subscriptions_tab() -> None:
    container = ui.column().classes("w-full gap-2")

    def _needs_review() -> bool:
        last = get_last_sub_check()
        if last is None:
            return True
        try:
            last_date = date.fromisoformat(last)
            delta = (date.today() - last_date).days
            return delta > 30
        except Exception:
            return True

    def _refresh_subs():
        container.clear()
        subs = get_subscriptions()

        with container:
            if _needs_review():
                callout(
                    "Deine Abonnements wurden seit mehr als 30 Tagen nicht überprüft. "
                    "Jetzt prüfen und nicht mehr benötigte Abos kündigen!",
                    variant="warning",
                )
                ui.button(
                    "Überprüfung abschließen",
                    icon="check_circle",
                    on_click=lambda: (mark_sub_check_done(), _refresh_subs(), ui.notify("Überprüfung markiert", type="positive")),
                ).props("unelevated color=warning").classes("mb-4")

            if not subs:
                empty_state("subscriptions", "Noch keine Abonnements",
                           "Trage wiederkehrende Dienste ein — z.B. Adobe, Spotify, Office 365 — "
                           "und behalte monatliche Kosten im Blick.")
                return

            for sub in subs:
                sid = sub["id"]
                name = sub.get("name", "")
                amount = float(sub.get("amount", 0))
                cycle = sub.get("cycle", "monatlich")
                url = sub.get("url", "")
                active = sub.get("active", True)
                last_review = sub.get("last_review")

                border_color = "#22C55E" if active else "#EF4444"
                with ui.card().classes(_card_classes()).style(f"border-left:4px solid {border_color}"):
                    with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                        ui.icon("subscriptions").style(
                            f"font-size:1.2rem;color:{border_color};flex-shrink:0"
                        )

                        with ui.column().classes("flex-1 gap-0 min-w-32"):
                            ui.label(name).style("font-size:0.9rem;font-weight:600")
                            detail = f"€ {amount:.2f} / {cycle}"
                            if url:
                                detail += f" · {url}"
                            ui.label(detail).style("font-size:0.75rem;color:#9CA3AF")
                            if last_review:
                                ui.label(f"Zuletzt geprüft: {last_review}").style(
                                    "font-size:0.7rem;color:#9CA3AF"
                                )

                        status_badge("Aktiv" if active else "Inaktiv", "success" if active else "neutral")

                        def make_keep(s_id=sid):
                            def _keep():
                                review_subscription(s_id, True)
                                _refresh_subs()
                                ui.notify("Abo behalten", type="positive")
                            return _keep

                        def make_cancel(s_id=sid):
                            def _cancel():
                                review_subscription(s_id, False)
                                _refresh_subs()
                                ui.notify("Abo als inaktiv markiert", type="warning")
                            return _cancel

                        def make_delete_sub(s_id=sid):
                            def _del():
                                delete_subscription(s_id)
                                _refresh_subs()
                                ui.notify("Abo gelöscht", type="negative")
                            return _del

                        ui.button("Behalten", icon="check", on_click=make_keep()).props(
                            "outline color=positive dense size=sm"
                        )
                        ui.button("Kündigen", icon="close", on_click=make_cancel()).props(
                            "outline color=negative dense size=sm"
                        )
                        ui.button(icon="delete_outline", on_click=make_delete_sub()).props(
                            "flat round dense color=negative size=sm"
                        )

    # Add Form
    with ui.card().classes("w-full rounded-xl border border-gray-100 p-4 shadow-sm mb-4"):
        section_title("Neues Abonnement", "add")
        with ui.row().classes("w-full gap-3 items-end flex-wrap"):
            sub_name_input = ui.input(placeholder="z.B. Spotify", label="Name").classes("flex-1 min-w-40")
            sub_amount_input = ui.number(placeholder="0.00", label="Betrag (€)", format="%.2f", min=0).classes("w-32")
            sub_cycle_select = ui.select(
                options=["monatlich", "quartalsweise", "jährlich", "wöchentlich"],
                value="monatlich",
                label="Zyklus",
            ).classes("w-36")
            sub_url_input = ui.input(placeholder="URL (optional)", label="URL").classes("w-48")

            def _add_sub():
                name = sub_name_input.value.strip()
                if not name:
                    ui.notify("Bitte Namen eingeben", type="warning")
                    return
                try:
                    amt = float(sub_amount_input.value or 0)
                except (ValueError, TypeError):
                    ui.notify("Ungültiger Betrag", type="warning")
                    return
                add_subscription(name, amt, sub_cycle_select.value or "monatlich", sub_url_input.value or "")
                sub_name_input.set_value("")
                sub_amount_input.set_value(None)
                sub_url_input.set_value("")
                _refresh_subs()
                ui.notify("Abonnement hinzugefügt", type="positive")

            ui.button("Hinzufügen", icon="add", on_click=_add_sub).props(
                "unelevated color=primary"
            )

    _refresh_subs()


# ---------------------------------------------------------------------------
# TAB: Auswertung — Finanz-Dashboard
# ---------------------------------------------------------------------------

def _build_finance_dashboard() -> None:
    """Monatliche Ausgaben-Auswertung mit Rechnungen und Abos."""
    from ...assistant_store import get_invoices, get_expenses, get_subscriptions, delete_invoice, update_invoice
    from datetime import date, datetime
    from collections import defaultdict

    today = date.today()

    invoices = get_invoices()
    expenses = get_expenses()
    subs = [s for s in get_subscriptions() if s.get("active", True)]

    # ── Monatlicher Betrag aus Abos / Ausgaben berechnen ──────────────────
    def _monthly_amount(items: list[dict]) -> float:
        total = 0.0
        for e in items:
            amt = float(e.get("amount", 0))
            cycle = e.get("cycle", "monatlich").lower()
            if cycle in ("jährlich", "jaehrlich"):
                total += amt / 12
            elif cycle in ("quartalsweise", "quartärlich"):
                total += amt / 3
            elif cycle in ("wöchentlich", "woechentlich"):
                total += amt * 4.33
            else:
                total += amt
        return total

    monthly_recurring = _monthly_amount(expenses + subs)

    # ── Rechnungen nach Monat gruppieren ──────────────────────────────────
    by_month: dict[str, float] = defaultdict(float)
    by_category: dict[str, float] = defaultdict(float)

    for inv in invoices:
        raw_date = inv.get("date", "")
        try:
            ym = raw_date[:7]  # YYYY-MM  (z.B. "2026-03")
            datetime.strptime(ym, "%Y-%m")  # Validierung — wirft bei ungültigem Format
        except Exception:
            ym = today.strftime("%Y-%m")
        amt = float(inv.get("amount", 0))
        by_month[ym] += amt
        cat = inv.get("category", "Sonstiges")
        by_category[cat] += amt

    # Letzte 6 Monate sicherstellen
    months_6: list[str] = []
    for i in range(5, -1, -1):
        import calendar
        yr = today.year
        mn = today.month - i
        while mn <= 0:
            mn += 12
            yr -= 1
        months_6.append(f"{yr:04d}-{mn:02d}")

    max_val = max((by_month.get(m, 0) for m in months_6), default=1) or 1
    month_labels = {
        "01": "Jan", "02": "Feb", "03": "Mär", "04": "Apr",
        "05": "Mai", "06": "Jun", "07": "Jul", "08": "Aug",
        "09": "Sep", "10": "Okt", "11": "Nov", "12": "Dez",
    }

    with ui.column().classes("w-full gap-5"):

        # ── KPI-Kacheln ─────────────────────────────────────────────────────
        total_invoices_year = sum(
            float(inv.get("amount", 0))
            for inv in invoices
            if inv.get("date", "").startswith(str(today.year))
        )
        total_invoices_month = by_month.get(today.strftime("%Y-%m"), 0.0)

        with ui.row().classes("gap-3 flex-wrap w-full"):
            _morning_stat("receipt_long", "Rechnungen diesen Monat",
                          f"{total_invoices_month:.0f} €", "#00d4ff",
                          f"{sum(1 for i in invoices if i.get('date','').startswith(today.strftime('%Y-%m')))} Belege",
                          "var(--ds-text-2)")
            _morning_stat("receipt_long", f"Rechnungen {today.year}",
                          f"{total_invoices_year:.0f} €", "#a78bfa",
                          f"{len(invoices)} Belege gesamt", "var(--ds-text-2)")
            _morning_stat("repeat", "Laufende Kosten/Monat",
                          f"{monthly_recurring:.0f} €", "#ff9f0a",
                          f"{len(expenses)+len(subs)} Positionen", "var(--ds-text-2)")
            _morning_stat("euro", "Gesamt (Monat est.)",
                          f"{total_invoices_month + monthly_recurring:.0f} €", "#00e87d",
                          "Rechnungen + laufende Kosten", "var(--ds-text-2)")

        # ── Balkendiagramm: Letzte 6 Monate ─────────────────────────────────
        section_title("Rechnungen letzte 6 Monate", "bar_chart")
        with ui.card().classes("ds-card-flat w-full"):
            with ui.row().classes("items-end gap-2 w-full").style("height:160px;padding:8px 4px 0"):
                for ym in months_6:
                    val = by_month.get(ym, 0.0)
                    pct = (val / max_val) * 100 if max_val > 0 else 0
                    mm = ym[5:7]
                    is_current = ym == today.strftime("%Y-%m")
                    bar_color = "#00d4ff" if is_current else "rgba(0,212,255,0.35)"

                    with ui.column().classes("items-center flex-1 gap-1").style("height:100%;justify-content:flex-end"):
                        if val > 0:
                            ui.label(f"{val:.0f}€").style(
                                "font-size:0.6rem;color:var(--ds-text-2);white-space:nowrap"
                            )
                        ui.element("div").style(
                            f"width:100%;max-width:48px;height:{max(pct, 2):.0f}%;border-radius:4px 4px 0 0;"
                            f"background:{bar_color};transition:height 0.3s"
                        )
                        ui.label(month_labels.get(mm, mm)).style(
                            f"font-size:0.68rem;font-weight:{'700' if is_current else '400'};"
                            f"color:{'#00d4ff' if is_current else 'var(--ds-text-2)'}"
                        )

        # ── Kategorien-Aufteilung ────────────────────────────────────────────
        if by_category:
            section_title("Ausgaben nach Kategorie", "donut_large")
            total_cat = sum(by_category.values()) or 1
            _CAT_COLORS = ["#00d4ff", "#a78bfa", "#00e87d", "#ff9f0a", "#ff3366",
                           "#38bdf8", "#c084fc", "#34d399", "#fb923c", "#f87171"]

            with ui.card().classes("ds-card-flat w-full"):
                with ui.column().classes("gap-2 w-full"):
                    for i, (cat, amt) in enumerate(sorted(by_category.items(), key=lambda x: -x[1])):
                        pct = (amt / total_cat) * 100
                        color = _CAT_COLORS[i % len(_CAT_COLORS)]
                        with ui.row().classes("items-center gap-3 w-full"):
                            ui.element("div").style(
                                f"width:10px;height:10px;border-radius:50%;background:{color};flex-shrink:0"
                            )
                            ui.label(cat).style("font-size:0.8rem;color:var(--ds-text);min-width:120px")
                            with ui.element("div").style(
                                "flex:1;height:8px;background:rgba(255,255,255,0.06);border-radius:4px;overflow:hidden"
                            ):
                                ui.element("div").style(
                                    f"width:{pct:.0f}%;height:100%;background:{color};border-radius:4px"
                                )
                            ui.label(f"{amt:.2f} €").style(
                                "font-size:0.78rem;font-weight:600;color:var(--ds-text);min-width:70px;text-align:right"
                            )
                            ui.label(f"{pct:.0f}%").style(
                                "font-size:0.68rem;color:var(--ds-text-2);min-width:34px;text-align:right"
                            )

        # ── Rechnungsliste ───────────────────────────────────────────────────
        section_title(f"Alle Rechnungen ({len(invoices)})", "receipt_long")
        inv_container = ui.column().classes("w-full gap-2")

        def _render_invoices():
            inv_container.clear()
            all_inv = get_invoices()
            with inv_container:
                if not all_inv:
                    with ui.row().classes("items-center gap-3").style(
                        "padding:16px;background:rgba(10,22,40,0.6);border-radius:8px;"
                        "border:1px dashed rgba(0,212,255,0.2)"
                    ):
                        ui.icon("receipt").style("color:var(--ds-text-3);font-size:1.5rem")
                        with ui.column().classes("gap-0"):
                            ui.label("Keine Rechnungen erfasst").style("font-size:0.85rem;color:var(--ds-text-2)")
                            ui.label("Rechnungen werden automatisch erkannt wenn Dokumente mit Typ 'Rechnung' "
                                     "sortiert werden.").style("font-size:0.72rem;color:var(--ds-text-3)")
                    return

                # Sortiert: neueste zuerst
                for inv in sorted(all_inv, key=lambda x: x.get("date", ""), reverse=True):
                    inv_id = inv["id"]
                    amt = float(inv.get("amount", 0))
                    cat = inv.get("category", "Sonstiges")
                    vendor = inv.get("vendor", "Unbekannt")
                    inv_date = inv.get("date", "")
                    inv_nr = inv.get("invoice_number", "")
                    src = inv.get("source_file", "")

                    with ui.card().classes("ds-card-flat w-full"):
                        with ui.row().classes("items-center gap-3 w-full"):
                            with ui.element("div").style(
                                "width:36px;height:36px;border-radius:8px;flex-shrink:0;"
                                "background:rgba(0,212,255,0.08);border:1px solid rgba(0,212,255,0.2);"
                                "display:flex;align-items:center;justify-content:center"
                            ):
                                ui.icon("receipt_long").style("font-size:1rem;color:#00d4ff")

                            with ui.column().classes("gap-0 flex-1 min-w-0"):
                                with ui.row().classes("items-center gap-2 flex-wrap"):
                                    ui.label(vendor).style(
                                        "font-size:0.85rem;font-weight:600;color:var(--ds-text)"
                                    )
                                    if inv_nr:
                                        ui.label(f"Nr. {inv_nr}").style(
                                            "font-size:0.65rem;padding:1px 6px;border-radius:4px;"
                                            "background:rgba(167,139,250,0.1);color:#a78bfa;"
                                            "border:1px solid rgba(167,139,250,0.2)"
                                        )
                                with ui.row().classes("items-center gap-2"):
                                    ui.label(inv_date).style("font-size:0.7rem;color:var(--ds-text-3)")
                                    ui.label("·").style("color:var(--ds-text-3)")
                                    ui.label(cat).style("font-size:0.7rem;color:var(--ds-text-2)")
                                    if src:
                                        ui.label("·").style("color:var(--ds-text-3)")
                                        ui.label(src[:30]).style("font-size:0.65rem;color:var(--ds-text-3)")

                            ui.label(f"{amt:.2f} €").style(
                                "font-size:1rem;font-weight:700;color:var(--ds-text);white-space:nowrap"
                            )

                            # Verknüpfte Todos
                            linked_todos = get_linked_todos_for_invoice(inv_id)
                            if linked_todos:
                                for lt in linked_todos[:2]:
                                    ui.label(f"✅ {lt['label'][:30]}").style(
                                        "font-size:0.62rem;padding:1px 6px;border-radius:4px;"
                                        "background:rgba(167,139,250,0.1);color:#a78bfa;"
                                        "border:1px solid rgba(167,139,250,0.2);white-space:nowrap"
                                    )

                            def make_todo_from_inv(iid=inv_id, ivendor=vendor, iamt=amt):
                                def handler():
                                    todo_text = f"Rechnung prüfen: {ivendor} — {iamt:.2f} €"
                                    add_todo(todo_text, priority="normal")
                                    # Todo-ID ist der letzte Eintrag
                                    todos = get_todos()
                                    if todos:
                                        last_todo = todos[-1]
                                        link_invoice_todo(iid, last_todo["id"], todo_text)
                                    ui.notify("Todo erstellt und verknüpft!", type="positive")
                                    _render_invoices()
                                return handler

                            ui.button(icon="add_task", on_click=make_todo_from_inv()).props(
                                "flat round dense"
                            ).style("color:#a78bfa").tooltip("Todo erstellen & verknüpfen")

                            def make_del(iid=inv_id):
                                def handler():
                                    delete_invoice(iid)
                                    _render_invoices()
                                    ui.notify("Rechnung gelöscht", type="negative")
                                return handler

                            ui.button(icon="delete_outline", on_click=make_del()).props(
                                "flat round dense"
                            ).style("color:var(--ds-error)")

        _render_invoices()

        # Manuell erfassen
        section_title("Rechnung manuell erfassen", "add")
        with ui.card().classes("ds-card-flat w-full"):
            with ui.grid(columns=3).classes("gap-3 w-full"):
                v_inp = ui.input(label="Lieferant", placeholder="Amazon, Telekom…").classes("ds-input w-full")
                a_inp = ui.number(label="Betrag (€)", value=0, format="%.2f", min=0).classes("ds-input w-full")
                d_inp = ui.input(label="Datum", placeholder="YYYY-MM-DD",
                                 value=today.isoformat()).classes("ds-input w-full")
                c_inp = ui.input(label="Kategorie", placeholder="Software, Büro…").classes("ds-input w-full")
                nr_inp = ui.input(label="Rechnungsnr. (optional)").classes("ds-input w-full")
                src_inp = ui.input(label="Quelldatei (optional)").classes("ds-input w-full")

            def do_add_manual():
                from ...assistant_store import add_invoice as _add_inv
                if not v_inp.value.strip():
                    ui.notify("Lieferant ist Pflichtfeld.", type="warning")
                    return
                _add_inv(
                    vendor=v_inp.value.strip(),
                    amount=float(a_inp.value or 0),
                    date=d_inp.value.strip() or today.isoformat(),
                    category=c_inp.value.strip() or "Sonstiges",
                    invoice_number=nr_inp.value.strip(),
                    source_file=src_inp.value.strip(),
                )
                ui.notify("Rechnung gespeichert!", type="positive")
                v_inp.value = ""
                a_inp.value = 0
                nr_inp.value = ""
                _render_invoices()

            ui.button("Rechnung erfassen", on_click=do_add_manual, icon="add").classes("ds-btn-primary").tooltip("Neue Rechnung manuell speichern")


# ---------------------------------------------------------------------------
# TAB: Feed (vollständiger Ereignisstream)
# ---------------------------------------------------------------------------

def _build_full_feed_tab() -> None:
    """Vollständiger Gehirn-Feed mit Filter und Live-Polling."""
    from ...feed_store import SOURCE_META, get_items
    from datetime import datetime as _dt

    filter_state = {"source": "alle"}
    container = ui.column().classes("w-full gap-2")

    def _render_feed(source_filter: str = "alle") -> None:
        container.clear()
        items = get_items(limit=100)
        if source_filter != "alle":
            items = [i for i in items if i.get("source") == source_filter]

        with container:
            if not items:
                with ui.element("div").style(
                    "text-align:center;padding:48px 24px;color:var(--ds-text-3);max-width:480px;margin:0 auto"
                ):
                    with ui.element("div").style(
                        "width:64px;height:64px;border-radius:16px;margin:0 auto 16px;"
                        "background:rgba(168,85,247,0.1);border:1px solid rgba(168,85,247,0.2);"
                        "display:flex;align-items:center;justify-content:center"
                    ):
                        ui.icon("hub").style("font-size:2rem;color:#a855f7")
                    ui.label("Noch keine Aktivitäten").style(
                        "font-size:1rem;font-weight:700;color:var(--ds-text);margin-bottom:8px"
                    )
                    ui.label(
                        "Hier erscheinen alle Ereignisse sobald das System aktiv wird — "
                        "z.B. verarbeitete Dokumente oder eingehende E-Mails."
                    ).style("font-size:0.8rem;line-height:1.6;margin-bottom:16px")
                    with ui.row().classes("gap-3 justify-center"):
                        ui.button("Zum Chat", icon="forum", on_click=lambda: ui.navigate.to("/")).props(
                            "flat dense no-caps"
                        ).style("color:#a855f7;border:1px solid rgba(168,85,247,0.3);border-radius:8px")
                        ui.button("E-Mail einrichten", icon="email", on_click=lambda: ui.navigate.to("/email")).props(
                            "flat dense no-caps"
                        ).style("color:#00d4ff;border:1px solid rgba(0,212,255,0.3);border-radius:8px")
                return

            for item in items:
                src = SOURCE_META.get(item.get("source", "system"),
                                      {"icon": "circle", "color": "#6b7280",
                                       "label": item.get("source", "?")})
                try:
                    ts = _dt.fromisoformat(item["timestamp"]).strftime("%d.%m.%Y %H:%M")
                except Exception:
                    ts = ""

                is_new = not item.get("seen", False)

                with ui.element("div").style(
                    f"padding:10px 14px;border-radius:10px;margin-bottom:4px;"
                    f"background:{'rgba(168,85,247,0.05)' if is_new else 'rgba(10,22,40,0.6)'};"
                    f"border:1px solid {'rgba(168,85,247,0.25)' if is_new else 'rgba(255,255,255,0.06)'};"
                ):
                    with ui.row().classes("items-start gap-3 w-full"):
                        with ui.element("div").style(
                            f"width:32px;height:32px;border-radius:8px;flex-shrink:0;"
                            f"background:{src['color']}15;border:1px solid {src['color']}30;"
                            "display:flex;align-items:center;justify-content:center;margin-top:1px"
                        ):
                            ui.icon(src["icon"]).style(f"font-size:1rem;color:{src['color']}")

                        with ui.column().classes("gap-1 flex-1 min-w-0"):
                            with ui.row().classes("items-center gap-2 w-full flex-wrap"):
                                ui.label(src["label"]).style(
                                    f"font-size:0.6rem;font-weight:700;padding:1px 7px;"
                                    f"border-radius:4px;background:{src['color']}12;"
                                    f"color:{src['color']};border:1px solid {src['color']}20"
                                )
                                if is_new:
                                    ui.label("NEU").style(
                                        "font-size:0.58rem;font-weight:800;padding:1px 5px;"
                                        "border-radius:4px;background:rgba(168,85,247,0.2);"
                                        "color:#a855f7;border:1px solid rgba(168,85,247,0.4)"
                                    )
                                ui.label(item.get("title", "")[:80]).style(
                                    "font-size:0.82rem;font-weight:600;color:var(--ds-text);flex:1;"
                                    "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                                )
                                ui.label(ts).style(
                                    "font-size:0.63rem;color:var(--ds-text-3);white-space:nowrap;margin-left:auto"
                                )

                            if item.get("content"):
                                ui.label(item["content"][:150] + ("…" if len(item["content"]) > 150 else "")).style(
                                    "font-size:0.74rem;color:var(--ds-text-2);line-height:1.5"
                                )

    # ── Filter-Bar ──────────────────────────────────────────────────────────
    with ui.column().classes("w-full gap-3"):
        with ui.row().classes("items-center gap-2 flex-wrap"):
            ui.icon("hub").style("font-size:1.1rem;color:#a855f7")
            ui.label("Ereignis-Feed").style(
                "font-size:0.9rem;font-weight:700;color:var(--ds-text);flex:1"
            )
            ui.button(icon="refresh", on_click=lambda: _render_feed(filter_state["source"])).props(
                "round dense flat"
            ).style("color:var(--ds-text-2)")

        # Source-Filter Chips
        sources = ["alle"] + list(SOURCE_META.keys())
        with ui.row().classes("gap-2 flex-wrap"):
            for src_key in sources:
                meta = SOURCE_META.get(src_key, {"icon": "filter_list", "color": "#6b7280", "label": "Alle"})
                label = "Alle" if src_key == "alle" else meta["label"]
                icon = "filter_list" if src_key == "alle" else meta["icon"]

                def _make_handler(k=src_key):
                    def _h():
                        filter_state["source"] = k
                        _render_feed(k)
                    return _h

                ui.button(label, icon=icon, on_click=_make_handler()).props(
                    "dense unelevated no-caps"
                ).style(
                    f"font-size:0.72rem;padding:3px 10px;border-radius:99px;"
                    f"background:rgba({_hex_to_rgb(meta['color']) if src_key != 'alle' else '107,114,128'},0.12);"
                    f"color:{'#a855f7' if src_key == 'alle' else meta['color']};"
                    f"border:1px solid rgba({_hex_to_rgb(meta['color']) if src_key != 'alle' else '107,114,128'},0.3)"
                )

        _render_feed()

        # Live-Polling (alle 10s)
        def _poll():
            try:
                _render_feed(filter_state["source"])
            except Exception:
                pass

        ui.timer(10.0, _poll)


def _hex_to_rgb(hex_color: str) -> str:
    """Hex-Farbe zu 'R,G,B' umwandeln fuer rgba()."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"{r},{g},{b}"
    return "128,128,128"


# ---------------------------------------------------------------------------
# Main build()
# ---------------------------------------------------------------------------

def build() -> None:
    """Assistent-Seite aufbauen."""
    from ...config import load_config
    try:
        cfg = load_config()
    except Exception:
        cfg = {}

    page_header("Mein Assistent", "Tagesüberblick · Aufgaben · Ausgaben · Abonnements · Aktivitäten")

    with ui.tabs().classes("w-full").props("dense align=left") as tabs:
        tab_morgen     = ui.tab("morgen",     label="Morgen",        icon="wb_sunny"     ).tooltip("Tagesüberblick: Todos, Termine, Inbox & E-Mails")
        tab_heute      = ui.tab("heute",      label="Aufgaben",      icon="task_alt"     ).tooltip("Aufgabenliste verwalten und neue Todos anlegen")
        tab_feed       = ui.tab("feed",       label="Aktivitäten",   icon="hub"          ).tooltip("Alle Ereignisse: Dokumente, E-Mails, System-Aktivitäten")
        tab_ausgaben   = ui.tab("ausgaben",   label="Ausgaben",      icon="euro_symbol"  ).tooltip("Wiederkehrende Kosten und Rechnungen im Überblick")
        tab_auswertung = ui.tab("auswertung", label="Auswertung",    icon="bar_chart"    ).tooltip("Finanzauswertung: Charts, Kategorien, Trends")
        tab_abos       = ui.tab("abos",       label="Abonnements",   icon="subscriptions").tooltip("Aktive Abos prüfen, verwalten und kündigen")

    with ui.tab_panels(tabs, value=tab_morgen).classes("w-full"):
        with ui.tab_panel(tab_morgen):
            _build_morning(cfg)

        with ui.tab_panel(tab_heute):
            _build_todos_tab()

        with ui.tab_panel(tab_feed):
            _build_full_feed_tab()

        with ui.tab_panel(tab_ausgaben):
            _build_expenses_tab()

        with ui.tab_panel(tab_auswertung):
            _build_finance_dashboard()

        with ui.tab_panel(tab_abos):
            _build_subscriptions_tab()


