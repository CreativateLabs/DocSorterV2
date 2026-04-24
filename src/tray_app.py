"""Doc-Sorter Menuleisten-App (macOS rumps-basiert).

Startet ein Icon in der Menuleiste mit:
  - Aktueller Inbox-/Review-Count (alle 30s aktualisiert)
  - Schnellzugriff auf Dashboard (oeffnet Browser/PyWebView)
  - Starten/Stoppen der automatischen Verarbeitung (Watcher)
  - Anzeige aktiver Alerts

Nutzung:
    python -m src.tray_app
    python -m src.tray_app --port 1991

Fuer Autostart: LaunchAgent-Plist kann eingerichtet werden,
siehe scripts/install-tray-autostart.sh
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from threading import Thread

try:
    import rumps  # type: ignore[import]
    _RUMPS_AVAILABLE = True
except ImportError:
    rumps = None  # type: ignore[assignment]
    _RUMPS_AVAILABLE = False

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DASHBOARD_PY = _PROJECT_ROOT / "dashboard.py"

# Default-Port, kann ueber DOCSORTER_PORT ueberschrieben werden
_DEFAULT_PORT = int(os.environ.get("DOCSORTER_PORT", "1991"))


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _get_stats() -> dict:
    """Stats aus der Config + Dateisystem lesen."""
    try:
        sys.path.insert(0, str(_PROJECT_ROOT))
        from src.config import get_file_types, load_config  # noqa: WPS433
    except Exception as exc:
        logger.debug("Config-Import fehlgeschlagen: %s", exc)
        return {"inbox": 0, "review": 0, "alerts": 0, "ok": False}

    try:
        cfg = load_config()
        inbox = Path(cfg["paths"]["inbox"])
        review = Path(cfg["paths"].get("review", str(Path(cfg["paths"]["archive"]) / "_review")))
        allowed = get_file_types(cfg)

        inbox_count = 0
        if inbox.exists():
            inbox_count = sum(
                1 for f in inbox.rglob("*")
                if f.is_file() and f.suffix.lower() in allowed
            )

        review_count = 0
        if review.exists():
            review_count = sum(1 for f in review.rglob("*") if f.is_file())

        alerts_count = 0
        try:
            from src.alerts import get_active_alerts  # noqa: WPS433
            alerts_count = len(get_active_alerts())
        except Exception:
            pass

        return {
            "inbox": inbox_count,
            "review": review_count,
            "alerts": alerts_count,
            "ok": True,
        }
    except Exception as exc:
        logger.debug("Stats-Fehler: %s", exc)
        return {"inbox": 0, "review": 0, "alerts": 0, "ok": False}


def _is_dashboard_running(port: int) -> bool:
    """Prueft ob Dashboard auf dem Port laeuft."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            s.connect(("127.0.0.1", port))
            return True
    except (OSError, socket.timeout):
        return False


def _format_title(stats: dict) -> str:
    """Kompakter Titel fuer die Menuleiste."""
    if not stats["ok"]:
        return "DS \u2014"
    parts = []
    if stats["inbox"] > 0:
        parts.append(f"\u2709{stats['inbox']}")
    if stats["review"] > 0:
        parts.append(f"?{stats['review']}")
    if stats["alerts"] > 0:
        parts.append(f"!{stats['alerts']}")
    if not parts:
        return "DS"
    return "DS " + " ".join(parts)


# ---------------------------------------------------------------------------
# Tray-App
# ---------------------------------------------------------------------------

# Conditional base class: rumps.App wenn verfuegbar, sonst object.
# So kann das Modul importiert werden (z.B. fuer Tests auf Linux-CI) ohne rumps.
_RumpsApp = rumps.App if _RUMPS_AVAILABLE else object
_rumps_timer = rumps.timer if _RUMPS_AVAILABLE else (lambda *_a, **_kw: lambda f: f)


class DocSorterTray(_RumpsApp):
    """Menuleisten-App fuer Doc-Sorter."""

    def __init__(self, port: int = _DEFAULT_PORT) -> None:
        if not _RUMPS_AVAILABLE:
            raise RuntimeError(
                "rumps ist nicht installiert. 'pip install rumps' oder auf "
                "Nicht-macOS-System: Tray-App ist nur fuer macOS verfuegbar."
            )
        super().__init__("DS", quit_button=None)
        self.port = port
        self.dashboard_proc: subprocess.Popen | None = None
        self._stats: dict = {"inbox": 0, "review": 0, "alerts": 0, "ok": False}

        # Menu
        self.item_stats = rumps.MenuItem("Lade \u2026")
        self.item_stats.set_callback(None)

        self.item_open = rumps.MenuItem("Dashboard \u00f6ffnen", callback=self.open_dashboard)
        self.item_start = rumps.MenuItem("Dashboard starten", callback=self.start_dashboard)
        self.item_stop = rumps.MenuItem("Dashboard stoppen", callback=self.stop_dashboard)

        self.item_process = rumps.MenuItem("Jetzt sortieren (Live)", callback=self.run_sort)
        self.item_preview = rumps.MenuItem("Vorschau (Dry Run)", callback=self.run_preview)

        self.item_quit = rumps.MenuItem("Beenden", callback=self.quit_app)

        self.menu = [
            self.item_stats,
            None,
            self.item_open,
            self.item_start,
            self.item_stop,
            None,
            self.item_preview,
            self.item_process,
            None,
            self.item_quit,
        ]

        self._refresh_menu_state()

    # ------------------------------------------------------------------
    # Menu-State
    # ------------------------------------------------------------------

    def _refresh_menu_state(self) -> None:
        running = _is_dashboard_running(self.port)
        self.item_open.set_callback(self.open_dashboard if running else None)
        self.item_start.set_callback(None if running else self.start_dashboard)
        self.item_stop.set_callback(self.stop_dashboard if running else None)

        status = f"Inbox: {self._stats['inbox']} \u00b7 Pr\u00fcfung: {self._stats['review']} \u00b7 Alerts: {self._stats['alerts']}"
        if not self._stats["ok"]:
            status = "Config nicht geladen"
        if running:
            status = f"\u2713 L\u00e4uft auf Port {self.port} \u2014 {status}"
        else:
            status = f"Gestoppt \u2014 {status}"
        self.item_stats.title = status

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def open_dashboard(self, _sender) -> None:
        webbrowser.open(f"http://127.0.0.1:{self.port}/")

    def start_dashboard(self, _sender) -> None:
        if self.dashboard_proc and self.dashboard_proc.poll() is None:
            rumps.notification("Doc-Sorter", "Dashboard l\u00e4uft bereits", "")
            return
        python = sys.executable
        env = os.environ.copy()
        env["DOCSORTER_PORT"] = str(self.port)
        self.dashboard_proc = subprocess.Popen(
            [python, str(_DASHBOARD_PY)],
            cwd=str(_PROJECT_ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        rumps.notification("Doc-Sorter", "Dashboard startet ...", f"Port {self.port}")
        # Nach 3s Menu refreshen
        Thread(target=self._delayed_refresh, args=(3,), daemon=True).start()

    def stop_dashboard(self, _sender) -> None:
        if self.dashboard_proc and self.dashboard_proc.poll() is None:
            self.dashboard_proc.terminate()
            try:
                self.dashboard_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.dashboard_proc.kill()
            self.dashboard_proc = None
            rumps.notification("Doc-Sorter", "Dashboard gestoppt", "")
        else:
            # Evtl. extern gestarteter Prozess \u2014 via Port-Signal
            rumps.notification("Doc-Sorter", "Kein vom Tray gestartetes Dashboard gefunden", "")
        self._refresh_menu_state()

    def run_sort(self, _sender) -> None:
        self._run_main(live=True)

    def run_preview(self, _sender) -> None:
        self._run_main(live=False)

    def _run_main(self, live: bool) -> None:
        main_py = _PROJECT_ROOT / "main.py"
        cmd = [sys.executable, str(main_py), "--live" if live else "--dry-run"]
        proc = subprocess.Popen(cmd, cwd=str(_PROJECT_ROOT))
        mode = "Live-Sortierung" if live else "Vorschau"
        rumps.notification("Doc-Sorter", f"{mode} gestartet", "PID %d" % proc.pid)

    def quit_app(self, _sender) -> None:
        if self.dashboard_proc and self.dashboard_proc.poll() is None:
            self.dashboard_proc.terminate()
        rumps.quit_application()

    # ------------------------------------------------------------------
    # Timer
    # ------------------------------------------------------------------

    @_rumps_timer(30)
    def tick(self, _sender) -> None:
        """Alle 30s Stats aktualisieren."""
        self._stats = _get_stats()
        self.title = _format_title(self._stats)
        self._refresh_menu_state()

    def _delayed_refresh(self, seconds: int) -> None:
        time.sleep(seconds)
        self._stats = _get_stats()
        self.title = _format_title(self._stats)
        self._refresh_menu_state()


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    if not _RUMPS_AVAILABLE:
        print(
            "rumps nicht installiert. Bitte 'pip install rumps' ausfuehren.\n"
            "Tray-App ist nur fuer macOS verfuegbar.",
            file=sys.stderr,
        )
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser(description="Doc-Sorter Tray")
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT)
    args = parser.parse_args()

    # Ignoriere Ctrl-C sauber
    signal.signal(signal.SIGINT, lambda *_a: sys.exit(0))

    app = DocSorterTray(port=args.port)
    app.run()


if __name__ == "__main__":
    main()
