"""Historie: Alle bisherigen Verarbeitungen anzeigen und durchsuchen.

UI Design Overhaul: Crisp Tabelle, bessere Filter, Status-Badges.
- "Confidence" -> "Sicherheit"
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from nicegui import ui

from ...config import load_config
from ...logger import LogManager
from ..theme import empty_state, page_header, status_badge


def _load_history(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    logs_dir = Path(cfg["paths"]["logs"])
    log_mgr = LogManager(logs_dir)
    return log_mgr.get_all_logs()


def build() -> None:
    """Historie-Seite aufbauen."""
    cfg = load_config()
    all_logs = _load_history(cfg)

    page_header(
        "Historie",
        f"{len(all_logs)} Verarbeitungen insgesamt.",
    )

    if not all_logs:
        empty_state(
            "history",
            "Noch keine Verarbeitungen",
            "Verarbeite einige Dokumente ueber Terminal > Jetzt sortieren.",
        )
        return

    # Filter
    with ui.row().classes("gap-3 mb-4 items-end"):
        filter_input = ui.input(
            label="Suche (Dateiname, Kunde, Typ...)",
            placeholder="z.B. GASAG",
        ).classes("w-64 ds-input")
        filter_status = ui.select(
            label="Status",
            options=["Alle", "Sicher", "Unsicher"],
            value="Alle",
        ).classes("w-32 ds-input")

    def _get_rows() -> list[dict]:
        rows = []
        search = (filter_input.value or "").lower()
        status_filter = filter_status.value

        for log in all_logs:
            cls = log.get("classification", {})
            source = Path(log.get("source", "")).name
            dest = Path(log.get("destination", "")).name
            ts = log.get("timestamp", "")[:19].replace("T", " ")
            unsicher = cls.get("unsicher", False)
            confidence = cls.get("confidence", 0)

            if status_filter == "Sicher" and unsicher:
                continue
            if status_filter == "Unsicher" and not unsicher:
                continue

            row_text = f"{source} {dest} {cls.get('dokumentenart', '')} {cls.get('kunde', '')} {cls.get('land', '')}".lower()
            if search and search not in row_text:
                continue

            rows.append({
                "zeit": ts,
                "quelle": source,
                "art": cls.get("dokumentenart", "?"),
                "kunde": cls.get("kunde", "?"),
                "land": cls.get("land", "?"),
                "sicherheit": f"{confidence:.0%}" if confidence else "?",
                "status": "Unsicher" if unsicher else "OK",
            })
        return rows

    columns = [
        {"name": "zeit", "label": "Zeitpunkt", "field": "zeit", "sortable": True, "align": "left"},
        {"name": "quelle", "label": "Datei", "field": "quelle", "sortable": True, "align": "left"},
        {"name": "art", "label": "Typ", "field": "art", "sortable": True},
        {"name": "kunde", "label": "Kunde", "field": "kunde", "sortable": True},
        {"name": "land", "label": "Land", "field": "land", "sortable": True},
        {"name": "sicherheit", "label": "Sicherheit", "field": "sicherheit", "sortable": True},
        {"name": "status", "label": "Status", "field": "status", "sortable": True},
    ]

    table = ui.table(
        columns=columns, rows=_get_rows(), row_key="zeit",
        pagination={"rowsPerPage": 25},
    ).classes("w-full ds-table")

    def _update_table() -> None:
        table.rows = _get_rows()
        table.update()

    filter_input.on("keyup", lambda _: _update_table())
    filter_status.on("update:model-value", lambda _: _update_table())

    def _export_csv() -> None:
        rows = _get_rows()
        if not rows:
            ui.notify("Keine Daten zum Exportieren", type="warning")
            return
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        ui.download(output.getvalue().encode("utf-8"), "docsorter_historie.csv")
        ui.notify(f"{len(rows)} Eintraege exportiert", type="positive")

    with ui.row().classes("gap-3 mt-4"):
        ui.button("Aktualisieren", on_click=_update_table, icon="refresh").classes("ds-btn-secondary")
        ui.button("CSV exportieren", on_click=_export_csv, icon="download").classes("ds-btn-ghost")
