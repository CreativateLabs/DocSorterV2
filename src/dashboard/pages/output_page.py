"""Output-Seite — Run-Accordions mit Live-Status.

Stub fuer Phase 1; wird in Phase 4 ausgebaut.
"""

from __future__ import annotations

from nicegui import ui

from ..theme import page_header, callout


def build() -> None:
    page_header("Output", "Sortier-Laeufe und verschobene Dateien.")
    callout("Phase 4 — Output-Seite wird hier gebaut.", "info")
