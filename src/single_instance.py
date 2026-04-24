"""Single-Instance-Schutz: verhindert dass Doc-Sorter zweimal läuft.

Strategie:
  1. Lock-File mit PID erstellen (plattformübergreifend)
  2. Port-Bind als zweite Absicherung
  3. Bei bereits laufender Instanz: Fenster in den Vordergrund bringen

Verwendung:
    from src.single_instance import SingleInstance

    guard = SingleInstance()
    if not guard.acquire():
        guard.focus_existing()
        sys.exit(0)          # Graceful exit — andere Instanz läuft schon
    # ... App starten ...
    # Am Ende: guard.release() (oder as Context-Manager)
"""

from __future__ import annotations

import logging
import os
import platform
import signal
import socket
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_APP_NAME  = "DocSorter"
_LOCK_PORT = 47832   # Fester Port nur für Instance-Check (nicht der App-Port)


def _lock_file_path() -> Path:
    """Plattformspezifischer Pfad für die Lock-Datei."""
    if platform.system() == "Windows":
        base = Path(os.environ.get("TEMP") or tempfile.gettempdir())
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support" / _APP_NAME
        base.mkdir(parents=True, exist_ok=True)
    else:
        base = Path(tempfile.gettempdir())
    return base / f"{_APP_NAME}.lock"


def _read_lock_pid(lock: Path) -> int | None:
    """PID aus Lock-Datei lesen. None wenn nicht lesbar oder ungültig."""
    try:
        text = lock.read_text(encoding="utf-8").strip()
        return int(text)
    except (OSError, ValueError):
        return None


def _pid_running(pid: int) -> bool:
    """Prüft ob ein Prozess mit dieser PID läuft."""
    if pid <= 0:
        return False
    try:
        if platform.system() == "Windows":
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)   # Signal 0 = nur prüfen, nicht senden
            return True
    except (OSError, ProcessLookupError):
        return False


def _bind_lock_port() -> socket.socket | None:
    """Versucht, den Lock-Port zu binden. None = bereits belegt (andere Instanz)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        s.bind(("127.0.0.1", _LOCK_PORT))
        s.listen(1)
        return s
    except OSError:
        return None


class SingleInstance:
    """Verhindert mehrfache gleichzeitige Instanzen von Doc-Sorter."""

    def __init__(self) -> None:
        self._lock_file = _lock_file_path()
        self._sock: socket.socket | None = None
        self._acquired = False

    def acquire(self) -> bool:
        """Lock erwerben. True = wir sind die erste Instanz, darf starten.
           False = andere Instanz läuft bereits."""

        # ── 1. Port-Check (schnellste Methode) ──────────────────────────
        sock = _bind_lock_port()
        if sock is None:
            logger.info("Lock-Port %d belegt — andere Instanz läuft", _LOCK_PORT)
            return False

        # ── 2. Lock-File-Check (Backup für Port-Kollisionen) ─────────────
        if self._lock_file.exists():
            existing_pid = _read_lock_pid(self._lock_file)
            if existing_pid and _pid_running(existing_pid):
                logger.info(
                    "Lock-Datei gefunden, Prozess %d läuft — andere Instanz aktiv",
                    existing_pid,
                )
                sock.close()
                return False
            else:
                # Stale Lock (Crash ohne Cleanup) → überschreiben
                logger.debug("Stale Lock-Datei gefunden (PID %s) — bereinige", existing_pid)

        # ── 3. Lock erwerben ────────────────────────────────────────────
        try:
            self._lock_file.write_text(str(os.getpid()), encoding="utf-8")
        except OSError as exc:
            logger.warning("Konnte Lock-Datei nicht schreiben: %s", exc)

        self._sock = sock
        self._acquired = True
        logger.debug("Single-Instance-Lock erworben (PID %d)", os.getpid())
        return True

    def release(self) -> None:
        """Lock freigeben (beim App-Ende aufrufen)."""
        if not self._acquired:
            return
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        try:
            if self._lock_file.exists():
                pid = _read_lock_pid(self._lock_file)
                if pid == os.getpid():   # Nur unsere eigene Lock-Datei löschen
                    self._lock_file.unlink(missing_ok=True)
        except OSError:
            pass
        self._acquired = False
        logger.debug("Single-Instance-Lock freigegeben")

    def focus_existing(self) -> None:
        """Versucht das Fenster der bereits laufenden Instanz in den Vordergrund zu bringen."""
        system = platform.system()
        try:
            if system == "Darwin":
                # macOS: AppleScript
                import subprocess
                subprocess.run(
                    ["osascript", "-e",
                     f'tell application "{_APP_NAME}" to activate'],
                    capture_output=True, timeout=3,
                )
            elif system == "Windows":
                # Windows: SetForegroundWindow via win32gui
                try:
                    import win32gui, win32con  # type: ignore[import]
                    def _enum(hwnd, _):
                        if win32gui.IsWindowVisible(hwnd):
                            title = win32gui.GetWindowText(hwnd)
                            if _APP_NAME.lower() in title.lower():
                                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                                win32gui.SetForegroundWindow(hwnd)
                    win32gui.EnumWindows(_enum, None)
                except ImportError:
                    pass   # pywin32 nicht installiert — kein Fokus möglich
        except Exception as exc:
            logger.debug("Focus-Existing fehlgeschlagen: %s", exc)

    # Context-Manager-Support
    def __enter__(self) -> "SingleInstance":
        return self

    def __exit__(self, *_) -> None:
        self.release()


# ── Globale Instanz ──────────────────────────────────────────────────────
_guard: SingleInstance | None = None


def ensure_single_instance() -> bool:
    """Singleton-Einstiegspunkt.

    Aufruf in dashboard.py vor dem Start.
    Gibt True zurück wenn diese Instanz starten darf,
    False wenn bereits eine andere läuft (diese Instanz soll beenden).
    """
    global _guard
    _guard = SingleInstance()
    if _guard.acquire():
        import atexit
        atexit.register(_guard.release)
        return True
    else:
        _guard.focus_existing()
        return False
