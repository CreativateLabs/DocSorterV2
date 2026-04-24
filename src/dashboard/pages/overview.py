"""Uebersicht-Seite: Crisp Stat-Cards, Pipeline-Visualisierung, Watcher und LLM Status.

UI Design Overhaul: Tailwind-orientiertes Design mit konsistenten Komponenten.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from nicegui import ui

from ...alerts import get_active_alerts
from ...config import get_file_types, load_config
from ...watcher import get_watcher_status, is_watching, start_watching, stop_watching
from ...llm_classifier import get_available_providers
from ..theme import (
    callout, empty_state, notify_error, page_header, pipeline_visual,
    section_divider, section_title, stat_card, status_badge,
)

logger = logging.getLogger(__name__)


def _get_stats(cfg: dict[str, Any]) -> dict[str, Any]:
    """Statistiken aus dem Dateisystem lesen."""
    inbox = Path(cfg["paths"]["inbox"])
    archive = Path(cfg["paths"]["archive"])
    logs_dir = Path(cfg["paths"]["logs"])
    review = Path(cfg["paths"].get("review", str(archive / "_review")))

    allowed = get_file_types(cfg)
    inbox_files = []
    if inbox.exists():
        inbox_files = [
            f for f in inbox.rglob("*")
            if f.is_file() and f.suffix.lower() in allowed
        ]

    review_files = []
    if review.exists():
        review_files = [f for f in review.rglob("*") if f.is_file()]

    state_path = archive / "_state.json"
    processed_count = 0
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            processed_count = len(state.get("processed", {}))
        except (json.JSONDecodeError, OSError):
            pass

    last_run = "Noch nie"
    log_files = sorted(logs_dir.glob("*.json")) if logs_dir.exists() else []
    if log_files:
        try:
            last_log = json.loads(log_files[-1].read_text(encoding="utf-8"))
            ts = last_log.get("timestamp", "")
            last_run = ts[:19].replace("T", " ") if ts else "unbekannt"
        except (json.JSONDecodeError, OSError):
            pass

    archive_count = sum(1 for f in archive.rglob("*") if f.is_file()) if archive.exists() else 0

    return {
        "inbox_count": len(inbox_files),
        "review_count": len(review_files),
        "processed_count": processed_count,
        "archive_count": archive_count,
        "last_run": last_run,
        "log_count": len(log_files),
    }


def build() -> None:
    """Uebersicht-Seite aufbauen mit Crisp Design."""
    cfg = load_config()
    stats = _get_stats(cfg)

    page_header(
        "Uebersicht",
        "Dein Dokumenten-Dashboard auf einen Blick.",
    )

    # ── Erster-Start-Banner (wenn noch nichts verarbeitet) ──────────────────
    if stats["processed_count"] == 0 and stats["inbox_count"] == 0 and stats["review_count"] == 0:
        callout(
            "Willkommen! So geht's los: Lege Dokumente in den Inbox-Ordner "
            "(z.B. per Drag\u2011&\u2011Drop) und starte dann im Terminal eine Vorschau. "
            "Danach kannst du die erkannten Klassifikationen pruefen und freigeben.",
            "info", "rocket_launch",
        )

    # ── Quick-Action-Banner wenn Dokumente in Inbox warten ──────────────────
    elif stats["inbox_count"] > 0:
        with ui.row().classes("items-center gap-3 w-full").style(
            "background:linear-gradient(135deg,rgba(0,212,255,0.12),rgba(124,58,237,0.08));"
            "border:1px solid rgba(0,212,255,0.35);border-radius:12px;"
            "padding:12px 16px;margin-bottom:12px;"
            "box-shadow:0 2px 20px rgba(0,212,255,0.15)"
        ):
            ui.icon("notifications_active").style("color:#00d4ff;font-size:1.4rem")
            with ui.column().classes("gap-0 flex-1"):
                ui.label(f"{stats['inbox_count']} neue Dokument(e) in der Inbox").style(
                    "font-size:0.95rem;font-weight:700;color:var(--ds-text)"
                )
                ui.label("Starte eine Vorschau oder sortiere direkt.").style(
                    "font-size:0.75rem;color:var(--ds-text-2)"
                )
            ui.button(
                "Zum Terminal",
                icon="play_arrow",
                on_click=lambda: ui.navigate.to("/terminal"),
            ).classes("ds-btn-primary").tooltip("Vorschau oder Sortierung starten")

    # ── Proaktive Alerts (Fristen, Zahlungsziele, Vertragsverl\u00e4ngerungen) ──
    try:
        alerts = get_active_alerts()
    except Exception as exc:
        logger.debug("Alert-Scan fehlgeschlagen: %s", exc)
        alerts = []

    if alerts:
        critical = [a for a in alerts if a.severity == "critical"]
        warn = [a for a in alerts if a.severity == "warning"]
        info = [a for a in alerts if a.severity == "info"]

        _sev_config = {
            "critical": ("#ff3366", "rgba(255,51,102,0.08)", "rgba(255,51,102,0.4)", "error"),
            "warning":  ("#ff9f0a", "rgba(255,159,10,0.08)", "rgba(255,159,10,0.4)", "warning"),
            "info":     ("#00d4ff", "rgba(0,212,255,0.06)", "rgba(0,212,255,0.3)", "notifications"),
        }

        # Header-Card
        with ui.element("div").style(
            "width:100%;border:1px solid rgba(255,159,10,0.3);border-radius:12px;"
            "background:rgba(255,159,10,0.04);padding:14px 18px;margin-bottom:12px"
        ):
            with ui.row().classes("items-center gap-3 w-full"):
                ui.icon("event_upcoming").style("color:#ff9f0a;font-size:1.4rem;flex-shrink:0")
                with ui.column().classes("gap-0 flex-1"):
                    ui.label(
                        f"{len(alerts)} Fristen & Erinnerungen"
                    ).style(
                        "font-size:0.95rem;font-weight:700;color:var(--ds-text)"
                    )
                    parts = []
                    if critical:
                        parts.append(f"{len(critical)} dringend")
                    if warn:
                        parts.append(f"{len(warn)} bald f\u00e4llig")
                    if info:
                        parts.append(f"{len(info)} Hinweis(e)")
                    ui.label(" \u00b7 ".join(parts)).style(
                        "font-size:0.75rem;color:var(--ds-text-2)"
                    )

            # Liste der Top 5 Alerts
            with ui.column().classes("gap-2 w-full").style("margin-top:10px"):
                for a in alerts[:5]:
                    sev_color, sev_bg, sev_border, _ = _sev_config.get(a.severity, _sev_config["info"])
                    with ui.row().classes("items-center gap-3 w-full").style(
                        f"background:{sev_bg};border-left:3px solid {sev_color};"
                        "border-radius:6px;padding:8px 12px"
                    ):
                        ui.icon({
                            "todo": "task_alt",
                            "invoice": "receipt_long",
                            "subscription": "autorenew",
                            "contract": "description",
                        }.get(a.type, "notifications")).style(
                            f"color:{sev_color};font-size:1.1rem;flex-shrink:0"
                        )
                        with ui.column().classes("gap-0 flex-1 min-w-0"):
                            ui.label(a.title).style(
                                "font-size:0.82rem;font-weight:700;color:var(--ds-text);"
                                "white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
                            )
                            ui.label(a.description).style(
                                "font-size:0.7rem;color:var(--ds-text-2);"
                                "white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
                            )
                        if a.action_hint:
                            ui.label(a.action_hint).style(
                                f"font-size:0.65rem;color:{sev_color};font-weight:600;"
                                "white-space:nowrap;flex-shrink:0"
                            )

                if len(alerts) > 5:
                    ui.label(f"+ {len(alerts) - 5} weitere \u2014 siehe Mein Assistent").style(
                        "font-size:0.7rem;color:var(--ds-text-3);text-align:center;margin-top:4px"
                    )

    # ── Review-Reminder wenn Dokumente zur Pruefung bereit ──────────────────
    if stats["review_count"] > 0:
        with ui.row().classes("items-center gap-3 w-full").style(
            "background:rgba(255,159,10,0.08);border:1px solid rgba(255,159,10,0.35);"
            "border-radius:12px;padding:12px 16px;margin-bottom:12px"
        ):
            ui.icon("rate_review").style("color:#ff9f0a;font-size:1.4rem")
            with ui.column().classes("gap-0 flex-1"):
                ui.label(f"{stats['review_count']} Dokument(e) warten auf deine Pr\u00fcfung").style(
                    "font-size:0.95rem;font-weight:700;color:var(--ds-text)"
                )
                ui.label("Je mehr du best\u00e4tigst, desto besser lernt das System.").style(
                    "font-size:0.75rem;color:var(--ds-text-2)"
                )
            ui.button(
                "Jetzt pr\u00fcfen",
                icon="rate_review",
                on_click=lambda: ui.navigate.to("/review"),
            ).classes("ds-btn-warning").tooltip("Zur Pr\u00fcfung-Seite springen")

    # Pipeline-Visualisierung
    pipeline_visual(
        inbox_count=stats["inbox_count"],
        review_count=stats["review_count"],
        archive_count=stats["archive_count"],
    )

    # Stat Cards
    with ui.row().classes("w-full gap-4 flex-wrap mt-2"):
        inbox_val = stat_card(
            "Inbox", stats["inbox_count"], "inbox", "blue", " Dateien",
        )
        review_val = stat_card(
            "Zur Pruefung", stats["review_count"], "rate_review", "amber", " Dateien",
        )
        processed_val = stat_card(
            "Verarbeitet", stats["processed_count"], "check_circle", "green", " gesamt",
        )
        lastrun_val = stat_card(
            "Letzter Lauf", stats["last_run"], "schedule", "purple",
        )

    section_divider()

    # ---- Automatische Verarbeitung (Watcher) ----
    with ui.card().classes("ds-card w-full"):
        with ui.row().classes("items-center justify-between w-full"):
            with ui.row().classes("items-center gap-3"):
                watcher_icon = ui.icon("").classes("text-2xl")
                with ui.column().classes("gap-0"):
                    ui.label("Automatische Verarbeitung").classes("ds-section-title")
                    watcher_status_label = ui.label("").classes("ds-page-subtitle text-sm")

            watcher_btn = ui.button("", icon="")

        def _update_watcher_ui() -> None:
            if is_watching():
                watcher_icon._props["name"] = "sensors"
                watcher_icon.classes(replace="text-2xl text-green-500")
                status = get_watcher_status()
                watcher_status_label.text = f"Aktiv -- {status['files_processed']} Dateien automatisch verarbeitet"
                watcher_btn._props["icon"] = "stop"
                watcher_btn.text = "Stoppen"
                watcher_btn.classes(replace="ds-btn-danger")
            else:
                watcher_icon._props["name"] = "sensors_off"
                watcher_icon.classes(replace="text-2xl text-gray-400")
                watcher_status_label.text = "Inaktiv -- Neue Dateien werden nicht automatisch verarbeitet"
                watcher_btn._props["icon"] = "play_arrow"
                watcher_btn.text = "Starten"
                watcher_btn.classes(replace="ds-btn-success")
            watcher_icon.update()
            watcher_btn.update()

        def _toggle_watcher() -> None:
            try:
                if is_watching():
                    stop_watching()
                    ui.notify("Automatische Verarbeitung gestoppt", type="info")
                else:
                    from ...reader import read_text
                    from ...classifier import classify
                    from ...config import (
                        get_document_type_keywords, get_known_customers,
                        get_country_keywords, get_ocr_languages,
                    )
                    from ...organizer import move_file
                    from ...logger import LogManager, StateManager, file_hash

                    fresh_cfg = load_config()

                    def _process_file(file_path: Path) -> None:
                        ocr_langs = get_ocr_languages(fresh_cfg)
                        ocr_cfg = fresh_cfg.get("ocr", {})
                        text = read_text(file_path, ocr_languages=ocr_langs,
                                         ocr_dpi=ocr_cfg.get("dpi", 200),
                                         max_pages=ocr_cfg.get("max_pages", 5))
                        classification = classify(
                            text=text,
                            document_type_keywords=get_document_type_keywords(fresh_cfg),
                            known_customers=get_known_customers(fresh_cfg),
                            country_keywords=get_country_keywords(fresh_cfg),
                        )
                        archive = Path(fresh_cfg["paths"]["archive"])
                        target, moved = move_file(file_path, archive, classification, dry_run=False)
                        if moved:
                            logs_dir = Path(fresh_cfg["paths"]["logs"])
                            state_path = archive / "_state.json"
                            sha = file_hash(file_path)
                            log_mgr = LogManager(logs_dir)
                            state = StateManager(state_path)
                            log_path = log_mgr.write_log(file_path, target, classification, sha, text)
                            state.mark_processed(sha, str(file_path), str(target), str(log_path))
                            logger.info("Watcher: %s -> %s", file_path.name, target)

                    started = start_watching(fresh_cfg, _process_file)
                    if started:
                        ui.notify("Automatische Verarbeitung gestartet", type="positive")
                    else:
                        ui.notify("Laeuft bereits", type="warning")
            except Exception as exc:
                notify_error(exc, prefix="Automatische Verarbeitung: ")
                logger.exception("Watcher-Toggle fehlgeschlagen")
            _update_watcher_ui()

        watcher_btn.on("click", _toggle_watcher)
        _update_watcher_ui()

    # ---- KI-Unterstuetzung (LLM) ----
    with ui.card().classes("ds-card w-full"):
        section_title("KI-Unterstuetzung", "smart_toy")
        llm_cfg = cfg.get("llm", {})
        providers = get_available_providers()

        if llm_cfg.get("enabled"):
            provider_name = llm_cfg.get("provider", "openai")
            with ui.row().classes("items-center gap-3 mt-2"):
                status_badge("Aktiv", "success")
                ui.label(f"Provider: {provider_name}").classes("text-sm")
                mode_text = "Nur bei unsicheren Ergebnissen" if llm_cfg.get("fallback_only") else "Immer aktiv"
                status_badge(mode_text, "info")
        else:
            with ui.row().classes("items-center gap-3 mt-2"):
                status_badge("Deaktiviert", "neutral")
                ui.label("Aktiviere unter Einstellungen > KI-Unterstuetzung").classes(
                    "text-sm text-gray-400"
                )

        with ui.row().classes("gap-3 mt-3"):
            for p in providers:
                variant = "success" if p["ready"] else "warning" if p["installed"] else "error"
                label = "Bereit" if p["ready"] else "Kein API-Key" if p["installed"] else "Nicht installiert"
                status_badge(f"{p['name']}: {label}", variant)

    # ---- Schnellzugriff: Pfade ----
    with ui.card().classes("ds-card w-full"):
        section_title("Pfade", "folder")
        with ui.grid(columns=2).classes("gap-x-6 gap-y-2 mt-2"):
            for key, label in [("inbox", "Inbox"), ("archive", "Archiv"), ("logs", "Logs")]:
                ui.label(f"{label}:").classes("text-sm font-medium text-gray-500")
                ui.label(cfg["paths"][key]).classes("text-sm font-mono break-all")

    # Auto-Refresh
    def _refresh_stats() -> None:
        try:
            fresh_cfg = load_config()
            fresh = _get_stats(fresh_cfg)
            inbox_val.text = f"{fresh['inbox_count']} Dateien"
            review_val.text = f"{fresh['review_count']} Dateien"
            processed_val.text = f"{fresh['processed_count']} gesamt"
            lastrun_val.text = fresh["last_run"]
            _update_watcher_ui()
        except Exception:
            pass

    ui.timer(10.0, _refresh_stats)

    with ui.row().classes("mt-4 gap-3 items-center"):
        ui.button("Aktualisieren", on_click=_refresh_stats, icon="refresh").classes("ds-btn-secondary")
        ui.label("Aktualisiert sich automatisch alle 10 Sekunden").classes("text-xs text-gray-400")
