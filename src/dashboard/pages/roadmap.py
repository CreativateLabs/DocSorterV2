"""Roadmap-Seite — zeigt Fortschritt und naechste Schritte.

Drei Sektionen: Verfuegbar / Naechste Version / Spaeter.
"""

from __future__ import annotations

from nicegui import ui

from ..theme import page_header, section_title


_AVAILABLE = [
    ("upload_file",       "Drag & Drop Input",         "Dokumente per Drag & Drop oder Datei-Dialog hochladen."),
    ("compare_arrows",    "IST/SOLL-Vorschau",         "Bestehende und vorgeschlagene Dateinamen nebeneinander editierbar."),
    ("auto_awesome",      "Automatisches Sortieren",   "Klassifikation + Umbenennung + Verschieben in einem Schritt."),
    ("school",            "Lernen aus Feedback",       "Hit-Counter, Keyword-Scores und Trainings-Engine passen sich deinem Workflow an."),
    ("translate",         "Mehrsprachige OCR",         "Deutsch, Englisch, Albanisch — Texterkennung in einer Pipeline."),
]

_COMING = [
    ("mail",              "E-Mail-Inbox",              "Mailpostfach direkt anbinden, Anhaenge automatisch importieren."),
    ("playlist_add_check","Bulk-Rename-Regeln",        "Eigene Regeln fuer Namens-Konventionen definieren und batch-anwenden."),
    ("content_copy",      "Duplikat-Erkennung",        "Gleiche Dokumente identifizieren und zusammenfuehren."),
]

_LATER = [
    ("smart_toy",         "Assistant-Chat",            "Dokument-Fragen in natuerlicher Sprache beantworten."),
    ("calendar_month",    "Kalender",                  "Termine aus Dokumenten extrahieren."),
    ("account_balance",   "Finanzen",                  "Rechnungen, Mahnungen, Zahlungsflows auf einen Blick."),
    ("account_balance_wallet","Bank-Abgleich",         "Transaktionen mit Kontoauszuegen matchen."),
    ("mic",               "Sprachmemos",               "Memos per Sprache aufnehmen und automatisch ablegen."),
]


def _render_items(items: list[tuple[str, str, str]], color: str, variant: str) -> None:
    """Rendert eine Liste von Roadmap-Eintraegen."""
    for icon, title, desc in items:
        with ui.element("div").style(
            f"border:1px solid {color}30;border-left:3px solid {color};"
            "border-radius:10px;background:rgba(10,22,40,0.5);"
            "padding:14px 18px;width:100%;display:flex;align-items:flex-start;gap:14px"
        ):
            with ui.element("div").style(
                f"width:36px;height:36px;border-radius:8px;flex-shrink:0;"
                f"display:flex;align-items:center;justify-content:center;"
                f"background:{color}18;color:{color}"
            ):
                ui.icon(icon).style("font-size:1.1rem")
            with ui.column().classes("gap-0").style("flex:1"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(title).style(
                        "font-size:0.92rem;font-weight:700;color:var(--ds-text)"
                    )
                    _badge(variant, color)
                ui.label(desc).style(
                    "font-size:0.78rem;color:var(--ds-text-2);line-height:1.5;margin-top:3px"
                )


def _badge(label: str, color: str) -> None:
    ui.label(label).style(
        f"font-size:0.62rem;font-weight:700;padding:2px 8px;border-radius:99px;"
        f"background:{color}18;color:{color};text-transform:uppercase;letter-spacing:0.06em"
    )


def build() -> None:
    """Roadmap-Seite aufbauen."""
    page_header(
        "Roadmap",
        "Was bereits funktioniert und was noch kommt.",
    )

    # ── Verfuegbar jetzt ──
    section_title("Verfuegbar jetzt", "check_circle")
    with ui.column().classes("w-full gap-2").style("margin-bottom:28px"):
        _render_items(_AVAILABLE, "#10b981", "Live")

    # ── Naechste Version ──
    section_title("Naechste Version", "schedule")
    with ui.column().classes("w-full gap-2").style("margin-bottom:28px"):
        _render_items(_COMING, "#f59e0b", "Geplant")

    # ── Spaeter ──
    section_title("Spaeter", "lightbulb")
    with ui.column().classes("w-full gap-2"):
        _render_items(_LATER, "#a78bfa", "Idee")
