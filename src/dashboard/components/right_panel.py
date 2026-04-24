"""Right Panel: Artifacts, Dateien und History in Tabs.

Zeigt kontextuelle Informationen neben dem Chat:
- Artifacts: Generierte Charts, Tabellen, Previews
- Dateien: Kompakter Dateibaum (Inbox/Archive/Review)
- History: Letzte Aktionen chronologisch
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from nicegui import ui

from ..agent import DocSorterAgent


# ---------------------------------------------------------------------------
# Artifacts Tab
# ---------------------------------------------------------------------------

def _build_artifacts_list(agent: DocSorterAgent, container=None) -> None:
    """Artifact-Karten aus dem Agent anzeigen."""
    artifacts = agent.get_artifacts()

    if not artifacts:
        with ui.column().classes("w-full items-center").style("padding:40px 16px"):
            ui.icon("dashboard").style("font-size:2.5rem;color:#D1D5DB")
            ui.label("Noch keine Artifacts").style(
                "font-size:0.85rem;font-weight:600;color:#9CA3AF;margin-top:12px"
            )
            ui.label("Charts, Tabellen und Previews erscheinen hier,").style(
                "font-size:0.7rem;color:#D1D5DB;text-align:center"
            )
            ui.label("sobald du Aktionen ausfuehrst.").style(
                "font-size:0.7rem;color:#D1D5DB;text-align:center"
            )
        return

    for artifact in reversed(artifacts):  # Neueste zuerst
        _type_icons = {
            "chart": ("bar_chart", "#3B82F6"),
            "table": ("table_chart", "#8B5CF6"),
            "file_list": ("folder", "#F59E0B"),
            "history": ("history", "#6B7280"),
        }
        icon, color = _type_icons.get(artifact["type"], ("info", "#6B7280"))

        with ui.card().classes("ds-artifact-card w-full"):
            with ui.row().classes("items-center gap-2 w-full"):
                ui.icon(icon).style(f"font-size:1rem;color:{color}")
                with ui.column().classes("gap-0 flex-1 min-w-0"):
                    ui.label(artifact["title"]).style(
                        "font-size:0.75rem;font-weight:600;overflow:hidden;"
                        "text-overflow:ellipsis;white-space:nowrap"
                    )
                    ui.label(artifact["timestamp"]).style(
                        "font-size:0.6rem;color:#9CA3AF"
                    )


# ---------------------------------------------------------------------------
# Dateien Tab
# ---------------------------------------------------------------------------

def _build_file_tree(agent: DocSorterAgent) -> None:
    """Kompakter Dateibaum: Inbox/Archive/Review."""
    try:
        from ...config import load_config, get_file_types

        cfg = load_config()
        inbox = Path(cfg["paths"]["inbox"])
        archive = Path(cfg["paths"]["archive"])
        review = Path(cfg["paths"].get("review", str(archive / "_review")))
        allowed = get_file_types(cfg)

        # Inbox-Dateien
        _folder_section("Inbox", "inbox", "#3B82F6", inbox, allowed)
        # Review-Dateien
        _folder_section("Pruefung", "rate_review", "#F59E0B", review, None)
        # Archive (nur Ordner-Struktur)
        _folder_section("Archiv", "archive", "#22C55E", archive, None, max_depth=1)

    except Exception as e:
        with ui.column().classes("w-full items-center p-4"):
            ui.label(f"Fehler: {e}").style("font-size:0.7rem;color:#EF4444")


def _folder_section(
    label: str,
    icon: str,
    color: str,
    path: Path,
    allowed: set[str] | None,
    max_depth: int = 2,
) -> None:
    """Eine Ordner-Sektion im Dateibaum."""
    if not path.exists():
        return

    # Dateien zaehlen
    if allowed:
        count = sum(1 for f in path.rglob("*") if f.is_file() and f.suffix.lower() in allowed)
    else:
        count = sum(1 for f in path.rglob("*") if f.is_file())

    with ui.column().classes("w-full").style("padding:8px 12px"):
        with ui.row().classes("items-center gap-2 w-full"):
            ui.icon(icon).style(f"font-size:0.9rem;color:{color}")
            ui.label(label).style("font-size:0.75rem;font-weight:600;flex:1")
            ui.label(str(count)).style(
                "font-size:0.65rem;font-weight:600;padding:1px 8px;"
                "border-radius:99px;background:#F3F4F6;color:#6B7280"
            )

        # Dateien auflisten (max 10)
        files = []
        for f in sorted(path.rglob("*"))[:50]:
            if not f.is_file():
                continue
            if allowed and f.suffix.lower() not in allowed:
                continue
            files.append(f)

        for f in files[:10]:
            rel = f.relative_to(path) if f.is_relative_to(path) else f
            with ui.row().classes("items-center gap-2").style(
                "padding:2px 0 2px 24px;cursor:pointer"
            ):
                ext = f.suffix.lower()
                file_icon = "picture_as_pdf" if ext == ".pdf" else "description"
                ui.icon(file_icon).style("font-size:0.75rem;color:#9CA3AF")
                ui.label(str(rel)).style(
                    "font-size:0.65rem;color:#6B7280;overflow:hidden;"
                    "text-overflow:ellipsis;white-space:nowrap"
                )

        if len(files) > 10:
            ui.label(f"... und {len(files) - 10} weitere").style(
                "font-size:0.6rem;color:#9CA3AF;padding-left:24px;font-style:italic"
            )


# ---------------------------------------------------------------------------
# History Tab
# ---------------------------------------------------------------------------

def _build_history_list(agent: DocSorterAgent) -> None:
    """Letzte Aktionen chronologisch."""
    try:
        from ...config import load_config
        from ...logger import LogManager

        cfg = load_config()
        logs_dir = Path(cfg["paths"]["logs"])

        if not logs_dir.exists():
            with ui.column().classes("w-full items-center").style("padding:40px 16px"):
                ui.icon("history").style("font-size:2.5rem;color:#D1D5DB")
                ui.label("Noch keine History").style(
                    "font-size:0.85rem;font-weight:600;color:#9CA3AF;margin-top:12px"
                )
                ui.label("Verarbeitete Dateien werden hier angezeigt.").style(
                    "font-size:0.7rem;color:#D1D5DB;text-align:center"
                )
            return

        log_mgr = LogManager(logs_dir)
        all_logs = log_mgr.get_all_logs()
        all_logs = sorted(all_logs, key=lambda x: x.get("timestamp", ""), reverse=True)[:20]

        if not all_logs:
            with ui.column().classes("w-full items-center").style("padding:40px 16px"):
                ui.icon("history").style("font-size:2.5rem;color:#D1D5DB")
                ui.label("Noch keine Eintraege").style(
                    "font-size:0.85rem;font-weight:600;color:#9CA3AF;margin-top:12px"
                )
                ui.label("Scanne die Inbox, um Dateien zu verarbeiten.").style(
                    "font-size:0.7rem;color:#D1D5DB;text-align:center"
                )
            return

        for log in all_logs:
            ts = log.get("timestamp", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    time_str = dt.strftime("%d.%m. %H:%M")
                except Exception:
                    time_str = ts[:16]
            else:
                time_str = ""

            source_name = Path(log.get("source", "")).name if log.get("source") else "?"
            doc_type = log.get("classification", {}).get("dokumentenart", "?")
            kunde = log.get("classification", {}).get("kunde", "?")

            with ui.row().classes("items-start gap-2 w-full").style(
                "padding:6px 12px;border-bottom:1px solid #F3F4F6"
            ):
                ui.icon("check_circle").style("font-size:0.8rem;color:#22C55E;margin-top:2px")
                with ui.column().classes("gap-0 flex-1 min-w-0"):
                    ui.label(source_name).style(
                        "font-size:0.7rem;font-weight:600;overflow:hidden;"
                        "text-overflow:ellipsis;white-space:nowrap"
                    )
                    ui.label(f"{doc_type} / {kunde}").style(
                        "font-size:0.6rem;color:#6B7280"
                    )
                ui.label(time_str).style("font-size:0.6rem;color:#9CA3AF;white-space:nowrap")

    except Exception as e:
        with ui.column().classes("w-full items-center p-4"):
            ui.label(f"Fehler: {e}").style("font-size:0.7rem;color:#EF4444")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_right_panel(agent: DocSorterAgent) -> ui.column:
    """Right Panel mit Tabs aufbauen.

    Returns ui.column (nicht ui.right_drawer) damit es im 3-Panel Layout
    als normales Element platziert werden kann.
    """
    panel = ui.column().classes("ds-right-panel")

    with panel:
        with ui.tabs().classes("w-full ds-right-tabs") as tabs:
            artifacts_tab = ui.tab("Artifacts", icon="dashboard")
            files_tab = ui.tab("Dateien", icon="folder")
            history_tab = ui.tab("History", icon="history")

        with ui.tab_panels(tabs, value=artifacts_tab).classes("w-full").style(
            "flex:1 1 0;min-height:0;overflow:hidden"
        ):
            with ui.tab_panel(artifacts_tab).style("padding:8px;height:100%;overflow-y:auto"):
                artifacts_container = ui.column().classes("w-full gap-2")
                with artifacts_container:
                    _build_artifacts_list(agent)

            with ui.tab_panel(files_tab).style("padding:8px;height:100%;overflow-y:auto"):
                _build_file_tree(agent)

            with ui.tab_panel(history_tab).style("padding:8px;height:100%;overflow-y:auto"):
                _build_history_list(agent)

    # Periodisches Update der Artifacts
    def _refresh_artifacts():
        try:
            artifacts_container.clear()
            with artifacts_container:
                _build_artifacts_list(agent)
        except Exception:
            pass

    ui.timer(15.0, _refresh_artifacts)

    return panel
