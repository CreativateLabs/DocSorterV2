"""LocalConnector: Lokales Dateisystem als Dokumenten-Quelle.

Standard-Connector der den bestehenden Inbox/Archive Zugriff wrapped.
Ist immer verbunden.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BaseConnector


class LocalConnector(BaseConnector):
    """Lokales Dateisystem als Dokumenten-Quelle."""

    def __init__(self, base_path: Path | None = None, allowed_types: set[str] | None = None):
        self._base_path = base_path
        self._allowed_types = allowed_types or {".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}

    @property
    def name(self) -> str:
        return "Lokales Dateisystem"

    @property
    def icon(self) -> str:
        return "folder"

    @property
    def description(self) -> str:
        return "Dateien aus dem lokalen Inbox-Ordner"

    def _get_base_path(self) -> Path:
        """Basis-Pfad ermitteln (aus Config oder explizit gesetzt)."""
        if self._base_path:
            return self._base_path
        try:
            from ...config import load_config
            cfg = load_config()
            return Path(cfg["paths"]["inbox"])
        except Exception:
            return Path.home() / ".doc-sorter" / "inbox"

    def list_files(self, folder: str = "") -> list[dict[str, Any]]:
        """Dateien im lokalen Ordner auflisten."""
        base = self._get_base_path()
        if folder:
            target = base / folder
        else:
            target = base

        if not target.exists():
            return []

        files = []
        for f in sorted(target.iterdir()):
            if f.is_dir():
                files.append({
                    "name": f.name,
                    "path": str(f),
                    "size": "",
                    "suffix": "",
                    "is_folder": True,
                })
            elif f.is_file() and f.suffix.lower() in self._allowed_types:
                stat = f.stat()
                size_kb = stat.st_size / 1024
                size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
                files.append({
                    "name": f.name,
                    "path": str(f),
                    "size": size_str,
                    "suffix": f.suffix.lower(),
                    "is_folder": False,
                })

        return files

    def read_file(self, path: str) -> bytes:
        """Datei-Inhalt lesen."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {path}")
        return p.read_bytes()

    def is_connected(self) -> bool:
        """Lokales Dateisystem ist immer verbunden."""
        return True

    def connect(self, **kwargs: Any) -> bool:
        """Keine Verbindung noetig fuer lokales FS."""
        return True
