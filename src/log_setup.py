"""Zentrales Logging-Setup mit Rotation und strukturiertem Output."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False


def setup_logging(
    log_dir: Path | None = None,
    level: int = logging.INFO,
    log_to_file: bool = True,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 10,
) -> None:
    """Logging fuer die gesamte Anwendung konfigurieren.

    - Console: INFO+ mit kurzem Format
    - Datei: DEBUG+ mit ausfuehrlichem Format + Rotation
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Bestehende Handler entfernen
    root.handlers.clear()

    # Console Handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console_fmt = logging.Formatter(
        "%(levelname)-8s %(message)s",
    )
    console.setFormatter(console_fmt)
    root.addHandler(console)

    # File Handler mit Rotation
    if log_to_file and log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "docsorter.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        root.addHandler(file_handler)

    # Drittanbieter-Logger leiser stellen
    for noisy in ["watchdog", "nicegui", "uvicorn", "httpx", "httpcore"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
