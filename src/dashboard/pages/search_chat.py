"""Universal Search Chat — Hauptdashboard.

Durchsucht Dokumente, Todos, Ausgaben, Abos, E-Mail-Regeln UND
fuehrt normale Gespraeche (Begruessung, Statistiken, Charts, etc.).
"""

from __future__ import annotations

import re as _re
import random as _random
from datetime import datetime
from pathlib import Path

from nicegui import run, ui

from ..agent import (
    DocSorterAgent,
    _is_greeting,
    _is_thanks,
    _is_wellbeing,
    _is_affirmation,
    _is_negation,
    _is_help_request,
    _extract_date_filter,
)


# ---------------------------------------------------------------------------
# Konversations-Antworten (HTML, unabhaengig vom Archiv-Chat-Agent)
# ---------------------------------------------------------------------------

def _chat_response(agent: DocSorterAgent, val: str) -> dict | None:
    """Gibt {'html', 'icon', 'color'} zurueck wenn val konversationell ist.

    None bedeutet: normaler Suchbegriff, bitte _search_all verwenden.
    """
    lower = val.lower().strip()

    # --- Begruessung ---
    if _is_greeting(lower):
        texts = [
            "Hallo! 👋 Ich bin dein Assistent. Du kannst hier alles durchsuchen — "
            "Dokumente, Todos, Ausgaben, Abos — oder einfach mit mir reden.",
            "Hi! Was kann ich für dich tun? Ich durchsuche Dokumente, beantworte Fragen "
            "und zeige Statistiken.",
            "Hey! Schreib mir einen Suchbegriff oder stell mir eine Frage — ich helfe dir.",
        ]
        return {
            "icon": "waving_hand", "color": "#a78bfa",
            "html": (
                _random.choice(texts) + "<br><br>"
                "💡 <b>Beispiele:</b> <i>Rechnung GASAG</i> · "
                "<i>Wie viele Verträge?</i> · <i>Timeline März 2024</i> · "
                "<i>Was steht in vertrag.pdf?</i>"
            ),
        }

    # --- Dankeschoen / positives Feedback ---
    if _is_thanks(lower):
        texts = [
            "Gerne! Noch etwas das ich suchen oder beantworten soll?",
            "Immer gerne! Falls du noch etwas brauchst — einfach schreiben.",
            "Kein Problem! Was kann ich noch für dich tun?",
            "Freut mich! 😊 Weiteres Anliegen?",
        ]
        return {"icon": "sentiment_satisfied", "color": "#00e87d",
                "html": _random.choice(texts)}

    # --- Wie geht's / Was geht / Umgangssprache ---
    if _is_wellbeing(lower):
        responses = [
            "Läuft! 😄 Ich bin der Such-Bot — alles im grünen Bereich. Was suchst du?",
            "Alles fit! 💪 Bereit zum Suchen. Einfach einen Begriff eingeben.",
            "Bestens! 🤖 Was geht bei dir? Wie kann ich helfen?",
            "Voll im Flow! Was steht an — soll ich etwas suchen?",
            "Danke der Nachfrage — läuft! Was brauchst du?",
        ]
        return {
            "icon": "smart_toy", "color": "#a78bfa",
            "html": _random.choice(responses),
        }

    # --- Zustimmung (ja, klar, genau, ...) ---
    if _is_affirmation(lower):
        responses = [
            "Alles klar! Was soll ich suchen oder beantworten?",
            "Super! Einfach einen Begriff eingeben oder eine Frage stellen.",
            "Prima! Womit kann ich dir helfen?",
            "Verstanden — was darf ich für dich tun?",
        ]
        return {"icon": "check_circle", "color": "#00e87d",
                "html": _random.choice(responses)}

    # --- Ablehnung (nein, nö, nee, ...) ---
    if _is_negation(lower):
        responses = [
            "Kein Problem! Sag mir einfach was du stattdessen suchst.",
            "Alright — was kann ich sonst für dich tun?",
            "Okay, kein Stress. Einfach schreiben wenn du etwas brauchst.",
            "Verstanden! Ich bin hier wenn du etwas brauchst.",
        ]
        return {"icon": "sentiment_neutral", "color": "#ff9f0a",
                "html": _random.choice(responses)}

    # --- Wie funktioniert das? / Kannst du helfen? ---
    if _is_help_request(lower):
        return {
            "icon": "manage_search", "color": "#00d4ff",
            "html": (
                "<b>Ich bin der Such-Chat</b> — dein Assistent für alles was du "
                "finden oder wissen willst. So funktioniere ich:<br><br>"
                "🔍 <b>Suchen:</b> Gib einfach einen Begriff ein — z.B. "
                "<em>Rechnung</em>, <em>GASAG</em>, <em>Netflix</em> oder "
                "<em>Kosovo 2024</em>. Ich durchsuche alle Dokumente, Todos, "
                "Ausgaben und Abos gleichzeitig.<br><br>"
                "📊 <b>Statistiken:</b> Frag mich direkt — "
                "<em>Wie viele Rechnungen gibt es?</em> oder "
                "<em>Wie oft kommt GASAG vor?</em><br><br>"
                "📅 <b>Timeline:</b> <em>Was wurde im März 2024 verarbeitet?</em> — "
                "ich zeige dir den Verlauf aus der History.<br><br>"
                "📖 <b>Dateiinhalt:</b> <em>Was steht in vertrag.pdf?</em> — "
                "ich lese dir den Inhalt direkt aus dem Archiv vor.<br><br>"
                "📈 <b>Grafiken:</b> <em>Zeig mir eine Grafik nach Dokumententyp</em> — "
                "ich erstelle dir ein Diagramm.<br><br>"
                "Einfach schreiben — ich verstehe normale Sätze genauso wie "
                "kurze Suchbegriffe."
            ),
        }

    # --- Statistik-Fragen ---
    if any(p in lower for p in [
        "wie viele", "wieviele", "wie viel", "wie oft", "anzahl", "zähle", "zaehle",
    ]):
        html = _stats_html(agent, lower)
        return {"icon": "analytics", "color": "#00e87d", "html": html}

    # --- Grafik / Chart ---
    if any(p in lower for p in [
        "als graph", "als grafik", "als diagramm", "als chart",
        "zeig grafik", "zeig diagramm", "zeig chart", "zeig einen graph",
        "visualisier", "zeig als bild",
    ]):
        return {"icon": "bar_chart", "color": "#00d4ff",
                "html": _chart_hint_html(lower), "chart": True,
                "chart_type": _detect_chart_type(lower)}

    # --- Dateiinhalt lesen ---
    if any(p in lower for p in [
        "was steht in", "was steht da", "inhalt von", "zeig den inhalt",
        "lese die datei", "öffne die datei", "zeig mir die datei", "was ist in der",
    ]):
        html = _read_doc_html(agent, val)
        return {"icon": "description", "color": "#00d4ff", "html": html}

    # --- Timeline / Datum ---
    date_hint = _extract_date_filter(lower)
    if date_hint or any(p in lower for p in [
        "timeline", "zeitverlauf", "zeitstrahl", "wann wurde", "wann war",
        "was passierte", "was wurde verarbeitet", "zeig verlauf",
    ]):
        html = _timeline_html(agent, lower, date_hint)
        return {"icon": "timeline", "color": "#ff9f0a", "html": html}

    # --- Dokument-Aktionen ---
    if any(p in lower for p in ["inbox scannen", "scan starten", "neue dateien prüfen"]):
        return {"icon": "search", "color": "#00d4ff",
                "html": "Wechsle in den <b>Archiv-Chat</b> um Dokumente zu scannen und zu sortieren. "
                        "Hier kannst du suchen und Fragen stellen."}

    # --- Hilfe ---
    if any(p in lower for p in ["hilfe", "help", "was kannst du", "kommandos", "befehle", "?"]):
        return {"icon": "help_outline", "color": "#a78bfa", "html": _help_html()}

    # --- Status / Uebersicht ---
    if any(p in lower for p in ["status", "übersicht", "uebersicht", "wie ist der stand"]):
        html = _stats_html(agent, "")
        return {"icon": "dashboard", "color": "#00e87d", "html": html}

    # Kein konversationeller Treffer → normaler Suchbegriff
    return None


# ---------------------------------------------------------------------------
# Konversations-HTML-Generatoren
# ---------------------------------------------------------------------------

def _stats_html(agent: DocSorterAgent, lower: str) -> str:
    try:
        from ...config import load_config, get_document_type_keywords, get_known_customers
        from ...logger import LogManager

        cfg = load_config()
        logs_dir = Path(cfg["paths"]["logs"])
        doc_type_counts: dict[str, int] = {}
        customer_counts: dict[str, int] = {}

        if logs_dir.exists():
            log_mgr = LogManager(logs_dir)
            for log in log_mgr.get_all_logs():
                dt = log.get("dokumentenart", "unbekannt")
                ku = log.get("kunde", "unbekannt")
                doc_type_counts[dt] = doc_type_counts.get(dt, 0) + 1
                customer_counts[ku] = customer_counts.get(ku, 0) + 1

        total = sum(doc_type_counts.values())

        # Spezifischer Typ gefragt?
        doc_kw = get_document_type_keywords(cfg)
        for dtype, keywords in doc_kw.items():
            if dtype.lower() in lower or any(k.lower() in lower for k in keywords):
                cnt = doc_type_counts.get(dtype, 0)
                return (f"Es gibt <b>{cnt}</b> archivierte Dokumente vom Typ "
                        f"<b>{dtype}</b>.")

        # Spezifischer Kunde?
        for c in get_known_customers(cfg):
            aliases = [c["name"]] + c.get("aliases", [])
            if any(a.lower() in lower for a in aliases):
                cnt = customer_counts.get(c["name"], 0)
                return (f"Von <b>{c['name']}</b> gibt es <b>{cnt}</b> "
                        f"archivierte Dokumente.")

        if not total:
            return ("Noch keine archivierten Dokumente vorhanden. "
                    "Sortiere Dateien im Archiv-Chat um Statistiken zu sehen.")

        inbox_count = 0
        try:
            inbox = Path(cfg["paths"]["inbox"])
            from ...config import get_file_types
            allowed = get_file_types(cfg)
            inbox_count = sum(1 for f in inbox.rglob("*")
                              if f.is_file() and f.suffix.lower() in allowed) \
                if inbox.exists() else 0
        except Exception:
            pass

        parts = [f"<b>Übersicht:</b><br>📥 Inbox: <b>{inbox_count}</b> Dateien<br>"
                 f"✅ Archiviert: <b>{total}</b> gesamt<br><br>"
                 f"<b>Nach Typ:</b>"]
        for dt, cnt in sorted(doc_type_counts.items(), key=lambda x: -x[1])[:6]:
            parts.append(f"• {dt}: <b>{cnt}</b>")
        return "<br>".join(parts)

    except Exception as e:
        return f"Statistiken konnten nicht geladen werden: {e}"


def _read_doc_html(agent: DocSorterAgent, text: str) -> str:
    lower = text.lower()
    quoted = _re.search(r'["\']([^"\']+)["\']', text)
    ext_match = _re.search(r'(\S+\.(?:pdf|docx|txt|png|jpg|tif|md))', text, _re.IGNORECASE)

    if quoted:
        keyword = quoted.group(1)
    elif ext_match:
        keyword = ext_match.group(1)
    else:
        stopwords = {
            "was", "steht", "in", "der", "die", "das", "von", "inhalt",
            "zeig", "mir", "datei", "öffne", "lese", "dem", "einem",
            "einer", "eine", "ein", "ist", "sind", "auch",
        }
        words = [w for w in lower.split() if w not in stopwords and len(w) > 2]
        keyword = " ".join(words[:3])

    if not keyword:
        return "Welche Datei meinst du? Z.B.: <i>'Was steht in rechnung_gasag.pdf?'</i>"

    try:
        from ...config import load_config, get_ocr_languages
        from ...reader import read_text

        cfg = load_config()
        search_dirs = [Path(cfg["paths"]["archive"]), Path(cfg["paths"]["inbox"])]
        kw = keyword.lower()
        found: list[Path] = []
        for d in search_dirs:
            if d.exists():
                for f in d.rglob("*"):
                    if f.is_file() and kw in f.name.lower():
                        found.append(f)

        if not found:
            return (f"Keine Datei mit '<b>{keyword}</b>' gefunden. "
                    f"Versuche einen anderen Dateinamen oder Suchbegriff.")

        f = found[0]
        raw = read_text(f, ocr_languages=get_ocr_languages(cfg),
                        ocr_dpi=cfg.get("ocr", {}).get("dpi", 200), max_pages=2)
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        preview = "\n".join(lines[:22])
        if len(preview) > 650:
            preview = preview[:650] + "…"
        more = f"<br><span style='font-size:0.72rem;color:var(--ds-text-2)'>… und {len(found)-1} weitere Treffer</span>" if len(found) > 1 else ""
        return (
            f"<b>{f.name}</b><br>"
            f"<span style='font-size:0.72rem;color:var(--ds-text-2)'>{f.parent}</span><br><br>"
            f"<pre style='font-size:0.78rem;white-space:pre-wrap;color:var(--ds-text);"
            f"max-height:300px;overflow:auto;background:rgba(0,0,0,0.2);"
            f"border-radius:8px;padding:10px'>{preview}</pre>{more}"
        )
    except Exception as e:
        return f"Fehler beim Lesen: {e}"


def _timeline_html(agent: DocSorterAgent, lower: str, date_hint: str | None) -> str:
    try:
        from ...config import load_config
        from ...logger import LogManager

        cfg = load_config()
        logs_dir = Path(cfg["paths"]["logs"])
        if not logs_dir.exists():
            return "Noch keine History vorhanden. Sortiere Dateien um den Verlauf zu sehen."

        log_mgr = LogManager(logs_dir)
        all_logs = log_mgr.get_all_logs()

        if date_hint:
            d = date_hint.lower().strip()
            filtered = [
                lg for lg in all_logs
                if d in lg.get("timestamp", "").lower()[:10]
                or d in lg.get("timestamp", "").lower()
            ]
            if not filtered:
                month_map = {
                    "januar": "01", "februar": "02", "märz": "03", "maerz": "03",
                    "april": "04", "mai": "05", "juni": "06", "juli": "07",
                    "august": "08", "september": "09", "oktober": "10",
                    "november": "11", "dezember": "12",
                }
                for month, num in month_map.items():
                    if month in d:
                        filtered = [lg for lg in all_logs if f"-{num}-" in lg.get("timestamp", "")]
                        break
        else:
            filtered = all_logs

        filtered = sorted(filtered, key=lambda x: x.get("timestamp", ""), reverse=True)[:15]

        if not filtered:
            label = f" für '<b>{date_hint}</b>'" if date_hint else ""
            return f"Keine History-Einträge{label} gefunden."

        label = f"<b>{len(filtered)} Einträge</b>" + (f" für '<b>{date_hint}</b>'" if date_hint else " (neueste zuerst)")
        rows = []
        for lg in filtered:
            ts = lg.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts)
                ts_str = dt.strftime("%d.%m. %H:%M")
            except Exception:
                ts_str = ts[:16]
            src = Path(lg.get("source", "")).name if lg.get("source") else "?"
            dtype = lg.get("dokumentenart", "?")
            kunde = lg.get("kunde", "?")
            rows.append(
                f"<div style='padding:5px 0;border-bottom:1px solid rgba(255,159,10,0.1);"
                f"font-size:0.8rem'>"
                f"<span style='color:#ff9f0a;font-size:0.7rem'>{ts_str}</span> "
                f"<b>{src}</b> → <span style='color:var(--ds-text-2)'>{dtype} / {kunde}</span></div>"
            )
        return f"{label}:<br>" + "".join(rows)

    except Exception as e:
        return f"Fehler beim Laden der Timeline: {e}"


def _detect_chart_type(lower: str) -> str:
    if any(w in lower for w in ["typ", "art", "dokumentenart"]):
        return "doctype_pie"
    if any(w in lower for w in ["kunde", "kunden"]):
        return "customer_bar"
    if any(w in lower for w in ["sicherheit", "confidence"]):
        return "confidence"
    return "timeline"


def _chart_hint_html(lower: str) -> str:
    chart_type = _detect_chart_type(lower)
    labels = {
        "timeline": "Dokumente pro Monat",
        "doctype_pie": "Nach Dokumententyp",
        "customer_bar": "Nach Kunde",
        "confidence": "Erkennungs-Sicherheit",
    }
    return f"Grafik wird geladen: <b>{labels.get(chart_type, chart_type)}</b>"


def _help_html() -> str:
    return (
        "<b>Was ich kann:</b><br><br>"
        "🔍 <b>Suchen:</b> Einfach einen Begriff eingeben — z.B. <i>Rechnung</i>, "
        "<i>GASAG</i>, <i>Netflix</i>, <i>Kosovo 2024</i><br><br>"
        "📊 <b>Statistiken:</b> <i>Wie viele Rechnungen gibt es?</i> · "
        "<i>Wie oft kommt GASAG vor?</i><br><br>"
        "📅 <b>Timeline:</b> <i>Was wurde im März 2024 verarbeitet?</i> · "
        "<i>Verlauf 2024</i><br><br>"
        "📖 <b>Inhalt lesen:</b> <i>Was steht in vertrag.pdf?</i><br><br>"
        "📈 <b>Grafiken:</b> <i>Zeig Grafik nach Dokumententyp</i><br><br>"
        "🗣️ <b>Chatten:</b> Hallo, Danke, Wie geht es dir? — einfach schreiben!"
    )


# ---------------------------------------------------------------------------
# File Search Backend
# ---------------------------------------------------------------------------

def _search_all(agent: DocSorterAgent, query: str) -> list[dict]:
    """Durchsucht alle Datenquellen nach query."""
    q = query.lower().strip()
    results: list[dict] = []

    year_match = _re.search(r'\b(20\d{2})\b', q)
    month_map = {
        "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4,
        "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
        "oktober": 10, "november": 11, "dezember": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
        "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dez": 12,
    }
    month_num = next((v for k, v in month_map.items() if k in q), None)
    date_filter = {"year": int(year_match.group(1)), "month": month_num} if year_match else None

    # --- Dokumente ---
    try:
        from ...config import load_config
        cfg = load_config()

        def _scan_folder(path_key: str, label: str, icon: str, color: str):
            raw = cfg.get("paths", {}).get(path_key, "")
            folder = Path(raw).expanduser() if raw else None
            if not folder or not folder.exists():
                return
            for f in folder.rglob("*"):
                if not f.is_file():
                    continue
                if date_filter:
                    try:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        if mtime.year != date_filter["year"]:
                            continue
                        if date_filter.get("month") and mtime.month != date_filter["month"]:
                            continue
                    except Exception:
                        pass
                    clean_q = _re.sub(r'\b20\d{2}\b', '', q)
                    for k in month_map:
                        clean_q = clean_q.replace(k, "")
                    clean_q = clean_q.strip()
                    if clean_q and clean_q not in f.name.lower():
                        continue
                else:
                    if q not in f.name.lower():
                        continue
                results.append({
                    "type": "doc", "label": label, "icon": icon, "color": color,
                    "name": f.name, "path": str(f),
                    "size": f"{f.stat().st_size / 1024:.1f} KB",
                })

        _scan_folder("inbox",   "Inbox",    "inbox",       "#00d4ff")
        _scan_folder("archive", "Archiv",   "archive",     "#00e87d")
        _scan_folder("review",  "Pruefung", "rate_review", "#ff9f0a")
    except Exception:
        pass

    # --- Todos ---
    try:
        from ...assistant_store import get_todos
        for todo in get_todos():
            text = todo.get("text", "")
            if q in text.lower() or q in " ".join(todo.get("tags", [])).lower():
                results.append({
                    "type": "todo", "label": "Todo", "icon": "check_box", "color": "#a78bfa",
                    "name": text,
                    "meta": f"Prioritaet: {todo.get('priority','normal')} · "
                            f"{'Erledigt' if todo.get('done') else 'Offen'}",
                })
    except Exception:
        pass

    # --- Ausgaben ---
    try:
        from ...assistant_store import get_expenses
        for exp in get_expenses():
            desc = exp.get("description", "")
            cat = exp.get("category", "")
            if q in desc.lower() or q in cat.lower():
                results.append({
                    "type": "expense", "label": "Ausgabe", "icon": "euro", "color": "#ff9f0a",
                    "name": desc,
                    "meta": f"{exp.get('amount','?')} € · {exp.get('date','?')} · {cat}",
                })
    except Exception:
        pass

    # --- Abonnements ---
    try:
        from ...assistant_store import get_subscriptions
        for sub in get_subscriptions():
            name = sub.get("name", "")
            if q in name.lower() or q in sub.get("category", "").lower():
                results.append({
                    "type": "subscription", "label": "Abo", "icon": "repeat", "color": "#00e87d",
                    "name": name,
                    "meta": f"{sub.get('amount','?')} €/{sub.get('interval','Monat')} · "
                            f"{sub.get('category','')}",
                })
    except Exception:
        pass

    # --- E-Mail-Regeln ---
    try:
        from ...assistant_store import get_email_rules
        for rule in get_email_rules():
            sender = rule.get("sender_pattern", "")
            subject = rule.get("subject_pattern", "")
            folder = rule.get("target_folder", "")
            if q in sender.lower() or q in subject.lower() or q in folder.lower():
                results.append({
                    "type": "email_rule", "label": "E-Mail-Regel", "icon": "mail",
                    "color": "#00d4ff",
                    "name": f"Von: {sender or '–'} / Betreff: {subject or '–'}",
                    "meta": f"→ {folder}",
                })
    except Exception:
        pass

    return results


# ---------------------------------------------------------------------------
# Message rendering
# ---------------------------------------------------------------------------

_MSG_ID = 0


def _next_id() -> str:
    global _MSG_ID
    _MSG_ID += 1
    return str(_MSG_ID)


def _ts() -> str:
    return datetime.now().strftime("%H:%M")


def _scroll_down() -> None:
    """Scrollt den Chat ans Ende — zielt gezielt auf den Chat-Container."""
    ui.run_javascript(
        "setTimeout(()=>{"
        # Zuerst: Chat-Container per ID (ds-chat-scroll oder ds-unified-scroll)
        "let c=null;"
        "const chatArea=document.getElementById('ds-chat-scroll')||document.getElementById('ds-unified-scroll');"
        "if(chatArea){c=chatArea.querySelector('.q-scrollarea__container');}"
        # Fallback: letzten scroll-container nehmen (wahrscheinlich der Chat)
        "if(!c){const all=document.querySelectorAll('.q-scrollarea__container');"
        "if(all.length)c=all[all.length-1];}"
        "if(c)c.scrollTop=c.scrollHeight;"
        "},50)"
    )


def _render_user_msg(container, text: str) -> None:
    with container:
        with ui.row().classes("w-full justify-end"):
            with ui.column().style(
                "max-width:75%;background:linear-gradient(135deg,#00d4ff,#0098cc);"
                "color:#05091a;font-weight:600;border-radius:14px 14px 4px 14px;"
                "padding:12px 16px;box-shadow:0 0 18px rgba(0,212,255,0.3)"
            ):
                ui.html(f'<span style="font-size:0.875rem">{text}</span>', sanitize=False)
                ui.label(_ts()).style("font-size:0.6rem;opacity:0.6;align-self:flex-end;margin-top:4px")


def _render_agent_msg(container, html: str, icon: str = "smart_toy",
                      color: str = "#00d4ff") -> None:
    with container:
        with ui.column().style(
            "max-width:92%;background:rgba(10,22,40,0.85);"
            "border:1px solid rgba(0,212,255,0.15);border-radius:14px 14px 14px 4px;"
            "padding:14px 18px;backdrop-filter:blur(8px)"
        ):
            with ui.row().classes("items-center gap-2 mb-2"):
                ui.icon(icon).style(f"font-size:1rem;color:{color}")
                ui.label(_ts()).style("font-size:0.6rem;color:var(--ds-text-2)")
            ui.html(
                f'<div style="font-size:0.875rem;line-height:1.65;color:var(--ds-text)">'
                f'{html}</div>',
                sanitize=False,
            )


def _render_chart_msg(container, chart_type: str) -> None:
    try:
        from ..chart_data import get_chart_config
        config = get_chart_config(chart_type)
        if not config:
            _render_agent_msg(container,
                              "Noch keine Daten für Charts. Sortiere Dateien um Statistiken zu sehen.",
                              icon="bar_chart")
            return
        with container:
            with ui.column().style(
                "width:100%;background:rgba(10,22,40,0.85);"
                "border:1px solid rgba(0,212,255,0.15);border-radius:14px;"
                "padding:14px 18px;backdrop-filter:blur(8px)"
            ):
                with ui.row().classes("items-center gap-2 mb-2"):
                    ui.icon("bar_chart").style("font-size:1rem;color:#00d4ff")
                    ui.label(_ts()).style("font-size:0.6rem;color:var(--ds-text-2)")
                ui.highchart(config).classes("w-full").style("min-height:280px")
    except Exception as e:
        _render_agent_msg(container, f"Chart konnte nicht geladen werden: {e}", icon="bar_chart")


def _render_results(container, results: list[dict], query: str) -> None:
    with container:
        with ui.column().style(
            "width:100%;background:rgba(10,22,40,0.85);"
            "border:1px solid rgba(0,212,255,0.15);border-radius:14px 14px 14px 4px;"
            "padding:14px 18px;backdrop-filter:blur(8px);gap:0"
        ):
            with ui.row().classes("items-center gap-2 mb-3"):
                ui.icon("search").style("font-size:1rem;color:#00d4ff")
                ui.html(
                    f'<span style="font-size:0.875rem;color:var(--ds-text)">'
                    f'<b>{len(results)}</b> Treffer für '
                    f'<b style="color:#00d4ff">„{query}"</b></span>',
                    sanitize=False,
                )
                ui.label(_ts()).style("font-size:0.6rem;color:var(--ds-text-2);margin-left:auto")

            for r in results[:30]:
                with ui.row().classes("items-center gap-3").style(
                    "padding:8px 0;border-bottom:1px solid rgba(0,212,255,0.07)"
                ):
                    with ui.element("div").style(
                        f"width:28px;height:28px;border-radius:6px;flex-shrink:0;"
                        f"background:{r['color']}18;display:flex;align-items:center;"
                        f"justify-content:center;border:1px solid {r['color']}30"
                    ):
                        ui.icon(r["icon"]).style(f"font-size:0.9rem;color:{r['color']}")
                    with ui.column().classes("gap-0 flex-1 min-w-0"):
                        ui.label(r["name"]).style(
                            "font-size:0.8rem;font-weight:600;color:var(--ds-text);"
                            "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                        )
                        meta = r.get("meta") or r.get("size") or ""
                        if meta:
                            ui.label(meta).style("font-size:0.65rem;color:var(--ds-text-2)")
                    ui.label(r["label"]).style(
                        f"font-size:0.6rem;font-weight:700;padding:2px 8px;border-radius:4px;"
                        f"background:{r['color']}15;color:{r['color']};"
                        f"border:1px solid {r['color']}30;white-space:nowrap;flex-shrink:0"
                    )

            if len(results) > 30:
                ui.label(f"… und {len(results)-30} weitere Treffer").style(
                    "font-size:0.7rem;color:var(--ds-text-2);font-style:italic;padding:8px 0 0"
                )


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(agent: DocSorterAgent) -> None:
    """Universal Search Chat aufbauen."""

    with ui.column().classes("ds-chat-container").style("padding:0;margin:0"):

        # Header
        with ui.element("div").style(
            "padding:16px 24px 12px;border-bottom:1px solid rgba(0,212,255,0.1);"
            "flex-shrink:0"
        ):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").style(
                    "width:36px;height:36px;border-radius:10px;"
                    "background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);"
                    "display:flex;align-items:center;justify-content:center"
                ):
                    ui.icon("manage_search").style("font-size:1.2rem;color:#00d4ff")
                with ui.column().classes("gap-0"):
                    ui.label("Suche & Chat").style(
                        "font-size:1rem;font-weight:700;color:var(--ds-text);line-height:1.2"
                    )
                    ui.label("Dokumente · Todos · Ausgaben · Abos · Statistiken · Konversation").style(
                        "font-size:0.7rem;color:var(--ds-text-2)"
                    )

        # Messages area
        with ui.element("div").style("flex:1 1 0;min-height:0;overflow:hidden;width:100%"):
            with ui.scroll_area().style("height:100%;width:100%"):
                messages_container = ui.column().classes("gap-4").style(
                    "width:100%;max-width:860px;margin:0 auto;padding:20px 24px"
                )

        # Initial welcome
        _render_agent_msg(
            messages_container,
            (
                "Hallo! 👋 Ich bin dein Assistent für Suche und Konversation.<br><br>"
                "🔍 <b>Suchen:</b> Einfach einen Begriff eingeben — <i>Rechnung</i>, <i>GASAG</i>, <i>2024</i><br>"
                "📊 <b>Statistiken:</b> <i>Wie viele Rechnungen gibt es?</i><br>"
                "📅 <b>Timeline:</b> <i>Was wurde im März 2024 verarbeitet?</i><br>"
                "📖 <b>Inhalt:</b> <i>Was steht in vertrag.pdf?</i><br>"
                "🗣️ <b>Chatten:</b> Hallo, Danke, Fragen — einfach schreiben!"
            ),
            icon="manage_search",
            color="#00d4ff",
        )

        # Suggestion chips
        import datetime as _dt
        _current_year = str(_dt.date.today().year)
        with ui.row().classes("ds-chip-row"):
            for label, q in [
                ("Rechnungen", "rechnung"),
                ("Verträge", "vertrag"),
                ("Todos", "todo"),
                ("Statistiken", "wie viele"),
                ("Timeline", "timeline"),
                ("2024", "2024"),
                ("dieses Jahr", _current_year),
                ("Hilfe", "hilfe"),
            ]:
                def make_chip(query=q, lbl=label):
                    async def handler():
                        _render_user_msg(messages_container, lbl)
                        convo = await run.io_bound(_chat_response, agent, query)
                        if convo:
                            if convo.get("chart"):
                                _render_chart_msg(messages_container, convo["chart_type"])
                            else:
                                _render_agent_msg(messages_container, convo["html"],
                                                  icon=convo.get("icon", "smart_toy"),
                                                  color=convo.get("color", "#00d4ff"))
                        else:
                            results = await run.io_bound(_search_all, agent, query)
                            if results:
                                _render_results(messages_container, results, query)
                            else:
                                _render_agent_msg(messages_container,
                                                  f'Keine Treffer für <b>„{query}"</b>.',
                                                  icon="search_off",
                                                  color="var(--ds-text-2)")
                        _scroll_down()
                    return handler
                ui.button(label, on_click=make_chip(), icon="search").classes(
                    "ds-suggestion-chip"
                ).props("dense unelevated no-caps")

        # Input area
        with ui.element("div").classes("ds-chat-input-area"):
            with ui.row().classes("items-center gap-3").style(
                "max-width:860px;margin:0 auto;width:100%"
            ):
                text_input = ui.input(
                    placeholder="Suchen oder fragen — z.B. 'Wie viele Rechnungen?' oder 'Hallo'..."
                ).classes("flex-1").props("outlined dense rounded").style("font-size:0.875rem")

                async def do_search():
                    val = text_input.value.strip()
                    if not val:
                        return
                    text_input.value = ""
                    lower = val.lower().strip()
                    _render_user_msg(messages_container, val)

                    # Konversationellen Intent prüfen
                    convo = await run.io_bound(_chat_response, agent, val)

                    if convo:
                        if convo.get("chart"):
                            _render_chart_msg(messages_container, convo["chart_type"])
                        else:
                            _render_agent_msg(
                                messages_container,
                                convo["html"],
                                icon=convo.get("icon", "smart_toy"),
                                color=convo.get("color", "#00d4ff"),
                            )
                    else:
                        # Normale Suche
                        results = await run.io_bound(_search_all, agent, val)
                        if results:
                            _render_results(messages_container, results, val)
                        else:
                            _render_agent_msg(
                                messages_container,
                                (
                                    f'Keine Treffer für <b>„{val}"</b> gefunden.<br>'
                                    f'<span style="color:var(--ds-text-2);font-size:0.8rem">'
                                    f'Tipp: Anderer Begriff oder Frage stellen — z.B. '
                                    f'<i>Wie viele {val}s gibt es?</i></span>'
                                ),
                                icon="search_off",
                                color="var(--ds-text-2)",
                            )
                    _scroll_down()

                text_input.on("keydown.enter", do_search)

                ui.button(icon="send", on_click=do_search).props("round dense").classes(
                    "ds-btn-primary"
                ).style("width:40px;height:40px;min-width:40px")
