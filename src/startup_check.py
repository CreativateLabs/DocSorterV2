"""Startup-Checks: Prüft ob alle notwendigen Abhängigkeiten vorhanden sind.

Wird beim Start des Programms aufgerufen. Zeigt verständliche Fehlermeldungen
wenn Tesseract, Poppler oder andere Abhängigkeiten fehlen.
"""

from __future__ import annotations

import logging
import platform
import shutil
import sys
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_OS = platform.system()


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str
    hint: str = ""
    critical: bool = False


def _check_tesseract() -> CheckResult:
    """Tesseract OCR vorhanden?"""
    path = shutil.which("tesseract")
    if path:
        return CheckResult("Tesseract OCR", True, f"Gefunden: {path}")

    if _OS == "Darwin":
        hint = "brew install tesseract tesseract-lang"
    elif _OS == "Windows":
        hint = "https://github.com/UB-Mannheim/tesseract/wiki (Installer herunterladen)"
    else:
        hint = "sudo apt-get install tesseract-ocr tesseract-ocr-deu"

    return CheckResult(
        "Tesseract OCR", False,
        "Nicht gefunden — OCR (Bildtexterkennung) nicht verfügbar",
        hint=hint,
        critical=False,
    )


def _check_poppler() -> CheckResult:
    """Poppler (pdftoppm) für PDF→Bild-Konvertierung vorhanden?"""
    path = shutil.which("pdftoppm")
    if path:
        return CheckResult("Poppler (PDF-Konvertierung)", True, f"Gefunden: {path}")

    if _OS == "Darwin":
        hint = "brew install poppler"
    elif _OS == "Windows":
        hint = "https://github.com/oschwartz10612/poppler-windows/releases (in PATH eintragen)"
    else:
        hint = "sudo apt-get install poppler-utils"

    return CheckResult(
        "Poppler (PDF-Konvertierung)", False,
        "Nicht gefunden — PDF-Vorschau und OCR auf PDFs nicht verfügbar",
        hint=hint,
        critical=False,
    )


def _check_python_version() -> CheckResult:
    """Python ≥ 3.10?"""
    v = sys.version_info
    ok = (v.major, v.minor) >= (3, 10)
    return CheckResult(
        "Python-Version",
        ok,
        f"Python {v.major}.{v.minor}.{v.micro}",
        hint="Python 3.10 oder neuer erforderlich" if not ok else "",
        critical=True,
    )


def _check_nicegui() -> CheckResult:
    """NiceGUI installiert?"""
    try:
        import nicegui
        return CheckResult("NiceGUI", True, f"Version {nicegui.__version__}")
    except ImportError:
        return CheckResult(
            "NiceGUI", False, "Nicht installiert",
            hint="pip install nicegui>=2.0",
            critical=True,
        )


def run_all_checks() -> list[CheckResult]:
    """Alle Startup-Checks ausführen und Ergebnisse zurückgeben."""
    checks = [
        _check_python_version(),
        _check_nicegui(),
        _check_tesseract(),
        _check_poppler(),
    ]

    for c in checks:
        if c.ok:
            logger.info("✓ %s: %s", c.name, c.message)
        elif c.critical:
            logger.error("✗ %s: %s | Tipp: %s", c.name, c.message, c.hint)
        else:
            logger.warning("⚠ %s: %s | Tipp: %s", c.name, c.message, c.hint)

    return checks


def has_critical_failure(checks: list[CheckResult]) -> bool:
    """Gibt es kritische Fehler die den Start verhindern?"""
    return any(not c.ok and c.critical for c in checks)


def format_summary(checks: list[CheckResult]) -> str:
    """Lesbare Zusammenfassung aller Checks."""
    lines = []
    for c in checks:
        icon = "✓" if c.ok else ("✗" if c.critical else "⚠")
        line = f"{icon} {c.name}: {c.message}"
        if not c.ok and c.hint:
            line += f"\n   → {c.hint}"
        lines.append(line)
    return "\n".join(lines)
