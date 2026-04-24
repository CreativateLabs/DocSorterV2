"""Input-Seite — Drag & Drop + IST/SOLL-Tabelle.

Stub fuer Phase 1; wird in Phase 3 ausgebaut.
"""

from __future__ import annotations

from nicegui import ui

from ..theme import page_header, callout


def build() -> None:
    page_header("Input", "Dokumente einlesen und Sortier-Vorschlag erzeugen.")
    callout("Phase 3 — Input-Seite wird hier gebaut.", "info")
