"""Watch Folder: Automatisch neue Dateien in der Inbox verarbeiten.

Nutzt watchdog zum Ueberwachen des Inbox-Ordners.
Bei neuen Dateien wird automatisch die Pipeline gestartet.

Features:
- Debouncing: Wartet kurz nach Dateiupload (fuer grosse Dateien)
- Configurable: Sofort oder gebatchtet
- Thread-safe: Laeuft als Background-Thread
- Integriert sich mit Dashboard
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Globaler Watcher-Status
_watcher_thread: threading.Thread | None = None
_watcher_running = False
_watcher_stop_event = threading.Event()
_processed_in_session: set[str] = set()
_session_lock = threading.Lock()          # Schutz fuer _processed_in_session


def _is_supported_file(file_path: Path, allowed_types: set[str]) -> bool:
    """Pruefen ob Dateityp unterstuetzt wird."""
    return file_path.suffix.lower() in allowed_types and file_path.is_file()


class InboxWatcher:
    """Ueberwacht einen Ordner auf neue Dateien und verarbeitet sie."""

    def __init__(
        self,
        inbox: Path,
        allowed_types: set[str],
        callback: Callable[[Path], None],
        debounce_seconds: float = 2.0,
        poll_interval: float = 5.0,
    ):
        self.inbox = inbox
        self.allowed_types = allowed_types
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.poll_interval = poll_interval
        self._known_files: dict[str, float] = {}  # path -> last_modified
        self._pending: dict[str, float] = {}  # path -> first_seen_time

    def scan_once(self) -> list[Path]:
        """Einmal den Ordner scannen und neue Dateien zurueckgeben."""
        if not self.inbox.exists():
            return []

        new_files = []
        current_files: dict[str, float] = {}

        for f in self.inbox.rglob("*"):
            if not _is_supported_file(f, self.allowed_types):
                continue

            key = str(f)
            try:
                mtime = f.stat().st_mtime
            except OSError:
                continue

            current_files[key] = mtime

            if key not in self._known_files:
                # Neue Datei entdeckt
                if key not in self._pending:
                    self._pending[key] = time.time()
                    logger.debug("Neue Datei entdeckt: %s (warte auf Debounce)", f.name)
                elif time.time() - self._pending[key] >= self.debounce_seconds:
                    # Debounce abgelaufen - Datei ist stabil
                    new_files.append(f)
                    del self._pending[key]
                    logger.info("Neue Datei bereit: %s", f.name)
            elif self._known_files[key] != mtime:
                # Datei wurde geaendert - erneut debounce
                self._pending[key] = time.time()

        self._known_files = current_files
        return new_files

    def process_new_files(self, files: list[Path]) -> int:
        """Neue Dateien ueber den Callback verarbeiten."""
        count = 0
        for f in files:
            key = str(f)
            with _session_lock:
                if key in _processed_in_session:
                    continue
            try:
                self.callback(f)
                with _session_lock:
                    _processed_in_session.add(key)
                count += 1
            except Exception as e:
                logger.error("Fehler bei Verarbeitung von %s: %s", f.name, e)
                # Datei NICHT als verarbeitet markieren → wird beim naechsten Scan erneut versucht
        return count


def start_watching(
    cfg: dict[str, Any],
    callback: Callable[[Path], None],
    poll_interval: float = 5.0,
    debounce_seconds: float = 2.0,
) -> bool:
    """Watcher starten (als Background-Thread).

    Args:
        cfg: Config-Dict
        callback: Funktion die pro neue Datei aufgerufen wird
        poll_interval: Sekunden zwischen Scans
        debounce_seconds: Warten nach Dateiupload

    Returns:
        True wenn gestartet, False wenn schon laeuft
    """
    global _watcher_thread, _watcher_running

    if _watcher_running:
        logger.warning("Watcher laeuft bereits")
        return False

    try:
        inbox = Path(cfg["paths"]["inbox"])
    except (KeyError, TypeError) as exc:
        logger.error("Watcher: Inbox-Pfad fehlt in Config: %s", exc)
        return False

    allowed = set(cfg.get("file_types", [".pdf"]))

    watcher = InboxWatcher(
        inbox=inbox,
        allowed_types=allowed,
        callback=callback,
        debounce_seconds=debounce_seconds,
        poll_interval=poll_interval,
    )

    # Initial-Scan: Bestehende Dateien merken (nicht verarbeiten)
    # Nur einmal scannen — scan_once() wuerde denselben rglob nochmal ausfuehren
    _known: dict[str, float] = {}
    for _f in inbox.rglob("*"):
        if _is_supported_file(_f, allowed):
            try:
                _known[str(_f)] = _f.stat().st_mtime
            except OSError:
                pass  # Datei zwischen rglob und stat() geloescht → ueberspringen
    watcher._known_files = _known

    _watcher_stop_event.clear()
    _watcher_running = True

    def _watch_loop() -> None:
        global _watcher_running
        logger.info("Watcher gestartet fuer: %s (Poll: %.1fs, Debounce: %.1fs)",
                     inbox, poll_interval, debounce_seconds)
        try:
            while not _watcher_stop_event.is_set():
                new = watcher.scan_once()
                if new:
                    count = watcher.process_new_files(new)
                    if count:
                        logger.info("Watcher: %d neue Dateien verarbeitet", count)
                _watcher_stop_event.wait(poll_interval)
        except Exception as e:
            logger.error("Watcher-Fehler: %s", e)
        finally:
            _watcher_running = False
            logger.info("Watcher gestoppt")

    _watcher_thread = threading.Thread(target=_watch_loop, daemon=True, name="inbox-watcher")
    _watcher_thread.start()
    return True


def stop_watching() -> bool:
    """Watcher stoppen.

    Returns:
        True wenn gestoppt, False wenn nicht lief
    """
    global _watcher_running, _watcher_thread

    if not _watcher_running:
        return False

    _watcher_stop_event.set()
    if _watcher_thread:
        joined = _watcher_thread
        _watcher_thread = None
        joined.join(timeout=10)
        if joined.is_alive():
            logger.warning("Watcher-Thread hat nach 10s nicht beendet")
    _watcher_running = False
    with _session_lock:
        _processed_in_session.clear()
    logger.info("Watcher gestoppt")
    return True


def is_watching() -> bool:
    """Ist der Watcher aktiv?"""
    return _watcher_running


def get_watcher_status() -> dict[str, Any]:
    """Status-Info fuer Dashboard."""
    return {
        "running": _watcher_running,
        "files_processed": len(_processed_in_session),
    }
