"""Einstellungs-Seite (Profil-Dropdown).

Stub fuer Phase 1; wird in Phase 5 ausgebaut.
"""

from __future__ import annotations

from nicegui import ui

from ..theme import page_header, callout


def build() -> None:
    page_header("Einstellungen", "Dokumentenarten, Kunden, Laender und Pfade.")
    callout("Phase 5 — Einstellungen werden hier gebaut.", "info")
