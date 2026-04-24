"""Einstellungen — ueber Profil-Dropdown erreichbar.

Sektionen:
  1. Pfade  (inline editierbar, direkter YAML-Save)
  2. Taxonomie (Dateiname-Muster, Ordner-Muster — mit Live-Vorschau)
  3. Schlagwoerter & Klassifikation (Link zu keywords_hub)
  4. Erweiterte Konfiguration (Link zum YAML-Editor)
  5. System & Lern-Engine (Link)

Alle Forms nutzen load_config_raw() + save_config() — nie die expandierte
Config direkt zurueckschreiben.
"""

from __future__ import annotations

from datetime import datetime as _dt
from pathlib import Path
from typing import Any

from nicegui import ui

from ...config import load_config_raw, save_config
from ..theme import callout, page_header, section_title


_PATH_LABELS = {
    "inbox":   ("Eingabe-Ordner",    "Hier legst du neue Dokumente ab."),
    "archive": ("Archiv-Ordner",     "Sortierte Dokumente landen hier."),
    "review":  ("Pruefungs-Ordner",  "Unsichere Dokumente landen hier."),
    "logs":    ("Protokoll-Ordner",  "Verarbeitungs-History wird hier gespeichert."),
}


def _nav_card(icon: str, title: str, subtitle: str, route: str) -> None:
    """Anklickbare Navigations-Karte (als Link)."""
    with ui.element("a").props(f'href="{route}"').style(
        "text-decoration:none;display:block;width:100%"
    ):
        with ui.element("div").style(
            "border:1px solid var(--ds-border);border-radius:12px;"
            "background:rgba(10,22,40,0.6);padding:16px 20px;"
            "transition:all 0.2s;cursor:pointer;display:flex;align-items:center;gap:16px"
        ).classes("ds-card-flat"):
            with ui.element("div").style(
                "width:40px;height:40px;border-radius:10px;display:flex;"
                "align-items:center;justify-content:center;"
                "background:rgba(0,212,255,0.12);color:#00d4ff;flex-shrink:0"
            ):
                ui.icon(icon).style("font-size:1.25rem")
            with ui.column().classes("gap-0").style("flex:1"):
                ui.label(title).style(
                    "font-size:0.92rem;font-weight:700;color:var(--ds-text)"
                )
                ui.label(subtitle).style(
                    "font-size:0.75rem;color:var(--ds-text-2);margin-top:2px"
                )
            ui.icon("arrow_forward").style(
                "color:var(--ds-text-3);font-size:1.1rem;flex-shrink:0"
            )


def build() -> None:
    """Einstellungs-Seite aufbauen."""
    page_header(
        "Einstellungen",
        "Pfade, Taxonomie, Schlagwoerter und erweiterte Konfiguration.",
    )

    cfg = load_config_raw()

    # =========================================================
    # Sektion 1 — Pfade
    # =========================================================
    with ui.card().classes("ds-card w-full"):
        section_title("Pfade", "folder")
        ui.label(
            "Wo liegen Eingaenge, Archiv und Prueflauf? "
            "Tilde (~) wird zu deinem Home-Verzeichnis expandiert."
        ).style("font-size:0.78rem;color:var(--ds-text-2);margin-bottom:12px")

        paths = cfg.setdefault("paths", {})
        path_inputs: dict[str, ui.input] = {}

        for key, (label, hint) in _PATH_LABELS.items():
            path_inputs[key] = ui.input(
                label=label,
                value=paths.get(key, ""),
            ).classes("w-full ds-input").props("outlined dense")
            ui.label(hint).style(
                "font-size:0.7rem;color:var(--ds-text-3);margin-bottom:10px;margin-top:-4px"
            )

        def _save_paths() -> None:
            raw = load_config_raw()
            for key, inp in path_inputs.items():
                raw.setdefault("paths", {})[key] = (inp.value or "").strip()
            save_config(raw)
            ui.notify("Pfade gespeichert.", type="positive", position="top")

        with ui.row().classes("justify-end w-full mt-2"):
            ui.button(
                "Pfade speichern", on_click=_save_paths, icon="save"
            ).classes("ds-btn-primary").props("unelevated no-caps")

    # =========================================================
    # Sektion 2 — Taxonomie
    # =========================================================
    with ui.card().classes("ds-card w-full mt-4"):
        section_title("Taxonomie", "drive_file_rename_outline")
        ui.label(
            "Wie werden Dateien benannt und abgelegt? "
            "Platzhalter in {} werden automatisch ersetzt."
        ).style("font-size:0.78rem;color:var(--ds-text-2);margin-bottom:12px")

        taxonomy = cfg.setdefault("taxonomy", {
            "filename_pattern": "{dokumentenart}_{kunde}_{land}_{datum}",
            "folder_pattern":   "{dokumentenart}/{land}/{kunde}/{jahr}",
        })

        fn_inp = ui.input(
            label="Dateiname-Muster",
            value=taxonomy.get("filename_pattern", ""),
        ).classes("w-full ds-input").props("outlined dense")
        ui.label("Platzhalter: {dokumentenart}  {kunde}  {land}  {datum}").style(
            "font-size:0.7rem;color:var(--ds-text-3);margin-bottom:8px;margin-top:-4px"
        )

        folder_inp = ui.input(
            label="Ordner-Muster",
            value=taxonomy.get("folder_pattern", ""),
        ).classes("w-full ds-input").props("outlined dense")
        ui.label("Platzhalter: {dokumentenart}  {land}  {kunde}  {jahr}  (/ fuer Unterordner)").style(
            "font-size:0.7rem;color:var(--ds-text-3);margin-bottom:12px;margin-top:-4px"
        )

        # Vorschau
        preview = ui.element("div").style(
            "border:1px solid rgba(0,212,255,0.2);border-radius:10px;"
            "background:rgba(0,212,255,0.04);padding:12px 14px;width:100%"
        )

        def _refresh_preview() -> None:
            sample = {
                "dokumentenart": "rechnung",
                "kunde": "GASAG",
                "land": "deutschland",
                "datum": _dt.now().strftime("%d.%m.%y"),
                "jahr": _dt.now().strftime("%Y"),
            }
            try:
                fn_ex = (fn_inp.value or "").format(**sample) + ".pdf"
                fd_ex = (folder_inp.value or "").format(**sample)
            except (KeyError, ValueError):
                fn_ex = "(Muster ungueltig)"
                fd_ex = "(Muster ungueltig)"
            preview.clear()
            with preview:
                ui.label("Vorschau (Rechnung von GASAG, Deutschland):").style(
                    "font-size:0.65rem;font-weight:700;color:#00d4ff;"
                    "text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px"
                )
                with ui.column().classes("gap-1").style("font-family:'JetBrains Mono',monospace;font-size:0.8rem"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("folder").style("color:#ff9f0a;font-size:1rem")
                        ui.label(fd_ex + "/").style("color:#00d4ff")
                    with ui.row().classes("items-center gap-2").style("margin-left:20px"):
                        ui.icon("description").style("color:#a78bfa;font-size:1rem")
                        ui.label(fn_ex).style("color:var(--ds-text);font-weight:700")

        _refresh_preview()
        fn_inp.on("keyup", lambda _: _refresh_preview())
        folder_inp.on("keyup", lambda _: _refresh_preview())

        def _save_taxonomy() -> None:
            raw = load_config_raw()
            raw.setdefault("taxonomy", {})["filename_pattern"] = (fn_inp.value or "").strip()
            raw["taxonomy"]["folder_pattern"] = (folder_inp.value or "").strip()
            save_config(raw)
            ui.notify("Taxonomie gespeichert.", type="positive", position="top")

        with ui.row().classes("justify-end w-full mt-3"):
            ui.button(
                "Taxonomie speichern", on_click=_save_taxonomy, icon="save"
            ).classes("ds-btn-primary").props("unelevated no-caps")

    # =========================================================
    # Sektion 3 — Links zu Hubs
    # =========================================================
    ui.html('<div style="height:24px"></div>', sanitize=False)
    section_title("Weitere Bereiche", "tune")

    with ui.column().classes("w-full gap-3"):
        _nav_card(
            "label",
            "Schlagwoerter & Klassifikation",
            "Dokumentenarten, Kunden, Laender und globale Schlagwoerter.",
            "/keywords",
        )
        _nav_card(
            "code",
            "Erweiterte Konfiguration",
            "Komplette config.yaml direkt bearbeiten — fuer Profis.",
            "/config",
        )
        _nav_card(
            "memory",
            "System & Lern-Engine",
            "System-Status, OCR, KI-Anbieter und Trainings-Statistik.",
            "/system",
        )
