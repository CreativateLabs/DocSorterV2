"""Roadmap-Seite (Profil-Dropdown).

Stub fuer Phase 1; wird in Phase 6 ausgebaut.
"""

from __future__ import annotations

from nicegui import ui

from ..theme import page_header, callout


def build() -> None:
    page_header("Roadmap", "Was ist verfuegbar, was kommt als naechstes.")
    callout("Phase 6 — Roadmap-Inhalte folgen.", "info")
