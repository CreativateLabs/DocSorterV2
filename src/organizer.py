"""Dateien umbenennen und in Ordnerstruktur verschieben."""

from __future__ import annotations

import logging
import os
import re
import shutil
import sys
from pathlib import Path

# Windows und macOS haben case-insensitive Dateisysteme per Default
_CASE_INSENSITIVE_FS = sys.platform in ("win32", "darwin")

from .classifier import Classification

logger = logging.getLogger(__name__)


def safe_name(text: str, max_len: int = 60) -> str:
    """Text fuer Dateinamen/Ordner bereinigen."""
    text = (text or "unbekannt").strip()
    text = re.sub(r'[\\/:*?"<>|]', "-", text)
    text = re.sub(r"[\s_]+", "_", text)
    text = text.strip("_-")
    return text[:max_len] if text else "unbekannt"


def build_filename(classification: Classification, original_ext: str) -> str:
    """Neuen Dateinamen nach Taxonomie bauen.

    Format: dokumentenart_kunde_land_datum.ext
    Gesamtlaenge wird auf 200 Zeichen begrenzt (sicher fuer alle Dateisysteme).
    """
    ext = original_ext.lower()[:10]  # Erweiterung sichern
    parts = [
        safe_name(classification.dokumentenart, 30),
        safe_name(classification.kunde, 40),
        safe_name(classification.land, 20),
        safe_name(classification.datum, 10),
    ]
    name = "_".join(parts)
    # Gesamtlaenge pruefen: max 200 Zeichen fuer den Stamm (ohne Erweiterung)
    max_stem = 200 - len(ext)
    if len(name) > max_stem:
        name = name[:max_stem]
    return f"{name}{ext}"


def build_target_folder(
    archive_base: Path,
    classification: Classification,
    is_review: bool = False,
) -> Path:
    """Zielordner nach Taxonomie bauen.

    Normal:  archive/dokumentenart/land/kunde/jahr/
    Review:  archive/_review/dokumentenart/
    """
    if is_review:
        return archive_base / "_review" / safe_name(classification.dokumentenart)

    return (
        archive_base
        / safe_name(classification.dokumentenart)
        / safe_name(classification.land)
        / safe_name(classification.kunde)
        / safe_name(classification.jahr, 4)
    )


def move_file(
    source: Path,
    archive_base: Path,
    classification: Classification,
    dry_run: bool = True,
) -> tuple[Path, bool]:
    """Datei umbenennen und verschieben.

    Returns: (ziel_pfad, tatsaechlich_verschoben)
    """
    target_folder = build_target_folder(
        archive_base,
        classification,
        is_review=classification.unsicher,
    )
    new_name = build_filename(classification, source.suffix)
    target_path = target_folder / new_name

    if dry_run:
        return target_path, False

    # Quell-Datei pruefen
    if not source.exists():
        logger.error("Quelldatei nicht mehr vorhanden: %s", source)
        return target_path, False

    if not source.is_file():
        logger.error("Quelle ist keine Datei: %s", source)
        return target_path, False

    # Ordner anlegen
    try:
        target_folder.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.error("Keine Schreibrechte fuer Zielordner: %s", target_folder)
        return target_path, False
    except OSError as e:
        logger.error("Ordner konnte nicht erstellt werden: %s -- %s", target_folder, e)
        return target_path, False

    # Kollision vermeiden: Zaehler statt Zeitstempel (deterministisch, kein Same-Second-Problem)
    # Auf case-insensitiven Dateisystemen (Windows, macOS) auch Gross/Klein-Kollisionen pruefen
    def _path_exists(p: Path) -> bool:
        if not p.exists():
            return False
        if _CASE_INSENSITIVE_FS:
            return True
        # Linux: nur exakte Gross/Klein-Schreibung zaehlt
        return p.name in {f.name for f in p.parent.iterdir()} if p.parent.exists() else False

    if _path_exists(target_path):
        stem = target_path.stem
        suffix = target_path.suffix
        counter = 1
        while _path_exists(target_path) and counter <= 999:
            target_path = target_folder / f"{stem}_{counter:03d}{suffix}"
            counter += 1
        if counter > 999 and _path_exists(target_path):
            import time as _time
            target_path = target_folder / f"{stem}_{int(_time.time())}{suffix}"
        logger.info("Namenskollision, umbenannt zu: %s", target_path.name)

    # Verschieben
    try:
        shutil.move(str(source), str(target_path))
        logger.info("Verschoben: %s -> %s", source.name, target_path)
        return target_path, True
    except PermissionError:
        logger.error("Keine Berechtigung zum Verschieben: %s", source)
        return target_path, False
    except OSError as e:
        logger.error("Verschieben fehlgeschlagen: %s -> %s: %s", source, target_path, e)
        return target_path, False
