"""Ordner-Browser: SharePoint-inspirierter lokaler Archiv-Verzeichnisbaum."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

from nicegui import ui

from ...config import load_config
from ..theme import enable_scroll, page_header, section_title, empty_state

# Kategorie-Farben
_CATEGORY_COLORS: dict[str, str] = {
    "rechnung":  "#3b82f6",
    "vertrag":   "#22c55e",
    "angebot":   "#f97316",
    "mahnung":   "#ef4444",
    "brief":     "#a855f7",
    "bericht":   "#06b6d4",
    "protokoll": "#14b8a6",
    "sonstiges": "#64748b",
}

_DEFAULT_COLOR = "#64748b"

_FILE_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _get_category_color(folder_name: str) -> str:
    name_lower = folder_name.lower()
    for key, color in _CATEGORY_COLORS.items():
        if key in name_lower:
            return color
    return _DEFAULT_COLOR


def _count_files(path: Path) -> int:
    try:
        return sum(1 for f in path.rglob("*") if f.is_file() and f.suffix.lower() in _FILE_EXTENSIONS)
    except PermissionError:
        return 0


def _count_direct_files(path: Path) -> int:
    try:
        return sum(1 for f in path.iterdir() if f.is_file() and f.suffix.lower() in _FILE_EXTENSIONS)
    except PermissionError:
        return 0


def _count_subdirs(path: Path) -> int:
    try:
        return sum(1 for f in path.iterdir() if f.is_dir())
    except PermissionError:
        return 0


def _open_in_finder(path: Path) -> None:
    try:
        system = platform.system()
        if system == "Darwin":
            subprocess.Popen(["open", str(path)])
        elif system == "Windows":
            subprocess.Popen(["explorer", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:
        ui.notify(f"Fehler beim Öffnen: {e}", type="negative")


def _get_archive_root() -> Path | None:
    try:
        cfg = load_config()
        p = Path(cfg["paths"]["archive"]).expanduser()
        return p if p.exists() else None
    except Exception:
        return None


def _build_folder_tree(
    parent_path: Path,
    search_filter: str,
    depth: int = 0,
    max_depth: int = 3,
) -> None:
    if depth >= max_depth:
        return

    try:
        subdirs = sorted(
            [d for d in parent_path.iterdir() if d.is_dir() and not d.name.startswith(".")],
            key=lambda d: d.name.lower(),
        )
    except PermissionError:
        return

    for folder in subdirs:
        folder_name = folder.name

        if search_filter and search_filter.lower() not in folder_name.lower():
            if depth == 0:
                continue

        color = _get_category_color(folder_name)
        file_count = _count_direct_files(folder)
        total_count = _count_files(folder)
        sub_count = _count_subdirs(folder)
        has_children = sub_count > 0

        with ui.expansion(caption="").classes("w-full").style(
            f"border:1px solid rgba(255,255,255,0.08);border-radius:10px;margin-bottom:6px;"
            f"background:rgba(10,22,40,0.6);overflow:hidden"
        ) as exp:
            with exp.add_slot("header"):
                with ui.row().classes("items-center gap-3 w-full py-1 px-2"):
                    ui.element("div").style(
                        f"width:10px;height:10px;border-radius:50%;"
                        f"background:{color};flex-shrink:0"
                    )
                    ui.icon("folder").style(f"font-size:1.1rem;color:{color};flex-shrink:0")
                    ui.label(folder_name).style(
                        "font-size:0.875rem;font-weight:600;flex:1;color:var(--ds-text)"
                    )
                    if file_count > 0:
                        ui.label(f"{file_count} gesamt").style(
                            f"font-size:0.68rem;background:{color}18;color:{color};"
                            "padding:2px 9px;border-radius:99px;white-space:nowrap;"
                            f"border:1px solid {color}30"
                        )
                    if total_count > file_count:
                        ui.label(f"{total_count} inkl. Unterordner").style(
                            "font-size:0.68rem;background:rgba(255,255,255,0.06);color:var(--ds-text-2);"
                            "padding:2px 9px;border-radius:99px;white-space:nowrap;"
                            "border:1px solid rgba(255,255,255,0.1)"
                        )
                    if sub_count > 0:
                        ui.label(f"{sub_count} Unterordner").style(
                            "font-size:0.68rem;background:rgba(0,232,125,0.08);color:#00e87d;"
                            "padding:2px 9px;border-radius:99px;white-space:nowrap;"
                            "border:1px solid rgba(0,232,125,0.2)"
                        )

                    def make_open(p=folder):
                        return lambda: _open_in_finder(p)

                    ui.button(
                        icon="open_in_new",
                        on_click=make_open(),
                    ).props("flat round dense size=sm").style(
                        "color:var(--ds-text-2)"
                    ).tooltip("Im Finder öffnen")

            with ui.column().classes("w-full pl-4 pb-2 gap-1"):
                try:
                    files = sorted(
                        [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in _FILE_EXTENSIONS],
                        key=lambda f: f.name.lower(),
                    )
                    if files:
                        for f in files[:20]:
                            with ui.row().classes("items-center gap-2 py-1"):
                                ext = f.suffix.lower()
                                icon = "picture_as_pdf" if ext == ".pdf" else (
                                    "image" if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff"} else
                                    "description"
                                )
                                ui.icon(icon).style("font-size:0.9rem;color:var(--ds-text-3);flex-shrink:0")
                                ui.label(f.name).style(
                                    "font-size:0.8rem;color:var(--ds-text-2);flex:1;overflow:hidden;"
                                    "text-overflow:ellipsis;white-space:nowrap"
                                )
                                size_kb = f.stat().st_size / 1024
                                ui.label(f"{size_kb:.0f} KB").style(
                                    "font-size:0.68rem;color:var(--ds-text-3);white-space:nowrap"
                                )
                        if len(files) > 20:
                            ui.label(f"... und {len(files) - 20} weitere Dateien").style(
                                "font-size:0.75rem;color:var(--ds-text-3);padding:4px 0"
                            )
                except PermissionError:
                    ui.label("Kein Zugriff").style("font-size:0.75rem;color:#ef4444")

                if has_children and depth < max_depth - 1:
                    _build_folder_tree(folder, search_filter, depth + 1, max_depth)


def build() -> None:
    """Ordner-Browser aufbauen."""
    page_header("Ordner", "Archivstruktur und Ordner verwalten — alle sortierten Dokumente auf einen Blick")

    archive_root = _get_archive_root()

    if archive_root is None:
        empty_state(
            "folder_off",
            "Archiv-Ordner nicht gefunden",
            "Bitte prüfe den Archiv-Pfad unter Einstellungen → Pfade und stelle sicher, dass der Ordner existiert.",
        )
        return

    total_files = _count_files(archive_root)
    total_subdirs = _count_subdirs(archive_root)

    # Stats Bar — dark mode
    with ui.row().classes("w-full gap-4 mb-6 flex-wrap items-stretch"):
        with ui.card().classes("ds-card flex-1 min-w-36"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("description").style("font-size:1.5rem;color:#3B82F6")
                with ui.column().classes("gap-0"):
                    ui.label("DATEIEN GESAMT").style(
                        "font-size:0.65rem;color:var(--ds-text-3);text-transform:uppercase;letter-spacing:0.06em"
                    )
                    ui.label(str(total_files)).style(
                        "font-size:1.5rem;font-weight:700;color:var(--ds-text)"
                    )

        with ui.card().classes("ds-card flex-1 min-w-36"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("folder").style("font-size:1.5rem;color:#22C55E")
                with ui.column().classes("gap-0"):
                    ui.label("UNTERORDNER").style(
                        "font-size:0.65rem;color:var(--ds-text-3);text-transform:uppercase;letter-spacing:0.06em"
                    )
                    ui.label(str(total_subdirs)).style(
                        "font-size:1.5rem;font-weight:700;color:var(--ds-text)"
                    )

        with ui.card().classes("ds-card flex-1 min-w-48"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("storage").style("font-size:1.5rem;color:#F59E0B")
                with ui.column().classes("gap-0 flex-1 overflow-hidden"):
                    ui.label("ARCHIVPFAD").style(
                        "font-size:0.65rem;color:var(--ds-text-3);text-transform:uppercase;letter-spacing:0.06em"
                    )
                    ui.label(str(archive_root)).style(
                        "font-size:0.75rem;font-weight:500;color:var(--ds-text-2);"
                        "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                    )

        ui.button(
            "Im Finder öffnen",
            icon="open_in_new",
            on_click=lambda: _open_in_finder(archive_root),
        ).classes("ds-btn-primary self-center")

    # Kategorien
    with ui.card().classes("ds-card w-full mb-4"):
        section_title("Kategorien", "palette")
        with ui.row().classes("gap-4 flex-wrap mt-2"):
            for cat_name, cat_color in _CATEGORY_COLORS.items():
                with ui.row().classes("items-center gap-2"):
                    ui.element("div").style(
                        f"width:10px;height:10px;border-radius:50%;background:{cat_color};flex-shrink:0"
                    )
                    ui.label(cat_name.capitalize()).style(
                        "font-size:0.8rem;color:var(--ds-text-2)"
                    )

    # Verzeichnisbaum
    with ui.card().classes("ds-card w-full"):
        section_title("Verzeichnisbaum", "account_tree")

        search_input = ui.input(
            placeholder="z.B. GASAG, Rechnungen, 2024",
            label="Ordner suchen",
        ).classes("w-full mt-3 mb-4 ds-input").props("outlined dense clearable")

        tree_container = ui.column().classes("w-full gap-1")

        def _refresh_tree(search_text: str = ""):
            tree_container.clear()
            with tree_container:
                _build_folder_tree(archive_root, search_text.strip())

        search_input.on("update:model-value", lambda e: _refresh_tree(e.args if isinstance(e.args, str) else ""))
        _refresh_tree()
