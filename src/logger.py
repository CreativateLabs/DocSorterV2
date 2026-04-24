"""Logging, State-Management und Undo-Funktionalitaet.

State-Datei (_state.json) mit File-Locking und atomarem Schreiben.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

# File-Locking: fcntl ist nur auf Unix/macOS verfuegbar
if sys.platform != "win32":
    import fcntl as _fcntl
    def _lock(f: object) -> None:
        _fcntl.flock(f.fileno(), _fcntl.LOCK_EX)  # type: ignore[attr-defined]
    def _unlock(f: object) -> None:
        _fcntl.flock(f.fileno(), _fcntl.LOCK_UN)  # type: ignore[attr-defined]
else:
    # Windows: Kein fcntl — atomares Schreiben via tempfile + os.replace reicht
    def _lock(f: object) -> None:   # type: ignore[misc]
        pass
    def _unlock(f: object) -> None:  # type: ignore[misc]
        pass

from .classifier import Classification

logger = logging.getLogger(__name__)


def file_hash(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """SHA-256 Hash einer Datei berechnen (fuer Idempotenz)."""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class StateManager:
    """Verwaltet den State (welche Dateien schon verarbeitet wurden).

    Features:
    - File-Locking (fcntl) gegen gleichzeitige Zugriffe
    - Atomares Schreiben (temp file + rename)
    - Automatisches Backup vor jedem Speichern
    """

    def __init__(self, state_path: Path):
        self.state_path = state_path
        self._state = self._load()

    def _load(self) -> dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("State-Datei korrupt, versuche Backup...")
                return self._try_recover()
            except OSError as e:
                logger.error("State-Datei nicht lesbar: %s", e)
        return {"processed": {}, "version": 2}

    def _try_recover(self) -> dict[str, Any]:
        """Versuche State aus Backup wiederherzustellen."""
        backup = self.state_path.with_suffix(".json.bak")
        if backup.exists():
            try:
                state = json.loads(backup.read_text(encoding="utf-8"))
                logger.info("State aus Backup wiederhergestellt")
                return state
            except (json.JSONDecodeError, OSError):
                logger.error("Backup ebenfalls korrupt")
        return {"processed": {}, "version": 2}

    def save(self) -> None:
        """State atomar speichern mit Locking und Backup."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        # Backup erstellen (wenn State-Datei existiert)
        if self.state_path.exists():
            backup = self.state_path.with_suffix(".json.bak")
            try:
                shutil.copy2(str(self.state_path), str(backup))
            except OSError:
                logger.warning("Backup konnte nicht erstellt werden")

        # Atomares Schreiben: temp file + rename
        content = json.dumps(self._state, ensure_ascii=False, indent=2)
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self.state_path.parent),
                suffix=".tmp",
                prefix=".state_",
            )
            try:
                with open(fd, "w", encoding="utf-8") as f:
                    _lock(f)
                    f.write(content)
                    f.flush()
                    _unlock(f)
                # Atomic rename (os.replace ist auf allen Plattformen atomar)
                os.replace(tmp_path, self.state_path)
            except Exception:
                Path(tmp_path).unlink(missing_ok=True)
                raise
        except OSError as e:
            logger.error("State konnte nicht gespeichert werden: %s", e)
            # Fallback: atomic write in selben Ordner
            try:
                import tempfile
                tmp_fd2, tmp_path2 = tempfile.mkstemp(
                    dir=self.state_path.parent, suffix=".tmp"
                )
                try:
                    with os.fdopen(tmp_fd2, "w", encoding="utf-8") as f2:
                        f2.write(content)
                    os.replace(tmp_path2, self.state_path)
                except Exception:
                    Path(tmp_path2).unlink(missing_ok=True)
                    raise
            except Exception as e2:
                logger.error("State-Fallback fehlgeschlagen: %s", e2)

    def is_processed(self, sha256: str) -> bool:
        return sha256 in self._state.get("processed", {})

    def mark_processed(self, sha256: str, source: str, destination: str, log_path: str) -> None:
        self._state.setdefault("processed", {})[sha256] = {
            "source": source,
            "destination": destination,
            "log": log_path,
            "timestamp": datetime.now().isoformat(),
        }
        self.save()

    def remove_entry(self, sha256: str) -> None:
        processed = self._state.get("processed", {})
        if sha256 in processed:
            del processed[sha256]
            self.save()

    def get_processed_count(self) -> int:
        return len(self._state.get("processed", {}))


class LogManager:
    """Schreibt Verarbeitungs-Logs und ermoeglicht Undo."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def write_log(
        self,
        source: Path,
        destination: Path,
        classification: Classification,
        sha256: str,
        text_preview: str = "",
    ) -> Path:
        """Log-Datei fuer eine Verarbeitung schreiben."""
        timestamp = datetime.now()
        entry = {
            "timestamp": timestamp.isoformat(),
            "source": str(source),
            "destination": str(destination),
            "sha256": sha256,
            "classification": asdict(classification),
            "text_preview": text_preview[:1500],
        }

        safe_stem = source.stem[:60].replace(" ", "_")
        log_name = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{safe_stem}.json"
        log_path = self.log_dir / log_name

        try:
            import tempfile
            content = json.dumps(entry, ensure_ascii=False, indent=2)
            tmp_fd, tmp_path = tempfile.mkstemp(dir=self.log_dir, suffix=".tmp")
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    f.write(content)
                os.replace(tmp_path, log_path)
            except Exception:
                Path(tmp_path).unlink(missing_ok=True)
                raise
            logger.debug("Log geschrieben: %s", log_name)
        except OSError as e:
            logger.error("Log konnte nicht geschrieben werden: %s", e)

        return log_path

    def get_last_log(self) -> Path | None:
        """Letztes Log-File finden (fuer Undo)."""
        logs = sorted(self.log_dir.glob("*.json"))
        return logs[-1] if logs else None

    def read_log(self, log_path: Path) -> dict[str, Any]:
        """Log-Datei lesen."""
        return json.loads(log_path.read_text(encoding="utf-8"))

    def get_all_logs(self) -> list[dict[str, Any]]:
        """Alle Logs lesen und als Liste zurueckgeben (neueste zuerst)."""
        logs = sorted(self.log_dir.glob("*.json"), reverse=True)
        results = []
        for log_path in logs:
            try:
                data = json.loads(log_path.read_text(encoding="utf-8"))
                data["_log_file"] = log_path.name
                results.append(data)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Log nicht lesbar: %s -- %s", log_path.name, e)
        return results


def undo_last(log_dir: Path, inbox: Path, state_path: Path) -> str:
    """Letzte Verschiebung rueckgaengig machen."""
    log_mgr = LogManager(log_dir)
    last_log = log_mgr.get_last_log()

    if not last_log:
        return "Kein Log gefunden -- nichts zum Rueckgaengig machen."

    data = log_mgr.read_log(last_log)
    dest = Path(data["destination"])

    if not dest.exists():
        return f"Datei nicht gefunden: {dest}"

    inbox.mkdir(parents=True, exist_ok=True)
    back_path = inbox / dest.name
    if back_path.exists():
        stamp = datetime.now().strftime("%H%M%S")
        back_path = inbox / f"{dest.stem}_UNDO_{stamp}{dest.suffix}"

    try:
        shutil.move(str(dest), str(back_path))
    except OSError as e:
        logger.error("Undo fehlgeschlagen: %s", e)
        return f"Undo fehlgeschlagen: {e}"

    sha = data.get("sha256")
    if sha:
        state_mgr = StateManager(state_path)
        state_mgr.remove_entry(sha)

    logger.info("Undo: %s -> %s", dest.name, back_path)
    return f"Rueckgaengig: {dest.name} -> {back_path}"
