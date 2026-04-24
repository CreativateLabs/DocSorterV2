"""App-Pfade — PyInstaller-sicher und cross-platform.

Im normalen Entwicklungsmodus liegen Daten relativ zum Projektverzeichnis.
Im gepackten Modus (PyInstaller sys.frozen) wird das korrekte AppData-Verzeichnis
des Betriebssystems verwendet, damit keine Daten in /Applications oder %PROGRAMFILES%
geschrieben werden (keine Admin-Rechte nötig).

Verwendung:
    from src.app_paths import get_app_dir, get_user_data_dir, get_config_path
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """Läuft der Code als PyInstaller-Bundle?"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_bundle_dir() -> Path:
    """Verzeichnis in dem die gebündelten Ressourcen liegen (PyInstaller _MEIPASS)."""
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    # Im Entwicklungsmodus: Projektverzeichnis (zwei Ebenen über src/)
    return Path(__file__).resolve().parent.parent


def get_user_data_dir() -> Path:
    """Beschreibbares Benutzer-Datenverzeichnis (plattformspezifisch).

    - macOS:   ~/Library/Application Support/DocSorterV2
    - Windows: %APPDATA%/DocSorterV2  (= C:/Users/<user>/AppData/Roaming/DocSorterV2)
    - Linux:   ~/.local/share/DocSorterV2
    - Dev:     Projektverzeichnis (kein sys.frozen)

    V2 nutzt ein eigenes Verzeichnis, damit bestehende V1-Daten (aus
    doc-sorter-mvp) unangetastet bleiben und V2-Installationen stets frisch
    starten. Eine Migration V1 -> V2 wird bei Bedarf separat bereitgestellt.
    """
    if not is_frozen():
        # Entwicklungsmodus: Daten liegen direkt im Projektverzeichnis
        return get_bundle_dir()

    import platform
    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "DocSorterV2"
    elif system == "Windows":
        import os
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        base = Path(appdata) / "DocSorterV2"
    else:
        # Linux / andere Unix
        base = Path.home() / ".local" / "share" / "DocSorterV2"

    base.mkdir(parents=True, exist_ok=True)
    return base


def get_config_path() -> Path:
    """Pfad zur config.yaml.

    Im Frozen-Modus liegt die Config im Benutzer-Datenverzeichnis,
    damit der Nutzer sie bearbeiten kann ohne Admin-Rechte.
    Im Dev-Modus: Projektverzeichnis/config.yaml.
    """
    data_dir = get_user_data_dir()
    config_file = data_dir / "config.yaml"

    # Beim ersten Start: saubere Default-Config aus Bundle kopieren.
    # Reihenfolge: config.default.yaml (Vorlage) → config.yaml (Nutzerdaten)
    if is_frozen() and not config_file.exists():
        bundle_dir = get_bundle_dir()
        # Primär: saubere Vorlage (niemals Nutzerdaten)
        for candidate in ("config.default.yaml", "config.yaml"):
            bundle_config = bundle_dir / candidate
            if bundle_config.exists():
                import shutil
                shutil.copy2(bundle_config, config_file)
                break

    return config_file


def get_state_path() -> Path:
    """Pfad zur _state.json (Benutzerkonten, Pläne, etc.)."""
    return get_user_data_dir() / "_state.json"


def get_logs_dir() -> Path:
    """Pfad zum Logs-Verzeichnis."""
    logs = get_user_data_dir() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs
