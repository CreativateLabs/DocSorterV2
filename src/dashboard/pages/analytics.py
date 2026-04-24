"""Analyse & Statistiken: Charts, Duplikate, Volltextsuche.

UI Design Overhaul: Crisp Cards, bessere Stat-Summary, konsistente Farben.
- "Confidence" -> "Erkennungs-Sicherheit"
- "Avg Confidence" -> "Durchschnittliche Sicherheit"
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from nicegui import ui

from ...config import load_config
from ...logger import LogManager
from ..theme import empty_state, page_header, stat_card, section_title


def _load_all_data(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    logs_dir = Path(cfg["paths"]["logs"])
    if not logs_dir.exists():
        return []
    log_mgr = LogManager(logs_dir)
    return log_mgr.get_all_logs()


def _build_timeline_chart(logs: list[dict]) -> None:
    section_title("Dokumente pro Monat", "timeline")

    if not logs:
        empty_state("bar_chart", "Keine Zeitdaten vorhanden")
        return

    monthly: Counter = Counter()
    for log in logs:
        ts = log.get("timestamp", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                key = dt.strftime("%Y-%m")
                monthly[key] += 1
            except (ValueError, TypeError):
                pass

    if not monthly:
        empty_state("bar_chart", "Keine Zeitdaten")
        return

    months = sorted(monthly.keys())
    counts = [monthly[m] for m in months]
    display_months = []
    for m in months:
        try:
            dt = datetime.strptime(m, "%Y-%m")
            display_months.append(dt.strftime("%b %Y"))
        except ValueError:
            display_months.append(m)

    ui.highchart({
        "title": {"text": ""},
        "chart": {"type": "column", "height": 280, "backgroundColor": "transparent"},
        "xAxis": {"categories": display_months},
        "yAxis": {"title": {"text": "Anzahl"}, "allowDecimals": False},
        "series": [{"name": "Dokumente", "data": counts, "color": "#3B82F6"}],
        "credits": {"enabled": False},
        "legend": {"enabled": False},
    }).classes("w-full")


def _build_doctype_chart(logs: list[dict]) -> None:
    section_title("Nach Dokumentenart", "pie_chart")

    if not logs:
        empty_state("pie_chart", "Keine Daten")
        return

    types: Counter = Counter()
    for log in logs:
        cls = log.get("classification", {})
        art = cls.get("dokumentenart", "unbekannt")
        types[art] += 1

    if not types:
        return

    data = [{"name": k, "y": v} for k, v in types.most_common(10)]

    ui.highchart({
        "title": {"text": ""},
        "chart": {"type": "pie", "height": 280, "backgroundColor": "transparent"},
        "series": [{"name": "Dokumente", "data": data}],
        "plotOptions": {"pie": {"dataLabels": {"enabled": True, "format": "{point.name}: {point.y}"}}},
        "credits": {"enabled": False},
    }).classes("w-full")


def _build_customer_chart(logs: list[dict]) -> None:
    section_title("Top Kunden", "leaderboard")

    if not logs:
        empty_state("bar_chart", "Keine Daten")
        return

    customers: Counter = Counter()
    for log in logs:
        cls = log.get("classification", {})
        kunde = cls.get("kunde", "unbekannt")
        customers[kunde] += 1

    if not customers:
        return

    top = customers.most_common(10)
    names = [k for k, v in top]
    counts = [v for k, v in top]

    ui.highchart({
        "title": {"text": ""},
        "chart": {"type": "bar", "height": 280, "backgroundColor": "transparent"},
        "xAxis": {"categories": names},
        "yAxis": {"title": {"text": "Dokumente"}, "allowDecimals": False},
        "series": [{"name": "Dokumente", "data": counts, "color": "#10B981"}],
        "credits": {"enabled": False},
        "legend": {"enabled": False},
    }).classes("w-full")


def _build_confidence_chart(logs: list[dict]) -> None:
    section_title("Erkennungs-Sicherheit", "speed")

    if not logs:
        empty_state("speed", "Keine Daten")
        return

    buckets = {"0-20%": 0, "20-40%": 0, "40-60%": 0, "60-80%": 0, "80-100%": 0}
    for log in logs:
        conf = log.get("classification", {}).get("confidence", 0)
        if conf < 0.2:
            buckets["0-20%"] += 1
        elif conf < 0.4:
            buckets["20-40%"] += 1
        elif conf < 0.6:
            buckets["40-60%"] += 1
        elif conf < 0.8:
            buckets["60-80%"] += 1
        else:
            buckets["80-100%"] += 1

    colors = ["#EF4444", "#F97316", "#EAB308", "#84CC16", "#22C55E"]

    ui.highchart({
        "title": {"text": ""},
        "chart": {"type": "column", "height": 240, "backgroundColor": "transparent"},
        "xAxis": {"categories": list(buckets.keys())},
        "yAxis": {"title": {"text": "Anzahl"}, "allowDecimals": False},
        "series": [{"name": "Dokumente", "data": [
            {"y": v, "color": colors[i]} for i, v in enumerate(buckets.values())
        ]}],
        "credits": {"enabled": False},
        "legend": {"enabled": False},
    }).classes("w-full")


def _build_duplicate_detector(logs: list[dict]) -> None:
    section_title("Duplikat-Erkennung", "content_copy")

    if not logs:
        empty_state("content_copy", "Keine Daten")
        return

    hash_files: defaultdict[str, list[dict]] = defaultdict(list)
    for log in logs:
        sha = log.get("sha256", "")
        if sha:
            hash_files[sha].append({
                "source": Path(log.get("source", "")).name,
                "dest": Path(log.get("destination", "")).name,
                "timestamp": log.get("timestamp", "")[:19].replace("T", " "),
            })

    duplicates = {k: v for k, v in hash_files.items() if len(v) > 1}

    if not duplicates:
        from ..theme import status_badge
        with ui.row().classes("items-center gap-2"):
            status_badge("Keine Duplikate gefunden", "success")
        return

    ui.label(f"{len(duplicates)} Duplikat-Gruppen gefunden").classes("text-amber-600 mb-2 font-medium")

    for sha, files in list(duplicates.items())[:20]:
        with ui.expansion(
            f"Hash: ...{sha[-8:]}  ({len(files)} Dateien)", icon="content_copy",
        ).classes("w-full ds-expansion"):
            for f in files:
                with ui.row().classes("gap-3 py-1"):
                    ui.label(f["source"]).classes("font-mono text-sm")
                    ui.label("->").classes("text-gray-400")
                    ui.label(f["dest"]).classes("font-mono text-sm")
                    ui.label(f["timestamp"]).classes("text-xs text-gray-400")


def _build_fulltext_search(logs: list[dict]) -> None:
    section_title("Volltextsuche", "search")
    ui.label(
        "Durchsuche alle verarbeiteten Dokumente nach Inhalten."
    ).classes("text-sm text-gray-500 mb-3")

    search_input = ui.input(
        label="Suchbegriff eingeben...",
        placeholder="z.B. GASAG, Rechnung, Vertrag...",
    ).classes("w-full ds-input").props("clearable")

    result_container = ui.column().classes("w-full mt-3")

    def _search() -> None:
        query = (search_input.value or "").strip().lower()
        result_container.clear()

        if not query or len(query) < 2:
            with result_container:
                ui.label("Mindestens 2 Zeichen eingeben.").classes("text-gray-400 italic text-sm")
            return

        matches = []
        for log in logs:
            text_preview = log.get("text_preview", "").lower()
            cls = log.get("classification", {})
            searchable = f"{text_preview} {cls.get('dokumentenart', '')} {cls.get('kunde', '')} {cls.get('land', '')}".lower()
            if query in searchable:
                matches.append(log)

        with result_container:
            if not matches:
                empty_state("search_off", f"Keine Treffer fuer '{search_input.value}'")
                return

            ui.label(f"{len(matches)} Treffer gefunden").classes("text-sm text-gray-500 mb-2")

            rows = []
            for log in matches[:50]:
                cls = log.get("classification", {})
                ts = log.get("timestamp", "")[:19].replace("T", " ")
                source = Path(log.get("source", "")).name
                preview = log.get("text_preview", "")[:200]

                lower_preview = preview.lower()
                idx = lower_preview.find(query)
                if idx >= 0:
                    start = max(0, idx - 40)
                    end = min(len(preview), idx + len(query) + 40)
                    context = ("..." if start > 0 else "") + preview[start:end] + ("..." if end < len(preview) else "")
                else:
                    context = preview[:100] + "..."

                rows.append({
                    "zeit": ts,
                    "datei": source,
                    "art": cls.get("dokumentenart", "?"),
                    "kunde": cls.get("kunde", "?"),
                    "kontext": context,
                })

            columns = [
                {"name": "zeit", "label": "Zeit", "field": "zeit", "sortable": True, "align": "left"},
                {"name": "datei", "label": "Datei", "field": "datei", "sortable": True, "align": "left"},
                {"name": "art", "label": "Typ", "field": "art", "sortable": True},
                {"name": "kunde", "label": "Kunde", "field": "kunde", "sortable": True},
                {"name": "kontext", "label": "Kontext", "field": "kontext", "align": "left"},
            ]

            ui.table(
                columns=columns, rows=rows, row_key="zeit",
                pagination={"rowsPerPage": 15},
            ).classes("w-full ds-table")

    search_input.on("keyup.enter", lambda _: _search())
    ui.button("Suchen", on_click=_search, icon="search").classes("ds-btn-primary mt-2")


def build() -> None:
    """Analyse-Seite aufbauen."""
    cfg = load_config()
    logs = _load_all_data(cfg)

    page_header(
        "Analyse & Statistiken",
        f"{len(logs)} Verarbeitungen analysiert.",
    )

    if not logs:
        empty_state(
            "analytics",
            "Noch keine Daten vorhanden",
            "Verarbeite einige Dokumente ueber Terminal > Jetzt sortieren und komme dann hierher zurueck.",
        )
        return

    # Summary Stats
    total = len(logs)
    unsicher = sum(1 for l in logs if l.get("classification", {}).get("unsicher", False))
    sicher = total - unsicher
    avg_conf = sum(l.get("classification", {}).get("confidence", 0) for l in logs) / total if total else 0

    with ui.row().classes("w-full gap-4 flex-wrap mb-4"):
        stat_card("Gesamt", total, "analytics", "blue")
        stat_card("Sicher", sicher, "check_circle", "green")
        stat_card("Unsicher", unsicher, "warning", "amber")
        stat_card("Durchschnittl. Sicherheit", f"{avg_conf:.0%}", "speed", "purple")

    with ui.tabs().classes("w-full ds-tabs") as tabs:
        tab_charts = ui.tab("Charts", icon="bar_chart")
        tab_dupes = ui.tab("Duplikate", icon="content_copy")
        tab_search = ui.tab("Suche", icon="search")

    with ui.tab_panels(tabs, value=tab_charts).classes("w-full"):
        with ui.tab_panel(tab_charts):
            with ui.grid(columns=2).classes("w-full gap-4"):
                with ui.card().classes("ds-card"):
                    _build_timeline_chart(logs)
                with ui.card().classes("ds-card"):
                    _build_doctype_chart(logs)
                with ui.card().classes("ds-card"):
                    _build_customer_chart(logs)
                with ui.card().classes("ds-card"):
                    _build_confidence_chart(logs)

        with ui.tab_panel(tab_dupes):
            _build_duplicate_detector(logs)

        with ui.tab_panel(tab_search):
            _build_fulltext_search(logs)
