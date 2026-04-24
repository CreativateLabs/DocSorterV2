"""Terminal-Seite: Jobs starten und Live-Output streamen.

UI Design Overhaul: Benutzerfreundliche Sprache, crisp Buttons, Dark-Terminal.
- "Dry Run" -> "Vorschau"
- "Live Run" -> "Jetzt sortieren"
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

from nicegui import ui

from ..theme import callout, page_header

# Projekt-Root (doc-sorter-mvp/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_MAIN_PY = _PROJECT_ROOT / "main.py"

# Globaler Job-State
_running = False
_current_proc: asyncio.subprocess.Process | None = None

# Regex um Fortschritt [X/Y] aus main.py-Ausgabe zu parsen
_PROGRESS_RE = re.compile(r"\[(\d+)/(\d+)\]")
# Regex fuer "Verarbeitet: N" / "Review: N" aus Zusammenfassung
_COUNT_RE = re.compile(r"(\d+)\s+(?:Dateien|Dokument)", re.IGNORECASE)


def _set_buttons_enabled(buttons: list[ui.button], enabled: bool) -> None:
    for btn in buttons:
        if enabled:
            btn.enable()
        else:
            btn.disable()


async def _run_job(
    log_widget: ui.log,
    mode: str,
    action_buttons: list[ui.button],
    stop_button: ui.button,
    status_box: "StatusBox",
) -> None:
    """main.py als Subprocess starten und Output live streamen."""
    global _running, _current_proc
    if _running:
        log_widget.push(">>> Ein Job laeuft bereits. Bitte warten.")
        return

    _running = True
    _set_buttons_enabled(action_buttons, False)
    stop_button.enable()

    mode_label = {
        "dry-run": "Vorschau",
        "live":    "Jetzt sortieren",
        "undo":    "R\u00fcckg\u00e4ngig",
    }.get(mode, mode)
    status_box.set_running(mode_label)

    python = sys.executable
    cmd = [python, str(_MAIN_PY)]
    if mode == "dry-run":
        cmd.append("--dry-run")
    elif mode == "live":
        cmd.append("--live")
    elif mode == "undo":
        cmd.append("--undo")

    log_widget.push(f">>> Starte: {mode_label} ({' '.join(cmd)})")
    log_widget.push("")

    try:
        _current_proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(_PROJECT_ROOT),
        )

        while True:
            line = await _current_proc.stdout.readline()
            if not line:
                break
            decoded = line.decode("utf-8", errors="replace").rstrip()
            log_widget.push(decoded)
            # Fortschritt extrahieren
            m = _PROGRESS_RE.search(decoded)
            if m:
                status_box.set_progress(int(m.group(1)), int(m.group(2)), decoded)

        await _current_proc.wait()
        log_widget.push("")
        code = _current_proc.returncode
        if code == 0:
            status_box.set_success(mode_label)
            log_widget.push(">>> \u2713 Erfolgreich abgeschlossen")
        else:
            status_box.set_error(f"Fehler (Code {code})")
            log_widget.push(f">>> Fehler (Code {code})")
    except asyncio.CancelledError:
        status_box.set_cancelled()
        log_widget.push(">>> Job abgebrochen.")
    except Exception as e:
        status_box.set_error(str(e))
        log_widget.push(f">>> FEHLER: {e}")
    finally:
        _running = False
        _current_proc = None
        _set_buttons_enabled(action_buttons, True)
        stop_button.disable()


async def _stop_job(log_widget: ui.log) -> None:
    global _current_proc
    if _current_proc and _current_proc.returncode is None:
        log_widget.push(">>> Stoppe laufenden Job...")
        _current_proc.terminate()
        try:
            await asyncio.wait_for(_current_proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            _current_proc.kill()
            log_widget.push(">>> Job beendet (Timeout).")


class StatusBox:
    """Status-Panel oberhalb des Terminals mit Spinner, Progress und Success/Error."""

    def __init__(self) -> None:
        self._container = ui.element("div").style(
            "width:100%;padding:12px 16px;border-radius:12px;margin-bottom:12px;"
            "background:rgba(148,163,184,0.06);border:1px solid rgba(148,163,184,0.15);"
            "transition:all 0.3s ease"
        )
        self._icon: ui.icon | None = None
        self._title: ui.label | None = None
        self._detail: ui.label | None = None
        self._progress: ui.linear_progress | None = None
        self.set_idle()

    def _rebuild(
        self,
        *,
        icon: str,
        icon_color: str,
        title: str,
        detail: str,
        bg: str,
        border: str,
        progress: float | None = None,
    ) -> None:
        self._container.clear()
        self._container.style(
            f"width:100%;padding:12px 16px;border-radius:12px;margin-bottom:12px;"
            f"background:{bg};border:1px solid {border};transition:all 0.3s ease"
        )
        with self._container:
            with ui.row().classes("items-center gap-3 w-full"):
                self._icon = ui.icon(icon).style(
                    f"font-size:1.4rem;color:{icon_color};flex-shrink:0"
                )
                with ui.column().classes("gap-0 flex-1"):
                    self._title = ui.label(title).style(
                        "font-size:0.95rem;font-weight:700;color:var(--ds-text)"
                    )
                    self._detail = ui.label(detail).style(
                        "font-size:0.75rem;color:var(--ds-text-2)"
                    )
            if progress is not None:
                self._progress = ui.linear_progress(
                    value=progress, show_value=False,
                ).props("rounded").style("margin-top:8px;height:6px")

    def set_idle(self) -> None:
        self._rebuild(
            icon="play_circle_outline", icon_color="#94a3b8",
            title="Bereit", detail="W\u00e4hle eine Aktion unten \u2014 Vorschau, Jetzt sortieren oder R\u00fcckg\u00e4ngig.",
            bg="rgba(148,163,184,0.06)", border="rgba(148,163,184,0.15)",
        )

    def set_running(self, mode: str) -> None:
        self._rebuild(
            icon="hourglass_top", icon_color="#00d4ff",
            title=f"{mode} l\u00e4uft \u2026",
            detail="Bitte warten. Der Fortschritt erscheint im Terminal unten.",
            bg="rgba(0,212,255,0.08)", border="rgba(0,212,255,0.35)",
            progress=0.0,
        )

    def set_progress(self, current: int, total: int, line: str) -> None:
        frac = current / total if total > 0 else 0
        short = line.strip()[:80] + ("\u2026" if len(line) > 80 else "")
        self._rebuild(
            icon="sync", icon_color="#00d4ff",
            title=f"Verarbeite Datei {current} von {total}",
            detail=short,
            bg="rgba(0,212,255,0.08)", border="rgba(0,212,255,0.35)",
            progress=frac,
        )

    def set_success(self, mode: str) -> None:
        self._rebuild(
            icon="check_circle", icon_color="#00e87d",
            title=f"\u2713 {mode} erfolgreich abgeschlossen",
            detail="Details im Terminal. Ge\u00e4nderte Dokumente siehst du in \u00dcbersicht oder Pr\u00fcfung.",
            bg="rgba(0,232,125,0.08)", border="rgba(0,232,125,0.35)",
        )

    def set_error(self, msg: str) -> None:
        self._rebuild(
            icon="error", icon_color="#ff3366",
            title="Fehler beim Ausf\u00fchren",
            detail=msg[:200],
            bg="rgba(255,51,102,0.08)", border="rgba(255,51,102,0.35)",
        )

    def set_cancelled(self) -> None:
        self._rebuild(
            icon="cancel", icon_color="#ff9f0a",
            title="Job abgebrochen",
            detail="Der laufende Vorgang wurde gestoppt.",
            bg="rgba(255,159,10,0.08)", border="rgba(255,159,10,0.35)",
        )


def build() -> None:
    """Terminal-Seite aufbauen mit modernem Design."""
    page_header(
        "Terminal",
        "Dokumente verarbeiten und Live-Ausgabe beobachten.",
    )

    # Hilfe-Callout
    callout(
        "Starte eine <strong>Vorschau</strong> um zu sehen was passiert, "
        "ohne Dateien zu verschieben. Dann <strong>Jetzt sortieren</strong> "
        "fuer die echte Verarbeitung.",
        "info",
    )

    ui.html('<div style="height:12px"></div>', sanitize=False)

    # Status-Panel
    status_box = StatusBox()

    # Terminal Log
    log_output = ui.log(max_lines=500).classes("w-full h-[440px] ds-terminal")
    log_output.push("Bereit. Waehle eine Aktion:")
    log_output.push("")

    action_buttons: list[ui.button] = []

    # Action-Buttons
    with ui.row().classes("gap-3 mt-4"):
        btn_dry = ui.button(
            "Vorschau",
            on_click=lambda: _run_job(log_output, "dry-run", action_buttons, btn_stop, status_box),
            icon="visibility",
        ).classes("ds-btn-primary").tooltip(
            "Zeigt was passieren wuerde, ohne Dateien zu verschieben"
        )
        action_buttons.append(btn_dry)

        btn_live = ui.button(
            "Jetzt sortieren",
            on_click=lambda: _run_job(log_output, "live", action_buttons, btn_stop, status_box),
            icon="play_arrow",
        ).classes("ds-btn-success").tooltip(
            "Dateien verarbeiten und ins Archiv verschieben"
        )
        action_buttons.append(btn_live)

        btn_undo = ui.button(
            "Rueckgaengig",
            on_click=lambda: _run_job(log_output, "undo", action_buttons, btn_stop, status_box),
            icon="undo",
        ).classes("ds-btn-warning").tooltip(
            "Letzte Verschiebung rueckgaengig machen"
        )
        action_buttons.append(btn_undo)

        btn_stop = ui.button(
            "Stoppen",
            on_click=lambda: _stop_job(log_output),
            icon="stop",
        ).classes("ds-btn-danger").tooltip("Laufenden Job abbrechen")
        btn_stop.disable()

        ui.button(
            "Ausgabe leeren",
            on_click=lambda: log_output.clear(),
            icon="delete_sweep",
        ).classes("ds-btn-ghost").tooltip("Terminal-Ausgabe leeren")
