#!/usr/bin/env python3
"""Doc-Sorter MVP Dashboard -- NiceGUI entry point.

Entwicklungsmodus (Browser):
  python dashboard.py

Desktop-App (natives Fenster):
  python dashboard.py --native
  oder: DOCSORTER_NATIVE=1 python dashboard.py

Im PyInstaller-Bundle wird automatisch der native Modus verwendet.
"""

from __future__ import annotations

import multiprocessing
import os
import secrets
import socket
import sys
from pathlib import Path

from src.dashboard.layout import build_layout
from src.single_instance import ensure_single_instance
from src.startup_check import run_all_checks, has_critical_failure
from src.version import __version__

from nicegui import ui


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _find_free_port(start: int = 8080, end: int = 8200) -> int:
    """Freien TCP-Port im angegebenen Bereich finden."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start  # Fallback: PyWebView öffnet trotzdem


def _load_storage_secret() -> str:
    """Storage-Secret laden oder generieren.

    Reihenfolge:
    1. Umgebungsvariable DOCSORTER_SECRET
    2. ~/.docsorter_secret Datei (persistent über Neustarts)
    3. Neues Secret generieren und in Datei speichern
    """
    # 1. Env-Variable
    env_secret = os.environ.get("DOCSORTER_SECRET")
    if env_secret:
        return env_secret

    # 2. Persistente Secret-Datei
    secret_file = Path.home() / ".docsorter_secret"
    if secret_file.exists():
        try:
            secret = secret_file.read_text(encoding="utf-8").strip()
            if len(secret) >= 32:
                return secret
        except OSError:
            pass

    # 3. Neu generieren und speichern
    secret = secrets.token_hex(32)
    try:
        secret_file.write_text(secret, encoding="utf-8")
        secret_file.chmod(0o600)  # Nur für Besitzer lesbar (Unix)
    except OSError:
        pass  # Windows: chmod ohne Effekt, aber kein Fehler
    return secret


def _is_native_mode() -> bool:
    """Wird das Dashboard als natives Desktop-Fenster gestartet?"""
    if getattr(sys, "frozen", False):
        return True  # PyInstaller-Bundle → immer nativ
    if os.environ.get("DOCSORTER_NATIVE", "").lower() in ("1", "true", "yes"):
        return True
    if "--native" in sys.argv:
        return True
    return False


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    native = _is_native_mode()
    is_dev = not native and not getattr(sys, "frozen", False)

    # Startup-Checks (non-blocking — Warnungen erscheinen in-app)
    checks = run_all_checks()
    _missing = [c for c in checks if not c.ok and not c.critical]
    _critical = has_critical_failure(checks)

    if _critical:
        # Kritischer Fehler (z.B. Python < 3.10) → Abbruch mit Meldung
        import sys as _sys
        from src.startup_check import format_summary
        print("\n❌ Doc-Sorter kann nicht gestartet werden:\n")
        print(format_summary(checks))
        _sys.exit(1)

    build_layout()

    # Einmalige Benachrichtigung wenn nicht-kritische Deps fehlen
    if _missing:
        missing_names = ", ".join(c.name for c in _missing)

        @ui.on_startup  # type: ignore[misc]
        async def _notify_missing() -> None:  # noqa: F811
            ui.notify(
                f"⚠ Nicht installiert: {missing_names} — "
                "unter System-Status einrichten",
                type="warning",
                timeout=8000,
                position="top",
                actions=[{"label": "Einrichten", "color": "white",
                          "handler": lambda: ui.navigate.to("/system")}],
            )

    port = _find_free_port() if native else int(os.environ.get("DOCSORTER_PORT", "8080"))
    secret = _load_storage_secret()

    ui.run(
        title=f"Doc-Sorter {__version__}",
        port=port,
        reload=is_dev,          # Nur im Dev-Modus: Auto-Reload
        native=native,          # Natives Fenster (PyWebView) im App-Modus
        window_size=(1280, 800),
        fullscreen=False,
        dark=None,              # System-Default (Auto-Dark-Mode)
        favicon="🗂️",
        storage_secret=secret,
        show=not native,        # Im nativen Modus übernimmt PyWebView das Öffnen
    )


if __name__ in {"__main__", "__mp_main__"}:
    # Pflicht für PyInstaller + multiprocessing: verhindert rekursives Spawnen
    multiprocessing.freeze_support()

    # Single-Instance-Schutz NUR im echten Haupt-Prozess.
    # NiceGUI spawnt intern Subprozesse (Server, PyWebView-Fenster).
    # Diese haben zwar __name__ == "__main__" im frozen Bundle, aber
    # multiprocessing.current_process().name ist nur im Original "MainProcess".
    if multiprocessing.current_process().name == "MainProcess":
        if not ensure_single_instance():
            print("Doc-Sorter läuft bereits — bringing existing window to front.")
            sys.exit(0)

    main()
