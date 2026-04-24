"""Dateien & Archiv — kombinierte Seite.

Vereint:
- Dateien-Browser (Inbox, Archiv, Prüfung) mit Suche, Upload, Finder-Integration
- Archiv-Kategorienbaum (expandierbar, verschachtelt)
- Verarbeitungs-History (zuletzt archivierte Dokumente aus LogManager)

Route: /dateien  (ersetzt auch /files)
"""

from __future__ import annotations

import platform
import subprocess
from datetime import datetime
from pathlib import Path

from nicegui import events, ui

from ..theme import callout, empty_state, page_header, section_title


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _count_files(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for f in folder.rglob("*") if f.is_file())


def _open_in_finder(path: Path) -> None:
    try:
        system = platform.system()
        target = str(path)
        if system == "Darwin":
            subprocess.Popen(["open", "-R", target] if path.is_file() else ["open", target])
        elif system == "Windows":
            subprocess.Popen(["explorer", "/select,", target] if path.is_file() else ["explorer", target])
        else:
            subprocess.Popen(["xdg-open", target if path.is_dir() else str(path.parent)])
        ui.notify(f"Geöffnet: {path.name}", type="positive")
    except Exception as e:
        ui.notify(f"Konnte nicht geöffnet werden: {e}", type="negative")


def _file_icon(ext: str) -> tuple[str, str]:
    """Icon und Farbe je Dateityp."""
    m = {
        ".pdf":  ("picture_as_pdf", "#ff3366"),
        ".docx": ("description",    "#3B82F6"),
        ".doc":  ("description",    "#3B82F6"),
        ".txt":  ("article",        "#9CA3AF"),
        ".md":   ("article",        "#9CA3AF"),
        ".png":  ("image",          "#00e87d"),
        ".jpg":  ("image",          "#00e87d"),
        ".jpeg": ("image",          "#00e87d"),
        ".tif":  ("image",          "#00e87d"),
        ".tiff": ("image",          "#00e87d"),
        ".xlsx": ("table_chart",    "#22C55E"),
        ".csv":  ("table_chart",    "#22C55E"),
    }
    return m.get(ext.lower(), ("insert_drive_file", "#6B7280"))


# ---------------------------------------------------------------------------
# Inbox / Prüfung: sortierbare Tabelle
# ---------------------------------------------------------------------------

def _build_file_table(folder: Path, search_term: str = "") -> None:
    if not folder.exists():
        empty_state(
            "folder_off", "Ordner nicht gefunden",
            f"Der Ordner existiert noch nicht. Prüfe die Pfade unter Einstellungen.",
        )
        return

    files = sorted(
        [f for f in folder.rglob("*") if f.is_file()],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    if search_term:
        files = [f for f in files if search_term.lower() in f.name.lower()]

    if not files and not search_term:
        empty_state(
            "folder_open", "Keine Dateien vorhanden",
            "Lade Dokumente über den Upload-Bereich oben hoch oder lege Dateien direkt in den Ordner.",
        )
        return

    if not files:
        empty_state(
            "search_off", f'Keine Treffer für "{search_term}"',
            "Versuche einen anderen Suchbegriff oder leere das Suchfeld.",
        )
        return

    rows = []
    for f in files:
        try:
            stat = f.stat()
            size_kb = stat.st_size / 1024
            size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
        except OSError:
            size_str, mtime = "?", "?"
        try:
            rel = str(f.relative_to(folder))
        except ValueError:
            rel = f.name
        rows.append({"name": rel, "typ": f.suffix.lower(), "groesse": size_str, "datum": mtime})

    ui.table(
        columns=[
            {"name": "name",    "label": "Name",     "field": "name",    "sortable": True, "align": "left"},
            {"name": "typ",     "label": "Typ",      "field": "typ",     "sortable": True},
            {"name": "groesse", "label": "Größe",    "field": "groesse", "sortable": True},
            {"name": "datum",   "label": "Geändert", "field": "datum",   "sortable": True},
        ],
        rows=rows, row_key="name",
        pagination={"rowsPerPage": 50},
    ).classes("w-full ds-table")

    with ui.row().classes("gap-2 mt-2 items-center"):
        ui.button(
            "Im Finder öffnen", on_click=lambda: _open_in_finder(folder), icon="folder_open",
        ).classes("ds-btn-ghost").props("size=sm dense").tooltip("Ordner im Dateimanager anzeigen")
        ui.label(f"{len(rows)} Dateien").style("font-size:0.78rem;color:var(--ds-text-3)")


# ---------------------------------------------------------------------------
# Archiv: expandierbarer Kategorienbaum
# ---------------------------------------------------------------------------

def _build_archive_tree(archive: Path, search_term: str = "") -> None:
    if not archive.exists():
        empty_state("archive", "Archiv nicht gefunden",
                    "Der Archiv-Ordner existiert noch nicht. Prüfe die Pfade unter Einstellungen.")
        return

    dirs = sorted([d for d in archive.iterdir() if d.is_dir()])
    if not dirs:
        empty_state("archive", "Archiv ist noch leer",
                    "Lade Dokumente in die Inbox und starte die Verarbeitung — "
                    "Doc-Sorter sortiert sie automatisch in Kategorien.")
        return

    total_files = sum(_count_files(d) for d in dirs)

    # Stat-Zeile
    with ui.row().classes("items-center gap-4 mb-3"):
        with ui.element("div").style(
            "background:rgba(0,232,125,0.08);border:1px solid rgba(0,232,125,0.2);"
            "border-radius:8px;padding:6px 14px;display:flex;gap:8px;align-items:center"
        ):
            ui.icon("archive").style("font-size:1rem;color:#00e87d")
            ui.label(f"{total_files} Dateien in {len(dirs)} Kategorien").style(
                "font-size:0.82rem;font-weight:600;color:#00e87d"
            )
        ui.button(
            "Im Finder öffnen", on_click=lambda: _open_in_finder(archive), icon="folder_open",
        ).classes("ds-btn-ghost").props("size=sm dense")

    for doc_type_dir in dirs:
        file_count = _count_files(doc_type_dir)

        # Suche: Ordner nur anzeigen wenn Treffer drin
        if search_term:
            matching = [f for f in doc_type_dir.rglob("*")
                        if f.is_file() and search_term.lower() in f.name.lower()]
            if not matching:
                continue

        folder_icon = "folder_special" if doc_type_dir.name.startswith("_") else "folder"
        color = "#00e87d" if not doc_type_dir.name.startswith("_") else "#F59E0B"

        with ui.expansion(
            f"{doc_type_dir.name}  ({file_count} Dateien)", icon=folder_icon,
        ).classes("w-full").style(
            f"border:1px solid {color}20;border-radius:10px;"
            f"background:{color}05;margin-bottom:6px"
        ):
            subdirs = sorted([d for d in doc_type_dir.iterdir() if d.is_dir()])
            if subdirs:
                for sub in subdirs:
                    sub_count = _count_files(sub)
                    with ui.expansion(
                        f"{sub.name}  ({sub_count})", icon="folder",
                    ).classes("w-full ml-4").style(
                        "border:1px solid rgba(255,255,255,0.06);border-radius:8px;margin-bottom:4px"
                    ):
                        sub_subdirs = sorted([d for d in sub.iterdir() if d.is_dir()])
                        if sub_subdirs:
                            for ssub in sub_subdirs:
                                ssub_count = _count_files(ssub)
                                with ui.expansion(
                                    f"{ssub.name}  ({ssub_count})", icon="folder",
                                ).classes("w-full ml-4").style(
                                    "border:1px solid rgba(255,255,255,0.04);border-radius:8px;margin-bottom:2px"
                                ):
                                    _build_file_table(ssub, search_term)
                        else:
                            _build_file_table(sub, search_term)
            else:
                _build_file_table(doc_type_dir, search_term)


# ---------------------------------------------------------------------------
# History-Tab
# ---------------------------------------------------------------------------

def _build_history_tab(logs_dir: Path) -> None:
    if not logs_dir.exists():
        empty_state(
            "history", "Noch keine History",
            "Sortiere Dokumente im Chat — dann erscheint hier der Verarbeitungs-Verlauf.",
        )
        return

    try:
        from ...logger import LogManager
        log_mgr = LogManager(logs_dir)
        all_logs = sorted(
            log_mgr.get_all_logs(),
            key=lambda x: x.get("timestamp", ""),
            reverse=True,
        )[:100]
    except Exception as e:
        ui.label(f"History konnte nicht geladen werden: {e}").style(
            "font-size:0.8rem;color:#EF4444;padding:16px"
        )
        return

    if not all_logs:
        empty_state(
            "history", "Noch keine Einträge",
            "Verarbeitete Dokumente erscheinen hier mit Typ, Kunde und Zeitstempel.",
        )
        return

    # Filter-Bar
    with ui.row().classes("items-center gap-3 mb-3 flex-wrap"):
        hist_search = ui.input(
            placeholder="Dateiname oder Kunde suchen …"
        ).classes("flex-1 ds-input").props("outlined dense clearable")
        hist_container = ui.column().classes("w-full gap-0")

    def _render_history(term: str = "") -> None:
        hist_container.clear()
        filtered = all_logs
        if term:
            filtered = [
                l for l in all_logs
                if term.lower() in (l.get("source", "") + l.get("kunde", "") +
                                    l.get("dokumentenart", "")).lower()
            ]
        with hist_container:
            if not filtered:
                empty_state("search_off", f'Keine Treffer für "{term}"', "")
                return
            for log in filtered:
                ts = log.get("timestamp", "")
                try:
                    ts_str = datetime.fromisoformat(ts).strftime("%d.%m.%Y %H:%M")
                except Exception:
                    ts_str = ts[:16]
                src   = Path(log.get("source", "")).name or "?"
                dtype = log.get("dokumentenart",
                                log.get("classification", {}).get("dokumentenart", "?"))
                kunde = log.get("kunde",
                                log.get("classification", {}).get("kunde", "?"))

                icon_name, icon_color = _file_icon(Path(src).suffix)

                with ui.element("div").style(
                    "display:flex;align-items:center;gap:12px;padding:9px 14px;"
                    "border-bottom:1px solid rgba(255,255,255,0.04);"
                    "transition:background 0.15s"
                ):
                    ui.icon(icon_name).style(
                        f"font-size:1.1rem;color:{icon_color};flex-shrink:0"
                    )
                    with ui.column().classes("gap-0 flex-1 min-w-0"):
                        ui.label(src).style(
                            "font-size:0.82rem;font-weight:600;color:var(--ds-text);"
                            "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                        )
                        with ui.row().classes("items-center gap-2"):
                            if dtype and dtype != "?":
                                ui.label(dtype).style(
                                    "font-size:0.65rem;font-weight:700;padding:1px 7px;"
                                    "border-radius:4px;background:rgba(0,212,255,0.1);"
                                    "color:#00d4ff;border:1px solid rgba(0,212,255,0.2)"
                                )
                            if kunde and kunde != "?":
                                ui.label(kunde).style(
                                    "font-size:0.65rem;color:var(--ds-text-2)"
                                )
                    ui.label(ts_str).style(
                        "font-size:0.68rem;color:#9CA3AF;white-space:nowrap;flex-shrink:0"
                    )

        ui.label(f"{len(filtered)} Einträge").style(
            "font-size:0.72rem;color:var(--ds-text-3);padding:8px 14px"
        )

    _render_history()
    hist_search.on("keyup", lambda e: _render_history(hist_search.value or ""))
    hist_search.on("clear", lambda: _render_history(""))


# ---------------------------------------------------------------------------
# Haupt-Build
# ---------------------------------------------------------------------------

def build() -> None:
    """Kombinierte Dateien & Archiv Seite."""
    try:
        from ...config import load_config, get_file_types
        cfg = load_config()
        inbox   = Path(cfg["paths"]["inbox"]).expanduser()
        archive = Path(cfg["paths"]["archive"]).expanduser()
        review  = Path(cfg["paths"].get("review", str(archive / "_review"))).expanduser()
        logs    = Path(cfg["paths"]["logs"]).expanduser()
    except Exception as e:
        ui.label(f"Konfiguration konnte nicht geladen werden: {e}").style(
            "color:#EF4444;padding:16px"
        )
        return

    inbox_count   = _count_files(inbox)
    archive_count = _count_files(archive)
    review_count  = _count_files(review)

    # ── Seitenkopf ─────────────────────────────────────────────────────────
    with ui.row().classes("items-center gap-3 mb-2 flex-wrap"):
        with ui.element("div").style(
            "width:44px;height:44px;border-radius:12px;"
            "background:rgba(0,232,125,0.12);border:1px solid rgba(0,232,125,0.3);"
            "display:flex;align-items:center;justify-content:center;flex-shrink:0"
        ):
            ui.icon("folder_special").style("font-size:1.4rem;color:#00e87d")
        with ui.column().classes("gap-0 flex-1"):
            ui.label("Dateien & Archiv").style(
                "font-size:1.3rem;font-weight:700;color:var(--ds-text)"
            )
            ui.label("Inbox · Archiv · Prüfung · History — alles an einem Ort").style(
                "font-size:0.8rem;color:var(--ds-text-2)"
            )

    # ── Stat-Chips ──────────────────────────────────────────────────────────
    with ui.row().classes("gap-3 mb-4 flex-wrap"):
        for label, count, color, icon in [
            ("Inbox",   inbox_count,   "#3B82F6", "inbox"),
            ("Archiv",  archive_count, "#00e87d", "archive"),
            ("Prüfung", review_count,  "#F59E0B", "rate_review"),
        ]:
            with ui.element("div").style(
                f"display:flex;align-items:center;gap:8px;padding:6px 14px;"
                f"border-radius:8px;background:{color}10;border:1px solid {color}30"
            ):
                ui.icon(icon).style(f"font-size:0.9rem;color:{color}")
                ui.label(f"{label}").style(f"font-size:0.75rem;color:{color};font-weight:600")
                ui.label(str(count)).style(
                    f"font-size:0.82rem;font-weight:800;color:{color}"
                )

    # ── Upload ──────────────────────────────────────────────────────────────
    with ui.expansion("Datei hochladen", icon="cloud_upload").classes("w-full mb-3").style(
        "border:1px solid rgba(0,212,255,0.15);border-radius:12px;"
        "background:rgba(0,212,255,0.03)"
    ):
        ui.label("Hochgeladene Dateien landen automatisch in der Inbox.").style(
            "font-size:0.75rem;color:var(--ds-text-2);margin-bottom:8px"
        )

        def handle_upload(e: events.UploadEventArguments) -> None:
            inbox.mkdir(parents=True, exist_ok=True)
            target = inbox / e.name
            if target.exists():
                stamp = datetime.now().strftime("%H%M%S")
                target = inbox / f"{target.stem}_{stamp}{target.suffix}"
            target.write_bytes(e.content.read())
            ui.notify(f"✓ Hochgeladen: {target.name}", type="positive")

        ui.upload(
            label="PDF, Word, Bilder hierher ziehen oder klicken",
            on_upload=handle_upload,
            auto_upload=True,
            multiple=True,
        ).classes("w-full").props("accept='.pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.tif,.tiff'")

    # ── Globale Suche ───────────────────────────────────────────────────────
    with ui.row().classes("items-center gap-3 mb-3 w-full"):
        search_input = ui.input(
            placeholder="Datei suchen — z.B. GASAG, Rechnung, 2026 …"
        ).classes("flex-1 ds-input").props("outlined dense clearable")
        search_input.style("max-width:520px")
        ui.label("Suche gilt für Inbox, Archiv und Prüfung.").style(
            "font-size:0.72rem;color:var(--ds-text-3)"
        )

    # ── Tabs ────────────────────────────────────────────────────────────────
    _inbox_lbl   = f"Inbox ({inbox_count})"
    _archive_lbl = f"Archiv ({archive_count})"
    _review_lbl  = f"Prüfung ({review_count})"

    with ui.tabs().classes("w-full mb-2").props("dense align=left") as tabs:
        tab_inbox   = ui.tab(_inbox_lbl,   icon="inbox"      ).tooltip("Neue, noch nicht verarbeitete Dokumente")
        tab_archive = ui.tab(_archive_lbl, icon="archive"    ).tooltip("Sortiertes Archiv — nach Typ und Kunde gegliedert")
        tab_review  = ui.tab(_review_lbl,  icon="rate_review").tooltip("Dokumente mit niedriger Erkennungs-Konfidenz")
        tab_history = ui.tab("History",    icon="history"    ).tooltip("Zuletzt verarbeitete und archivierte Dokumente")

    panel_container = ui.tab_panels(tabs, value=tab_inbox).classes("w-full")

    def _refresh_panels(search_term: str = "") -> None:
        panel_container.clear()
        with panel_container:
            with ui.tab_panel(tab_inbox):
                _build_file_table(inbox, search_term)

            with ui.tab_panel(tab_archive):
                _build_archive_tree(archive, search_term)

            with ui.tab_panel(tab_review):
                if review_count == 0 and not search_term:
                    with ui.element("div").style(
                        "text-align:center;padding:40px;color:var(--ds-text-3)"
                    ):
                        with ui.element("div").style(
                            "width:56px;height:56px;border-radius:14px;margin:0 auto 12px;"
                            "background:rgba(0,232,125,0.1);border:1px solid rgba(0,232,125,0.2);"
                            "display:flex;align-items:center;justify-content:center"
                        ):
                            ui.icon("check_circle").style("font-size:1.6rem;color:#00e87d")
                        ui.label("Nichts zu prüfen").style(
                            "font-size:0.95rem;font-weight:600;color:#00e87d;margin-bottom:4px"
                        )
                        ui.label("Alle Dokumente wurden sicher erkannt.").style(
                            "font-size:0.78rem"
                        )
                else:
                    _build_file_table(review, search_term)

            with ui.tab_panel(tab_history):
                with ui.card().classes("w-full").style(
                    "background:rgba(10,22,40,0.6);border:1px solid rgba(255,255,255,0.06);"
                    "border-radius:12px;overflow:hidden;padding:0"
                ):
                    _build_history_tab(logs)

    _refresh_panels()

    def _on_search():
        _refresh_panels(search_input.value or "")

    search_input.on("keyup.enter", lambda _: _on_search())
    search_input.on("clear",       lambda _: _refresh_panels(""))

    # ── Footer-Aktionen ─────────────────────────────────────────────────────
    with ui.row().classes("mt-4 gap-3 flex-wrap"):
        ui.button(
            "Aktualisieren", on_click=lambda: ui.navigate.reload(), icon="refresh",
        ).classes("ds-btn-secondary").tooltip("Dateilisten neu laden")
        ui.button(
            "Inbox öffnen", on_click=lambda: _open_in_finder(inbox), icon="folder_open",
        ).classes("ds-btn-ghost").tooltip("Inbox-Ordner im Dateimanager anzeigen")
        ui.button(
            "Archiv öffnen", on_click=lambda: _open_in_finder(archive), icon="folder_open",
        ).classes("ds-btn-ghost").tooltip("Archiv-Ordner im Dateimanager anzeigen")
