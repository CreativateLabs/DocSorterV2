"""BaseConnector: Abstrakte Basis fuer Dokumenten-Quellen.

Jeder Connector muss diese Methoden implementieren:
- name/icon: Anzeige-Informationen
- list_files: Dateien in einem Ordner auflisten
- read_file: Datei-Inhalt lesen
- is_connected/connect: Verbindungsstatus
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """Abstrakte Basis fuer Dokumenten-Quellen."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Anzeigename des Connectors."""
        ...

    @property
    @abstractmethod
    def icon(self) -> str:
        """Material Icon Name."""
        ...

    @property
    def description(self) -> str:
        """Optionale Beschreibung."""
        return ""

    @abstractmethod
    def list_files(self, folder: str = "") -> list[dict[str, Any]]:
        """Dateien in einem Ordner auflisten.

        Returns:
            Liste von Dicts mit:
            - name: Dateiname
            - path: Pfad/Identifier
            - size: Groesse als String
            - suffix: Dateiendung
            - is_folder: bool
        """
        ...

    @abstractmethod
    def read_file(self, path: str) -> bytes:
        """Datei-Inhalt als Bytes lesen."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Ist der Connector aktiv/verbunden?"""
        ...

    @abstractmethod
    def connect(self, **kwargs: Any) -> bool:
        """Verbindung herstellen.

        Returns:
            True wenn erfolgreich
        """
        ...

    def disconnect(self) -> None:
        """Verbindung trennen (optional)."""
        pass

    def get_status(self) -> dict[str, Any]:
        """Status-Information fuer Dashboard."""
        return {
            "name": self.name,
            "icon": self.icon,
            "connected": self.is_connected(),
            "description": self.description,
        }
