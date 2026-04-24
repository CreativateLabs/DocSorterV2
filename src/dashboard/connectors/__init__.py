"""Connector-Architektur: Erweiterbare Dokumenten-Quellen.

Connectors abstrahieren den Zugriff auf verschiedene Dokumenten-Quellen:
- LocalConnector: Lokales Dateisystem (Standard)
- Zukuenftig: GoogleDriveConnector, SharePointConnector, etc.
"""

from .base import BaseConnector
from .local import LocalConnector

__all__ = ["BaseConnector", "LocalConnector"]
