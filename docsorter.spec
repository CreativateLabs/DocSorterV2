# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller Spec-Datei für Doc-Sorter Desktop App.

Erstellt ein natives macOS .app / Windows .exe Bundle.

Bauen:
  Mac:     pyinstaller docsorter.spec --distpath dist/mac
  Windows: pyinstaller docsorter.spec --distpath dist/win
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ---------------------------------------------------------------------------
# NiceGUI Ressourcen sammeln (CSS, JS, Icons, Templates)
# ---------------------------------------------------------------------------
nicegui_datas = collect_data_files("nicegui")

# ---------------------------------------------------------------------------
# Projektspezifische Ressourcen
# ---------------------------------------------------------------------------
project_root = Path(SPECPATH)

extra_datas = [
    # SAUBERE Default-Config (KEINE Nutzerdaten, KEINE Secrets).
    # Wird beim ersten App-Start in das Benutzer-Datenverzeichnis kopiert.
    # config.yaml (Nutzerdaten) wird BEWUSST NICHT gebundelt.
    (str(project_root / "config.default.yaml"), "."),
    # NiceGUI statische Assets
    *nicegui_datas,
]

# ---------------------------------------------------------------------------
# Windows: Tesseract OCR in Bundle einbetten
# TESSERACT_PATH kann per Umgebungsvariable überschrieben werden
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    tess_path = os.environ.get(
        "TESSERACT_PATH",
        r"C:\Program Files\Tesseract-OCR"
    )
    if os.path.exists(tess_path):
        extra_datas.append((tess_path, "tesseract"))
        print(f"[spec] Tesseract gefunden und wird eingebettet: {tess_path}")

# ---------------------------------------------------------------------------
# Versteckte Imports die PyInstaller nicht automatisch findet
# ---------------------------------------------------------------------------
hidden_imports = [
    # NiceGUI internals
    "nicegui.elements",
    "nicegui.events",
    "nicegui.storage",
    *collect_submodules("nicegui"),
    # Async
    "asyncio",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    # Starlette / FastAPI
    "starlette",
    "starlette.routing",
    "starlette.middleware",
    "starlette.responses",
    # ML / Lern-Engine (optional — kein harter Fehler wenn nicht vorhanden)
    "sklearn",
    "sklearn.linear_model",
    "sklearn.preprocessing",
    "sentence_transformers",
    # Dokument-Lesen
    "pypdf",
    "docx",
    "pytesseract",
    "pdf2image",
    "PIL",
    "PIL.Image",
    # Sonstiges
    "httpx",
    "yaml",
    "watchdog",
    "watchdog.observers",
    "watchdog.observers.polling",
    "langdetect",
    "slugify",
    # Windows: pywebview
    "webview",
]

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [str(project_root / "dashboard.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=extra_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
        "notebook",
        "jupyter",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

# ---------------------------------------------------------------------------
# Einzelne EXE (für Windows) / macOS App
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DocSorter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                    # Kein Terminal-Fenster
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,                 # None = aktuell; 'arm64' / 'x86_64' für Crossbuild
    codesign_identity=None,           # Mac: Signing-Identity (Code-Signierung)
    entitlements_file=None,
    icon=str(project_root / "assets" / "icon.icns") if sys.platform == "darwin"
        else str(project_root / "assets" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DocSorter",
)

# ---------------------------------------------------------------------------
# macOS .app Bundle
# ---------------------------------------------------------------------------
if sys.platform == "darwin":
    # Version dynamisch aus src/version.py (einzige Quelle der Wahrheit)
    try:
        sys.path.insert(0, str(project_root))
        from src.version import __version__ as _app_version  # noqa: E402
    except Exception:
        _app_version = "0.0.0"

    app = BUNDLE(
        coll,
        name="DocSorter.app",
        icon=str(project_root / "assets" / "icon.icns"),
        bundle_identifier="de.docsorter.app",
        info_plist={
            "CFBundleName": "Doc-Sorter",
            "CFBundleDisplayName": "Doc-Sorter",
            "CFBundleVersion": _app_version,
            "CFBundleShortVersionString": _app_version,
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,  # Dark Mode Support
            "LSMinimumSystemVersion": "12.0",          # macOS Monterey+

            # ── macOS-Berechtigungsdialoge (TCC) ────────────────────────────
            # Ohne diese Usage-Description-Strings verweigert macOS den
            # Zugriff STUMM (ohne Dialog). Jeder String muss aussagen,
            # warum die App die Berechtigung braucht.
            "NSCameraUsageDescription":
                "Doc-Sorter kann Dokumente per Kamera scannen, um sie "
                "automatisch zu sortieren und zu erkennen.",
            "NSDocumentsFolderUsageDescription":
                "Doc-Sorter greift auf den Dokumente-Ordner zu, um "
                "abgelegte Dateien zu sortieren und zu archivieren.",
            "NSDownloadsFolderUsageDescription":
                "Doc-Sorter überwacht optional den Downloads-Ordner, "
                "um neue Dokumente automatisch einzulesen.",
            "NSDesktopFolderUsageDescription":
                "Doc-Sorter überwacht optional den Schreibtisch, "
                "um dort abgelegte Dokumente automatisch zu sortieren.",
            "NSAppleEventsUsageDescription":
                "Doc-Sorter öffnet bei Bedarf Dateien in anderen Programmen "
                "(z. B. Vorschau oder Safari) zur Ansicht.",
        },
    )
