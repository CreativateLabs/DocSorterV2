"""System-Voraussetzungen pruefen: Tesseract, Poppler, Python-Version."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

_OS = platform.system()  # "Darwin", "Windows", "Linux"


@dataclass
class CheckResult:
    """Ergebnis einer Voraussetzungs-Pruefung."""
    name: str
    ok: bool
    version: str = ""
    message: str = ""
    fix_hint: str = ""


def check_python_version(min_version: tuple[int, int] = (3, 9)) -> CheckResult:
    """Python-Version pruefen."""
    current = sys.version_info[:2]
    ok = current >= min_version
    return CheckResult(
        name="Python",
        ok=ok,
        version=f"{current[0]}.{current[1]}",
        message=f"Python {current[0]}.{current[1]}" if ok else f"Python {current[0]}.{current[1]} (min {min_version[0]}.{min_version[1]} benoetigt)",
        fix_hint="" if ok else "Python 3.10+ installieren: https://python.org",
    )


def check_tesseract() -> CheckResult:
    """Tesseract OCR pruefen."""
    path = shutil.which("tesseract")
    if not path:
        if _OS == "Darwin":
            hint = "brew install tesseract tesseract-lang"
        elif _OS == "Windows":
            hint = (
                "choco install tesseract  (Windows, Chocolatey)\n"
                "ODER manuell: https://github.com/UB-Mannheim/tesseract/wiki"
            )
        else:
            hint = "sudo apt install tesseract-ocr tesseract-ocr-deu  (Debian/Ubuntu)"
        return CheckResult(
            name="Tesseract OCR",
            ok=False,
            message="Nicht installiert",
            fix_hint=hint,
        )
    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        version_line = result.stdout.split("\n")[0] if result.stdout else result.stderr.split("\n")[0]
        version = version_line.replace("tesseract ", "").strip()
    except Exception:
        version = "unbekannt"

    return CheckResult(name="Tesseract OCR", ok=True, version=version, message=f"OK ({version})")


def check_tesseract_languages(required: str = "eng+deu+sqi") -> CheckResult:
    """Tesseract-Sprachen pruefen."""
    try:
        result = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True, text=True, timeout=5,
        )
        available = set(result.stdout.strip().split("\n")[1:])  # Erste Zeile ist Header
        needed = set(required.split("+"))
        missing = needed - available

        if missing:
            if _OS == "Darwin":
                lang_hint = "brew install tesseract-lang"
            elif _OS == "Windows":
                lang_hint = (
                    "Tesseract-Installer ausfuehren und Sprachpakete auswaehlen:\n"
                    "https://github.com/UB-Mannheim/tesseract/wiki"
                )
            else:
                lang_hint = "sudo apt install tesseract-ocr-deu tesseract-ocr-sqi  (Debian/Ubuntu)"
            return CheckResult(
                name="Tesseract Sprachen",
                ok=False,
                version=f"{len(available)} verfuegbar",
                message=f"Fehlend: {', '.join(sorted(missing))}",
                fix_hint=lang_hint,
            )
        return CheckResult(
            name="Tesseract Sprachen",
            ok=True,
            version=f"{', '.join(sorted(needed))} verfuegbar",
            message="OK",
        )
    except FileNotFoundError:
        return CheckResult(
            name="Tesseract Sprachen",
            ok=False,
            message="Tesseract nicht installiert",
            fix_hint="Zuerst Tesseract installieren",
        )
    except Exception as e:
        return CheckResult(name="Tesseract Sprachen", ok=False, message=str(e))


def check_poppler() -> CheckResult:
    """Poppler (pdftotext/pdftoppm) pruefen fuer PDF-zu-Bild-Konvertierung."""
    path = shutil.which("pdftoppm") or shutil.which("pdftotext")
    if not path:
        if _OS == "Darwin":
            poppler_hint = "brew install poppler"
        elif _OS == "Windows":
            poppler_hint = (
                "choco install poppler  (Windows, Chocolatey)\n"
                "ODER manuell: https://github.com/oschwartz10612/poppler-windows/releases"
            )
        else:
            poppler_hint = "sudo apt install poppler-utils  (Debian/Ubuntu)"
        return CheckResult(
            name="Poppler",
            ok=False,
            message="Nicht installiert",
            fix_hint=poppler_hint,
        )
    return CheckResult(name="Poppler", ok=True, message="OK")


def run_all_checks(ocr_languages: str = "eng+deu+sqi") -> list[CheckResult]:
    """Alle Voraussetzungen pruefen."""
    return [
        check_python_version(),
        check_tesseract(),
        check_tesseract_languages(ocr_languages),
        check_poppler(),
    ]


def print_check_results(results: list[CheckResult]) -> bool:
    """Ergebnisse auf der Konsole ausgeben. Returns True wenn alles OK."""
    all_ok = True
    print("\n  System-Check:")
    for r in results:
        status = "OK" if r.ok else "FEHLT"
        icon = "+" if r.ok else "!"
        print(f"    [{icon}] {r.name}: {r.message}")
        if not r.ok:
            all_ok = False
            if r.fix_hint:
                for line in r.fix_hint.split("\n"):
                    print(f"        -> {line}")
    print()
    return all_ok
