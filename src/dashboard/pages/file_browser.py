"""Dateien-Browser: Inbox, Archiv und Pruefung mit Suche, Upload und Finder-Integration.

UI Design Overhaul: Crisp Karten, konsistente Buttons, bessere Tabellen.
"""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from nicegui import events, ui

from ...config import load_config
from ..theme import callout, empty_state, page_header, section_title, stat_card


def _count_files(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for f in folder.rglob("*") if f.is_file())


def _open_in_finder(path: Path) -> None:
    target = str(path)
    try:
        system = platform.system()
        if system == "Darwin":
            if path.is_file():
                subprocess.Popen(["open", "-R", target])
            else:
                subprocess.Popen(["open", target])
        elif system == "Windows":
            if path.is_file():
                subprocess.Popen(["explorer", "/select,", target])
            else:
                subprocess.Popen(["explorer", target])
        else:
            subprocess.Popen(["xdg-open", target if path.is_dir() else str(path.parent)])
        ui.notify(f"Geoeffnet: {path.name}", type="positive")
    except Exception as e:
        ui.notify(f"Konnte nicht geoeffnet werden: {e}", type="negative")


def _build_file_table(folder: Path, search_term: str = "", show_actions: bool = True) -> None:
    if not folder.exists():
        empty_state("folder_off", "Ordner nicht gefunden", f"Der Ordner '{folder}' existiert noch nicht. Prüfe den Pfad unter Einstellungen → Pfade.")
        return

    def _safe_mtime(f: Path) -> float:
        try:
            return f.stat().st_mtime
        except OSError:
            return 0.0  # Datei zwischen Scan und stat() gelöscht

    files = sorted(
        [f for f in folder.rglob("*") if f.is_file()],
        key=_safe_mtime,
        reverse=True,
    )

    if not files:
        empty_state("folder_open", "Keine Dateien vorhanden", "Lade Dokumente über den Upload-Bereich oben hoch oder lege Dateien direkt in den Ordner.")
        return

    rows = []
    for f in files:
        try:
            stat = f.stat()
            size_kb = stat.st_size / 1024
            size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
        except OSError:
            size_str = "?"
            mtime = "?"

        try:
            rel = f.relative_to(folder)
            display_name = str(rel) if str(rel) != f.name else f.name
        except ValueError:
            display_name = f.name

        if search_term and search_term.lower() not in display_name.lower():
            continue

        rows.append({
            "name": display_name,
            "typ": f.suffix.lower(),
            "groesse": size_str,
            "datum": mtime,
        })

    if not rows:
        empty_state("search_off", f"Keine Treffer für '{search_term}'", "Versuche einen anderen Suchbegriff oder lösche die Suche um alle Dateien anzuzeigen.")
        return

    columns = [
        {"name": "name", "label": "Name", "field": "name", "sortable": True, "align": "left"},
        {"name": "typ", "label": "Typ", "field": "typ", "sortable": True},
        {"name": "groesse", "label": "Groesse", "field": "groesse", "sortable": True},
        {"name": "datum", "label": "Geaendert", "field": "datum", "sortable": True},
    ]

    ui.table(
        columns=columns, rows=rows, row_key="name",
        pagination={"rowsPerPage": 50},
    ).classes("w-full ds-table")

    if show_actions:
        with ui.row().classes("gap-2 mt-2"):
            ui.button(
                "Im Finder öffnen", on_click=lambda: _open_in_finder(folder), icon="folder_open",
            ).classes("ds-btn-ghost").props("size=sm").tooltip("Diesen Ordner im Dateimanager anzeigen")
            ui.label(f"{len(rows)} Dateien").classes("text-sm text-gray-400 pt-1")


def _build_archive_tree(archive: Path) -> None:
    if not archive.exists():
        empty_state("archive", "Archiv nicht gefunden", f"Der Archiv-Ordner '{archive}' existiert noch nicht. Prüfe den Pfad unter Einstellungen → Pfade.")
        return

    dirs = sorted([d for d in archive.iterdir() if d.is_dir()])
    if not dirs:
        empty_state("archive", "Archiv ist noch leer", "Lade Dokumente in die Inbox und starte die Verarbeitung — Doc-Sorter sortiert sie automatisch in Kategorien.")
        return

    total_files = sum(sum(1 for _ in d.rglob("*") if _.is_file()) for d in dirs)
    ui.label(f"{total_files} Dateien in {len(dirs)} Kategorien").classes("text-sm text-gray-500 mb-2")

    for doc_type_dir in dirs:
        file_count = sum(1 for _ in doc_type_dir.rglob("*") if _.is_file())
        icon = "folder_special" if doc_type_dir.name.startswith("_") else "folder"
        with ui.expansion(
            f"{doc_type_dir.name}  ({file_count} Dateien)", icon=icon,
        ).classes("w-full ds-expansion"):
            subdirs = sorted([d for d in doc_type_dir.iterdir() if d.is_dir()])
            if subdirs:
                for sub in subdirs:
                    sub_count = sum(1 for _ in sub.rglob("*") if _.is_file())
                    with ui.expansion(
                        f"{sub.name}  ({sub_count})", icon="folder",
                    ).classes("w-full ml-4 ds-expansion"):
                        sub_subdirs = sorted([d for d in sub.iterdir() if d.is_dir()])
                        if sub_subdirs:
                            for ssub in sub_subdirs:
                                ssub_count = sum(1 for _ in ssub.rglob("*") if _.is_file())
                                with ui.expansion(
                                    f"{ssub.name}  ({ssub_count})", icon="folder",
                                ).classes("w-full ml-4 ds-expansion"):
                                    _build_file_table(ssub)
                        else:
                            _build_file_table(sub)
            else:
                _build_file_table(doc_type_dir)


def build() -> None:
    """Dateien-Browser-Seite aufbauen."""
    cfg = load_config()

    inbox = Path(cfg["paths"]["inbox"])
    archive = Path(cfg["paths"]["archive"])
    review = Path(cfg["paths"].get("review", str(archive / "_review")))

    inbox_count = _count_files(inbox)
    review_count = _count_files(review)
    archive_count = _count_files(archive)

    page_header("Dateien", "Alle Dateien in Inbox, Archiv und Prüfung durchsuchen und verwalten.")

    # Upload
    with ui.card().classes("ds-card w-full"):
        section_title("Dateien hochladen", "cloud_upload")

        def handle_upload(e: events.UploadEventArguments) -> None:
            inbox.mkdir(parents=True, exist_ok=True)
            target = inbox / e.name
            # Kollision: Zaehler statt Zeitstempel (eindeutiger)
            if target.exists():
                stem, suffix = target.stem, target.suffix
                counter = 1
                while target.exists() and counter <= 999:
                    target = inbox / f"{stem}_{counter:03d}{suffix}"
                    counter += 1
            # Atomares Schreiben: kein korruptes File bei Abbruch
            content = e.content.read()
            tmp_fd, tmp_path = tempfile.mkstemp(dir=inbox, suffix=".tmp")
            try:
                with os.fdopen(tmp_fd, "wb") as f:
                    f.write(content)
                os.replace(tmp_path, target)
            except Exception as exc:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                ui.notify(f"Upload fehlgeschlagen: {exc}", type="negative")
                return
            ui.notify(f"Hochgeladen: {target.name}", type="positive")

        ui.upload(
            label="Dokumente hierher ziehen oder klicken zum Hochladen (PDF, Word, Bilder)",
            on_upload=handle_upload,
            auto_upload=True,
            multiple=True,
        ).classes("w-full").props("accept='.pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.tif,.tiff'")

    # Suche
    with ui.row().classes("w-full mb-3 items-end gap-3 mt-2"):
        search_input = ui.input(
            label="Datei suchen", placeholder="z.B. GASAG, Rechnung, 2024",
        ).classes("w-64 ds-input").props("clearable")

    with ui.tabs().classes("w-full ds-tabs") as tabs:
        tab_inbox = ui.tab(f"Inbox ({inbox_count})", icon="inbox")
        tab_archive = ui.tab(f"Archiv ({archive_count})", icon="archive")
        tab_review = ui.tab(f"Pruefung ({review_count})", icon="rate_review")

    panel_container = ui.tab_panels(tabs, value=tab_inbox).classes("w-full")

    def _refresh_panels() -> None:
        panel_container.clear()
        with panel_container:
            with ui.tab_panel(tab_inbox):
                _build_file_table(inbox, search_input.value or "")
            with ui.tab_panel(tab_archive):
                _build_archive_tree(archive)
            with ui.tab_panel(tab_review):
                _build_file_table(review, search_input.value or "")

    _refresh_panels()
    search_input.on("keyup.enter", lambda _: _refresh_panels())

    with ui.row().classes("mt-4 gap-3"):
        ui.button("Aktualisieren", on_click=lambda: ui.navigate.reload(), icon="refresh").classes("ds-btn-secondary").tooltip("Dateilisten neu laden")
        ui.button("Inbox öffnen", on_click=lambda: _open_in_finder(inbox), icon="folder_open").classes("ds-btn-ghost").tooltip("Inbox-Ordner im Finder anzeigen")
        ui.button("Archiv öffnen", on_click=lambda: _open_in_finder(archive), icon="folder_open").classes("ds-btn-ghost").tooltip("Archiv-Ordner im Finder anzeigen")
