"""Input-Seite — Drag & Drop, Dokumente analysieren, IST/SOLL-Tabelle, Pending-Run.

Flow:
1. Nutzer zieht Dokumente in den Upload-Bereich.
2. Pro Datei: text extrahieren, klassifizieren (Keyword + Lern-Engine),
   SOLL-Dateinamen + Zielordner berechnen.
3. Nutzer prueft / editiert die Vorschlaege in der Tabelle.
4. "Struktur uebernehmen und sortieren" -> pending_<uuid>.json + Worker
   wird gestartet, Redirect zu /output?run=<uuid>.

Saubere Reuse: reader.read_text, classifier.classify, learning_engine.predict,
organizer.build_filename / build_target_folder.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

from nicegui import events, ui

from ...classifier import Classification, classify
from ...config import (
    get_country_keywords,
    get_document_type_keywords,
    get_known_customers,
    get_ocr_languages,
    load_config,
)
from ...organizer import build_filename, build_target_folder
from ...reader import read_text
from ..theme import callout, friendly_error, page_header, section_title

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pfade fuer Pending-Runs / Run-State / Intake
# ---------------------------------------------------------------------------

RUN_STATE_DIR = Path("~/DocSorterV2/runs").expanduser()
INTAKE_DIR = Path("~/DocSorterV2/runs/_intake").expanduser()


def _ensure_dirs() -> None:
    RUN_STATE_DIR.mkdir(parents=True, exist_ok=True)
    INTAKE_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomic JSON-Write nach Projekt-Standard."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2))
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Klassifikation einer einzelnen Datei
# ---------------------------------------------------------------------------

def _classify_file(path: Path, cfg: dict) -> Classification:
    """Datei lesen, klassifizieren, ggf. Lern-Engine ueberschreiben lassen."""
    text = read_text(
        path,
        ocr_languages=get_ocr_languages(cfg),
        ocr_dpi=cfg.get("ocr", {}).get("dpi", 200),
        max_pages=cfg.get("ocr", {}).get("max_pages", 5),
    )

    cls = classify(
        text=text,
        document_type_keywords=get_document_type_keywords(cfg),
        known_customers=get_known_customers(cfg),
        country_keywords=get_country_keywords(cfg),
        min_text_length=cfg.get("confidence", {}).get("min_text_length", 30),
        uncertain_fields=cfg.get("confidence", {}).get(
            "uncertain_if_missing", ["kunde", "dokumentenart"]
        ),
    )

    # Lern-Engine: ueberschreibt nur bei hoher Konfidenz
    try:
        from ...learning_engine import _HIGH_CONFIDENCE, predict
        result = predict(text)
        if result.available and result.is_confident and result.confidence >= _HIGH_CONFIDENCE:
            cls.dokumentenart = result.label
            cls.confidence = max(cls.confidence, result.confidence)
            cls.matched_keywords.append(f"learning_engine({result.confidence:.2f})")
    except Exception as exc:
        logger.debug("Lern-Engine nicht verfuegbar: %s", exc)

    return cls


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def build() -> None:
    """Input-Seite aufbauen."""
    _ensure_dirs()

    page_header(
        "Input",
        "Dokumente einlesen — Doc-Sorter schlaegt Namen und Zielordner vor.",
    )

    # State pro Page-Render: Liste der vorgeschlagenen Files
    proposals: list[dict[str, Any]] = []

    cfg = load_config()
    archive_base = Path(cfg.get("paths", {}).get(
        "archive", "~/Documents/DocSorter/output"
    )).expanduser()

    # Upload-Handler wird hier schon deklariert — Verwendung von _render_table
    # ueber Late-Binding (Name erst zur Call-Time aufgeloest).
    async def _on_upload(e: events.UploadEventArguments) -> None:
        try:
            run_intake = INTAKE_DIR / uuid.uuid4().hex[:12]
            run_intake.mkdir(parents=True, exist_ok=True)
            target = run_intake / e.name
            content = e.content.read() if hasattr(e.content, "read") else e.content
            with open(target, "wb") as f:
                f.write(content)

            from nicegui import run as _run
            cls = await _run.io_bound(_classify_file, target, cfg)

            new_name = build_filename(cls, target.suffix)
            target_folder = build_target_folder(
                archive_base, cls, is_review=cls.unsicher
            )
            try:
                folder_rel = str(target_folder.relative_to(archive_base))
            except ValueError:
                folder_rel = str(target_folder)

            proposals.append({
                "intake_path": str(target),
                "original_name": e.name,
                "classification": cls,
                "proposed_name": new_name,
                "proposed_folder_rel": folder_rel,
            })
            _render_table.refresh()
            ui.notify(
                f'"{e.name}" analysiert ({cls.confidence:.0%} sicher)',
                type="positive",
            )
        except Exception as exc:
            logger.exception("Upload-Verarbeitung fehlgeschlagen")
            title, hint = friendly_error(exc)
            ui.notify(f"{title} - {hint}", type="negative", multi_line=True)

    # ---- 1) Upload-Bereich ----
    with ui.card().classes("ds-card w-full"):
        section_title("Dokumente hochladen", "cloud_upload")
        ui.label(
            "PDF, DOCX, Bilder oder Text. Mehrere Dateien gleichzeitig moeglich."
        ).style("font-size:0.82rem;color:var(--ds-text-2);margin-bottom:10px")

        ui.upload(
            multiple=True,
            auto_upload=True,
            max_file_size=2 * 1024 * 1024 * 1024,
            on_upload=_on_upload,
        ).classes("w-full ds-upload-area").props(
            'label="Dateien hier ablegen oder auswaehlen" accept="*.*"'
        )

    # ---- 2) Mailpostfach-Stub ----
    with ui.card().classes("ds-card-flat w-full mt-4").style("opacity:0.65"):
        with ui.row().classes("items-center gap-3 w-full"):
            ui.icon("mail").style("font-size:1.6rem;color:var(--ds-text-2)")
            with ui.column().classes("gap-0 flex-1"):
                ui.label("Oder verbinde dein Mailpostfach").style(
                    "font-size:0.95rem;font-weight:600;color:var(--ds-text)"
                )
                ui.label(
                    "Anhaenge automatisch importieren — coming soon."
                ).style("font-size:0.78rem;color:var(--ds-text-2)")
            ui.button("Bald verfuegbar").props("flat dense disable").style(
                "color:var(--ds-text-2);text-transform:none"
            )

    # ---- 3) Vorschlags-Tabelle (refreshable) ----
    table_container = ui.column().classes("w-full mt-6 gap-3")

    @ui.refreshable
    def _render_table() -> None:
        if not proposals:
            with ui.card().classes("ds-card-flat w-full").style(
                "border-style:dashed;text-align:center;padding:32px"
            ):
                ui.icon("inbox").style(
                    "font-size:2.5rem;color:var(--ds-text-3);margin-bottom:8px"
                )
                ui.label("Noch keine Dokumente. Lade welche hoch.").style(
                    "font-size:0.88rem;color:var(--ds-text-2)"
                )
            return

        section_title(f"Vorschlag fuer {len(proposals)} Dokument(e)", "edit_note")

        # Header
        with ui.row().classes("w-full items-center gap-2").style(
            "padding:8px 12px;background:rgba(0,212,255,0.05);"
            "border-radius:8px;font-size:0.7rem;font-weight:700;"
            "text-transform:uppercase;letter-spacing:0.06em;color:var(--ds-primary)"
        ):
            ui.label("IST-Dateiname").style("flex:2;min-width:0")
            ui.label("→").style("flex:0;min-width:24px;text-align:center")
            ui.label("SOLL-Dateiname (editierbar)").style("flex:3;min-width:0")
            ui.label("Zielordner").style("flex:3;min-width:0")
            ui.label("").style("width:40px;text-align:center")  # action col

        # Zeilen
        for idx, item in enumerate(proposals):
            confidence = item["classification"].confidence
            conf_color = (
                "#10b981" if confidence >= 0.7
                else "#f59e0b" if confidence >= 0.4
                else "#ef4444"
            )
            with ui.element("div").style(
                "border:1px solid var(--ds-border);border-radius:10px;"
                f"border-left:3px solid {conf_color};"
                "background:rgba(10,22,40,0.5);padding:10px 12px;width:100%"
            ):
                with ui.row().classes("w-full items-center gap-2"):
                    # IST
                    with ui.column().classes("gap-0").style("flex:2;min-width:0"):
                        ui.label(item["original_name"]).style(
                            "font-size:0.82rem;color:var(--ds-text);font-weight:600;"
                            "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                        )
                        ui.label(
                            f"Konfidenz {confidence:.0%} · "
                            f"{item['classification'].dokumentenart}"
                        ).style("font-size:0.68rem;color:var(--ds-text-2)")

                    ui.icon("arrow_forward").style(
                        "color:var(--ds-text-3);font-size:1rem"
                    ).classes("flex-shrink-0")

                    # SOLL editierbar
                    name_inp = ui.input(value=item["proposed_name"]).props(
                        "outlined dense"
                    ).classes("ds-input").style("flex:3;min-width:0")
                    name_inp.on(
                        "blur",
                        lambda _, i=idx, inp=name_inp: proposals[i].update(
                            {"proposed_name": inp.value or ""}
                        ),
                    )

                    # Zielordner editierbar (Pfad relativ zum Archiv anzeigen)
                    rel_target = item["proposed_folder_rel"]
                    folder_inp = ui.input(value=rel_target).props(
                        "outlined dense"
                    ).classes("ds-input").style("flex:3;min-width:0")
                    folder_inp.on(
                        "blur",
                        lambda _, i=idx, inp=folder_inp: proposals[i].update(
                            {"proposed_folder_rel": inp.value or ""}
                        ),
                    )

                    # Entfernen
                    def _remove(i: int = idx) -> None:
                        # Temp-Datei ggf. wegwerfen
                        try:
                            Path(proposals[i]["intake_path"]).unlink(missing_ok=True)
                        except Exception:
                            pass
                        proposals.pop(i)
                        _render_table.refresh()

                    ui.button(icon="close", on_click=_remove).props(
                        "round flat size=sm"
                    ).style("color:#ff3366").classes("flex-shrink-0")

        # Action-Button
        with ui.row().classes("w-full justify-end gap-3 mt-4"):
            ui.button(
                "Struktur uebernehmen und sortieren",
                icon="play_arrow",
                on_click=_submit_run,
            ).classes("ds-btn-success").props("unelevated no-caps")

    # ---- 4) Submit-Handler: Pending schreiben + Worker starten + Redirect ----
    def _submit_run() -> None:
        if not proposals:
            ui.notify("Keine Dokumente zum Sortieren.", type="warning")
            return

        run_id = uuid.uuid4().hex[:12]
        files_payload = []
        for item in proposals:
            target_dir = archive_base / item["proposed_folder_rel"]
            target_path = target_dir / item["proposed_name"]
            files_payload.append({
                "src": item["intake_path"],
                "original_name": item["original_name"],
                "target": str(target_path),
                "target_folder": str(target_dir),
                "target_name": item["proposed_name"],
            })

        pending = {
            "id": run_id,
            "created_at": _now_iso(),
            "files": files_payload,
        }
        pending_path = RUN_STATE_DIR / f"pending_{run_id}.json"
        _atomic_write_json(pending_path, pending)

        # Worker im Background starten — Output-Page pollt das State-File
        from . import output_page  # spaete Import-Aufloesung
        threading.Thread(
            target=output_page.run_worker,
            args=(run_id, pending),
            daemon=True,
        ).start()

        proposals.clear()
        _render_table.refresh()
        ui.navigate.to(f"/output?run={run_id}")

    # Initiales Render
    with table_container:
        _render_table()


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
