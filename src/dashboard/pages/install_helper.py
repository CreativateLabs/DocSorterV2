"""In-App Installations-Hilfe für fehlende Abhängigkeiten.

Zeigt eine freundliche UI wenn Tesseract oder Poppler fehlen —
kein Terminal, kein manuelles Installieren nötig.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

from nicegui import ui

logger = logging.getLogger(__name__)

_OS = platform.system()

# Download-URLs für Tesseract
_TESSERACT_WIN_URL   = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
_TESSERACT_BREW_DOCS = "https://formulae.brew.sh/formula/tesseract"
_HOMEBREW_URL        = "https://brew.sh"
_POPPLER_WIN_URL     = "https://github.com/oschwartz10612/poppler-windows/releases"


def _has_tesseract() -> bool:
    import shutil
    return bool(shutil.which("tesseract"))


def _has_homebrew() -> bool:
    import shutil
    return bool(shutil.which("brew"))


def _has_poppler() -> bool:
    import shutil
    return bool(shutil.which("pdftoppm"))


# ---------------------------------------------------------------------------
# macOS Installation
# ---------------------------------------------------------------------------

def _install_tesseract_mac_brew(
    status_label: ui.label,
    btn: ui.button,
    done_callback,
) -> None:
    """Tesseract über Homebrew installieren (im Hintergrund-Thread)."""
    btn.disable()
    status_label.set_text("⏳ Installiere Tesseract + deutsche Sprachdaten …")
    status_label.classes(add="text-amber-400", remove="text-red-400 text-green-400")

    def _run() -> None:
        try:
            proc = subprocess.run(
                ["brew", "install", "tesseract", "tesseract-lang"],
                capture_output=True, text=True, timeout=300,
            )
            if proc.returncode == 0 and _has_tesseract():
                status_label.set_text("✓ Tesseract erfolgreich installiert!")
                status_label.classes(add="text-green-400", remove="text-amber-400 text-red-400")
                ui.notify("Tesseract installiert ✓", type="positive")
                if done_callback:
                    done_callback()
            else:
                err = proc.stderr.strip()[:200]
                status_label.set_text(f"✗ Fehler: {err or 'Unbekannt'}")
                status_label.classes(add="text-red-400", remove="text-amber-400 text-green-400")
                btn.enable()
        except subprocess.TimeoutExpired:
            status_label.set_text("✗ Timeout — bitte manuell installieren")
            status_label.classes(add="text-red-400", remove="text-amber-400")
            btn.enable()
        except Exception as exc:
            status_label.set_text(f"✗ {exc}")
            status_label.classes(add="text-red-400", remove="text-amber-400")
            btn.enable()

    threading.Thread(target=_run, daemon=True).start()


def _install_homebrew_mac(status_label: ui.label, btn: ui.button) -> None:
    """Homebrew-Installationsseite im Browser öffnen."""
    webbrowser.open(_HOMEBREW_URL)
    status_label.set_text("Browser geöffnet → Homebrew installieren → App neu starten")
    status_label.classes(add="text-blue-400", remove="text-red-400")
    btn.disable()


# ---------------------------------------------------------------------------
# Windows Installation
# ---------------------------------------------------------------------------

def _download_tesseract_win(status_label: ui.label, btn: ui.button) -> None:
    """Tesseract-Installer herunterladen und starten."""
    import tempfile
    import urllib.request

    btn.disable()
    status_label.set_text("⏳ Lade Tesseract-Installer herunter … (ca. 40 MB)")
    status_label.classes(add="text-amber-400", remove="text-red-400 text-green-400")

    def _run() -> None:
        try:
            tmp_dir = Path(tempfile.gettempdir())
            installer = tmp_dir / "tesseract-installer.exe"

            urllib.request.urlretrieve(_TESSERACT_WIN_URL, installer)
            status_label.set_text("✓ Download fertig — Installer wird gestartet …")

            # Installer starten (Windows UAC-Dialog erscheint normal)
            os.startfile(str(installer))
            status_label.set_text("✓ Installer gestartet — bitte folge den Anweisungen, dann App neu starten")
            status_label.classes(add="text-green-400", remove="text-amber-400")

        except Exception as exc:
            status_label.set_text(f"✗ Download fehlgeschlagen: {exc}")
            status_label.classes(add="text-red-400", remove="text-amber-400")
            # Fallback: Browser öffnen
            webbrowser.open(_TESSERACT_WIN_URL)
            btn.enable()

    threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# Status-Check-Karte (wird in system.py eingebettet)
# ---------------------------------------------------------------------------

def build_dependency_card() -> None:
    """Karte mit Status aller Abhängigkeiten + Install-Buttons.

    Aufruf in system.py oder dashboard welcome screen.
    """
    tesseract_ok = _has_tesseract()
    poppler_ok   = _has_poppler()

    # Wenn alles OK → kompakte grüne Karte
    if tesseract_ok and poppler_ok:
        with ui.card().classes("ds-card w-full").style(
            "border:1px solid rgba(34,197,94,.3);background:rgba(34,197,94,.05)"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("check_circle").style("color:#22c55e;font-size:1.4rem")
                with ui.column().classes("gap-0"):
                    ui.label("Alle Abhängigkeiten vorhanden").style(
                        "font-weight:700;font-size:.95rem;color:#22c55e"
                    )
                    ui.label("Tesseract OCR ✓  ·  Poppler ✓  ·  App voll funktionsfähig").style(
                        "font-size:.78rem;color:#9CA3AF"
                    )
        return

    # Fehlende Abhängigkeiten → Hilfe-Karte
    with ui.card().classes("w-full").style(
        "border:1px solid rgba(245,158,11,.35);background:rgba(245,158,11,.05);"
        "border-radius:16px;padding:24px"
    ):
        with ui.row().classes("items-center gap-3 mb-4"):
            ui.icon("build_circle").style("font-size:1.6rem;color:#F59E0B")
            with ui.column().classes("gap-0"):
                ui.label("Abhängigkeiten einrichten").style(
                    "font-size:1rem;font-weight:700"
                )
                ui.label(
                    "Einige Funktionen benötigen zusätzliche Programme — "
                    "klicke auf Installieren."
                ).style("font-size:.8rem;color:#9CA3AF")

        # Tesseract
        if not tesseract_ok:
            _dep_row_tesseract()

        # Poppler
        if not poppler_ok:
            _dep_row_poppler()


def _dep_row_tesseract() -> None:
    """Eine Zeile für Tesseract mit Install-Button."""
    with ui.card().style(
        "background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);"
        "border-radius:12px;padding:16px;margin-bottom:12px"
    ):
        with ui.row().classes("items-start gap-4 w-full flex-wrap"):
            # Icon + Info
            with ui.column().classes("gap-1 flex-1"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("visibility").style("color:#F59E0B;font-size:1.1rem")
                    ui.label("Tesseract OCR").style("font-weight:700;font-size:.95rem")
                    ui.label("Fehlt").style(
                        "font-size:.65rem;font-weight:700;text-transform:uppercase;"
                        "background:rgba(239,68,68,.15);color:#EF4444;"
                        "border-radius:999px;padding:2px 8px"
                    )
                ui.label(
                    "Texterkennung auf gescannten Bildern und Fotos. "
                    "Ohne Tesseract werden Bild-Dokumente (JPG, PNG, TIFF) nicht ausgelesen."
                ).style("font-size:.78rem;color:#9CA3AF;line-height:1.6")

            # Install-Button (plattformabhängig)
            status = ui.label("").style("font-size:.78rem;margin-top:8px;width:100%")

            if _OS == "Darwin":
                if _has_homebrew():
                    btn = ui.button(
                        "Tesseract installieren",
                        icon="download",
                    ).classes("ds-btn-primary").props("size=sm")
                    btn.on("click", lambda b=btn, s=status: _install_tesseract_mac_brew(s, b, None))
                    ui.label("Wird via Homebrew installiert · keine Admin-Rechte nötig").style(
                        "font-size:.7rem;color:#64748B;margin-top:4px"
                    )
                else:
                    # Homebrew nicht da → erst Homebrew
                    btn_brew = ui.button(
                        "Homebrew installieren (Schritt 1)",
                        icon="open_in_browser",
                    ).classes("ds-btn-secondary").props("size=sm")
                    btn_brew.on("click", lambda b=btn_brew, s=status: _install_homebrew_mac(s, b))
                    ui.label(
                        "Danach: brew install tesseract tesseract-lang"
                    ).style("font-size:.7rem;color:#64748B;margin-top:4px")

            elif _OS == "Windows":
                btn_win = ui.button(
                    "Tesseract herunterladen & installieren",
                    icon="download",
                ).classes("ds-btn-primary").props("size=sm")
                btn_win.on("click", lambda b=btn_win, s=status: _download_tesseract_win(s, b))
                ui.label(
                    "Lädt den offiziellen Installer herunter (~40 MB) und startet ihn"
                ).style("font-size:.7rem;color:#64748B;margin-top:4px")

            else:
                ui.button(
                    "Anleitung öffnen", icon="open_in_browser",
                    on_click=lambda: webbrowser.open("https://tesseract-ocr.github.io/tessdoc/Installation.html"),
                ).classes("ds-btn-secondary").props("size=sm")

            ui.element("div").style("width:100%")
            status


def _dep_row_poppler() -> None:
    """Eine Zeile für Poppler mit Install-Button."""
    with ui.card().style(
        "background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);"
        "border-radius:12px;padding:16px"
    ):
        with ui.row().classes("items-start gap-4 w-full flex-wrap"):
            with ui.column().classes("gap-1 flex-1"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("picture_as_pdf").style("color:#F59E0B;font-size:1.1rem")
                    ui.label("Poppler").style("font-weight:700;font-size:.95rem")
                    ui.label("Fehlt").style(
                        "font-size:.65rem;font-weight:700;text-transform:uppercase;"
                        "background:rgba(239,68,68,.15);color:#EF4444;"
                        "border-radius:999px;padding:2px 8px"
                    )
                ui.label(
                    "PDF-zu-Bild-Konvertierung für OCR auf gescannten PDFs. "
                    "Einfache Text-PDFs funktionieren auch ohne Poppler."
                ).style("font-size:.78rem;color:#9CA3AF;line-height:1.6")

            status = ui.label("").style("font-size:.78rem;margin-top:8px;width:100%")

            if _OS == "Darwin":
                if _has_homebrew():
                    def _install_poppler(s=status) -> None:
                        s.set_text("⏳ Installiere Poppler …")
                        s.classes(add="text-amber-400")
                        def _run():
                            r = subprocess.run(["brew", "install", "poppler"], capture_output=True, timeout=180)
                            if r.returncode == 0:
                                s.set_text("✓ Poppler installiert!")
                                s.classes(add="text-green-400", remove="text-amber-400")
                            else:
                                s.set_text("✗ Fehler — versuche: brew install poppler")
                                s.classes(add="text-red-400", remove="text-amber-400")
                        threading.Thread(target=_run, daemon=True).start()

                    ui.button("Poppler installieren", icon="download", on_click=_install_poppler).classes("ds-btn-secondary").props("size=sm")
                else:
                    ui.label("brew install poppler").style(
                        "font-family:monospace;background:rgba(255,255,255,.06);"
                        "padding:4px 10px;border-radius:6px;font-size:.8rem"
                    )
            elif _OS == "Windows":
                ui.button(
                    "Download-Seite öffnen", icon="open_in_browser",
                    on_click=lambda: webbrowser.open(_POPPLER_WIN_URL),
                ).classes("ds-btn-secondary").props("size=sm")
                ui.label("ZIP entpacken → Ordner zu PATH hinzufügen").style(
                    "font-size:.7rem;color:#64748B;margin-top:4px"
                )
            else:
                ui.button(
                    "Anleitung", icon="open_in_browser",
                    on_click=lambda: webbrowser.open("https://poppler.freedesktop.org/"),
                ).classes("ds-btn-secondary").props("size=sm")

            ui.element("div").style("width:100%")
            status
