"""Pruefung: Unsichere Dokumente pruefen, korrigieren und freigeben.

Lern-Features (Enhancement 1–4):
  1. Feedback-Loop:     Korrektur senkt Keyword-Score des alten Typs
  2. Bestaetigung:      "Ja, korrekt" gibt Bonus-Hits fuer gematchte Keywords
  3. Neuer-Typ:         LLM-Vorschlag unbekannter Typen → "Jetzt anlegen"-Angebot
  4. Keyword-Qualitaet: decisive_hits werden gezaehlt wenn ≤3 Keywords entscheidend waren
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote as _url_quote

from nicegui import app, ui
from starlette.requests import Request
from starlette.responses import FileResponse, Response

from ...config import (
    get_country_keywords,
    get_document_type_keywords,
    get_known_customers,
    load_config,
    load_config_raw,
    save_config,
)
from ...organizer import build_filename, build_target_folder
from ...classifier import Classification
from ...user_profile import record_classification_feedback
from ...learning_engine import add_example as le_add_example, get_status as le_get_status
from ..theme import callout, empty_state, notify_error, page_header, status_badge


# ---------------------------------------------------------------------------
# Vorschau-Route: Dokumente aus _review/ sicher ausliefern
# ---------------------------------------------------------------------------

_PREVIEW_MIME: dict[str, str] = {
    ".pdf":  "application/pdf",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif":  "image/tiff",
    ".tiff": "image/tiff",
    ".txt":  "text/plain; charset=utf-8",
    ".md":   "text/plain; charset=utf-8",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
_PDF_EXT    = ".pdf"


@app.get("/api/review/preview")
async def _serve_preview(request: Request) -> Response:
    """Liefert eine Datei aus dem _review/-Ordner aus.

    Sicherheit:
    - Path wird mit resolve() kanonisiert (loest .. und Symlinks auf)
    - Datei muss sich unter einem _review-Verzeichnis befinden (exakter Part-Match)
    - Dateityp wird geprueft (nur bekannte Medientypen)
    """
    raw_path = request.query_params.get("path", "")
    if not raw_path:
        return Response(content="Kein Pfad angegeben", status_code=400)

    p = Path(raw_path).resolve()

    # Sicherheitscheck 1: Nach resolve() kein .. mehr moeglich.
    # Exakter Part-Vergleich: "_review" muss als eigenes Verzeichnis im Pfad liegen.
    if "_review" not in p.parts:
        return Response(content="Zugriff verweigert", status_code=403)

    # Sicherheitscheck 2: Datei muss existieren und eine echte Datei sein
    if not p.exists() or not p.is_file():
        return Response(content="Datei nicht gefunden", status_code=404)

    # Sicherheitscheck 3: Nur bekannte Dateitypen ausliefern
    ext = p.suffix.lower()
    if ext not in _PREVIEW_MIME:
        return Response(content="Dateityp nicht erlaubt", status_code=403)

    mime = _PREVIEW_MIME[ext]
    return FileResponse(str(p), media_type=mime, filename=p.name)


def _build_preview_dialog(rf: dict) -> None:
    """Oeffnet einen Dialog mit Dokumentvorschau."""
    path = rf["path"]
    ext  = Path(path).suffix.lower()
    enc  = _url_quote(path, safe="/")
    url  = f"/api/review/preview?path={enc}"

    with ui.dialog().props("maximized") as dlg, ui.card().classes("w-full h-full flex flex-col"):
        # Kopfzeile
        with ui.row().classes("w-full items-center justify-between mb-2 flex-shrink-0"):
            ui.label(rf["name"]).classes("font-semibold text-base truncate")
            ui.button(icon="close", on_click=dlg.close).props("flat round dense")

        # Inhalt
        if ext in _IMAGE_EXTS:
            # Bilder direkt anzeigen
            ui.image(url).classes("max-w-full max-h-full object-contain")

        elif ext == _PDF_EXT:
            # PDF im Browser-Viewer
            ui.html(
                f'<iframe src="{url}" '
                f'style="width:100%;height:100%;min-height:70vh;border:none;flex:1;" '
                f'title="Dokument-Vorschau"></iframe>',
                sanitize=False,
            ).classes("flex-1 w-full")

        elif ext == ".docx":
            # DOCX: Text-Vorschau aus Log + Download-Button
            preview_text = rf.get("text_preview", "")
            with ui.column().classes("flex-1 w-full gap-3 overflow-auto"):
                if preview_text:
                    ui.label("Textinhalt (extrahiert):").classes(
                        "text-xs font-semibold text-gray-500"
                    )
                    ui.textarea(value=preview_text).props(
                        "readonly outlined autogrow"
                    ).classes("w-full font-mono text-sm")
                else:
                    ui.label(
                        "Kein Textinhalt verfuegbar. Lade die Datei herunter um sie zu oeffnen."
                    ).classes("text-sm text-gray-500")
                ui.link("Datei herunterladen", url).classes("text-blue-500 text-sm")

        else:
            # Alle anderen: Text-Vorschau oder Download
            preview_text = rf.get("text_preview", "")
            with ui.column().classes("flex-1 w-full gap-3 overflow-auto"):
                if preview_text:
                    ui.textarea(value=preview_text).props(
                        "readonly outlined autogrow"
                    ).classes("w-full font-mono text-sm")
                else:
                    ui.label("Keine Vorschau verfuegbar.").classes("text-sm text-gray-500")
                ui.link("Datei herunterladen", url).classes("text-blue-500 text-sm")

    dlg.open()


# ---------------------------------------------------------------------------
# Daten laden
# ---------------------------------------------------------------------------

def _get_review_files(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    archive = Path(cfg["paths"]["archive"])
    review  = Path(cfg["paths"].get("review", str(archive / "_review")))
    logs_dir = Path(cfg["paths"]["logs"])

    if not review.exists():
        return []

    # stat() in separatem Schritt mit Fehlerbehandlung:
    # Dateien koennen zwischen rglob() und stat() geloescht werden (Race Condition)
    def _safe_mtime(f: Path) -> float:
        try:
            return f.stat().st_mtime
        except OSError:
            return 0.0

    files = sorted(
        [f for f in review.rglob("*") if f.is_file()],
        key=_safe_mtime,
        reverse=True,
    )

    # Log-Index: Dateiname → {classification, text_preview}
    log_index: dict[str, dict] = {}
    if logs_dir.exists():
        for log_file in logs_dir.glob("*.json"):
            try:
                data = json.loads(log_file.read_text(encoding="utf-8"))
                dest = Path(data.get("destination", ""))
                log_index[dest.name] = {
                    "cls":          data.get("classification", {}),
                    "text_preview": data.get("text_preview", ""),
                }
            except (json.JSONDecodeError, OSError):
                pass

    result = []
    for f in files:
        try:
            stat = f.stat()
        except OSError:
            continue  # Datei zwischen rglob() und stat() geloescht
        size_kb = stat.st_size / 1024
        size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
        log_entry = log_index.get(f.name, {})
        cls_data  = log_entry.get("cls", {})
        result.append({
            "path":             str(f),
            "name":             f.name,
            "size":             size_str,
            "date":             datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M"),
            "dokumentenart":    cls_data.get("dokumentenart", "unbekannt"),
            "kunde":            cls_data.get("kunde", "unbekannt"),
            "land":             cls_data.get("land", "unbekannt"),
            "confidence":       cls_data.get("confidence", 0),
            "gruende":          cls_data.get("unsicher_gruende", []),
            # Lern-System: gematchte Keywords + Dokumenttext für Training
            "matched_keywords": cls_data.get("matched_keywords", []),
            "text_preview":     log_entry.get("text_preview", ""),
        })
    return result


# ---------------------------------------------------------------------------
# Aktionen
# ---------------------------------------------------------------------------

def _reclassify_and_move(
    file_path: str,
    dokumentenart: str,
    kunde: str,
    land: str,
    cfg: dict[str, Any],
) -> str:
    source = Path(file_path)
    if not source.exists():
        return f"Datei nicht gefunden: {source}"

    archive = Path(cfg["paths"]["archive"])

    # Originales Datei-Datum verwenden (Aenderungszeit) statt heute.
    # Dokument-Datum soll dem echten Dokumentdatum entsprechen, nicht dem Review-Datum.
    try:
        file_dt = datetime.fromtimestamp(source.stat().st_mtime)
    except OSError:
        file_dt = datetime.now()

    cls = Classification(
        dokumentenart=dokumentenart or "unbekannt",
        kunde=kunde or "unbekannt",
        land=land or "unbekannt",
        datum=file_dt.strftime("%d.%m.%y"),
        datum_full=file_dt.strftime("%d.%m.%Y"),
        jahr=file_dt.strftime("%Y"),
        unsicher=False,
    )

    target_folder = build_target_folder(archive, cls, is_review=False)
    new_name = build_filename(cls, source.suffix)
    target = target_folder / new_name

    target_folder.mkdir(parents=True, exist_ok=True)

    # Kollision deterministisch mit Zaehler loesen (nicht Zeitstempel — nicht unique!)
    if target.exists():
        stem   = target.stem
        suffix = target.suffix
        counter = 1
        while target.exists() and counter <= 999:
            target = target_folder / f"{stem}_{counter:03d}{suffix}"
            counter += 1

    try:
        shutil.move(str(source), str(target))
        return f"Verschoben: {source.name} -> {target}"
    except OSError as e:
        return f"Fehler: {e}"


def _move_to_inbox(file_path: str, cfg: dict[str, Any]) -> str:
    source = Path(file_path)
    if not source.exists():
        return f"Datei nicht gefunden: {source}"

    inbox = Path(cfg["paths"]["inbox"])
    inbox.mkdir(parents=True, exist_ok=True)
    target = inbox / source.name

    if target.exists():
        stamp = datetime.now().strftime("%H%M%S")
        target = inbox / f"{source.stem}_{stamp}{source.suffix}"

    try:
        shutil.move(str(source), str(target))
        return f"Zurueck in Inbox: {source.name}"
    except OSError as e:
        return f"Fehler: {e}"


def _add_doctype_to_config(new_type: str) -> None:
    """Neuen Dokumententyp dauerhaft in Config speichern + Keywords auto-ausfuellen."""
    try:
        from .config_editor import _lookup_keywords
        cfg_raw = load_config_raw()
        doc_types: dict = cfg_raw.setdefault("document_types", {})
        if new_type in doc_types:
            return
        kw = _lookup_keywords(new_type)
        if not kw:
            kw = {"keywords_de": [new_type], "keywords_en": [], "keywords_sq": []}
        doc_types[new_type] = kw
        save_config(cfg_raw)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("_add_doctype_to_config fehlgeschlagen: %s", exc)


# ---------------------------------------------------------------------------
# UI — einzelne Review-Karte
# ---------------------------------------------------------------------------

def _build_review_card(
    rf: dict,
    doc_types: list[str],
    customers: list[str],
    countries: list[str],
    cfg: dict[str, Any],
    on_moved: Any,
    selected_paths: set[str] | None = None,
    on_toggle: Any = None,
) -> None:
    orig_art = rf["dokumentenart"]
    matched_kws = rf.get("matched_keywords", [])

    # Erkennen ob die Dokumentenart ein unbekannter LLM-Vorschlag ist
    is_new_suggestion = (
        orig_art not in ("unbekannt", "")
        and orig_art not in doc_types
    )

    with ui.card().classes("ds-card w-full"):

        # ── Checkbox fuer Batch-Auswahl ───────────────────────────────────
        if selected_paths is not None and on_toggle is not None:
            with ui.row().classes("items-center gap-2 mb-2 -mb-1"):
                cb = ui.checkbox(
                    value=(rf["path"] in selected_paths),
                ).props("dense dark")
                cb.on_value_change(
                    lambda e, p=rf["path"]: on_toggle(p, e.value)
                )
                ui.label("Fuer Stapel-Aktion ausw\u00e4hlen").style(
                    "font-size:0.72rem;color:var(--ds-text-3)"
                )

        # ── Neuer-Typ-Banner (Enhancement 3) ──────────────────────────────
        if is_new_suggestion:
            with ui.element("div").classes(
                "flex items-center gap-3 bg-amber-50 dark:bg-amber-900/30 "
                "border border-amber-300 dark:border-amber-600 rounded-lg px-3 py-2 mb-3"
            ):
                ui.icon("auto_awesome").classes("text-amber-500 flex-shrink-0")
                with ui.column().classes("gap-0 flex-1"):
                    ui.label("Neue Dokumentenart erkannt").classes(
                        "text-xs font-bold text-amber-700 dark:text-amber-300"
                    )
                    ui.label(
                        f'Doc-Sorter hat "{orig_art}" erkannt — dieser Typ ist noch nicht in deiner Config.'
                    ).classes("text-xs text-amber-600 dark:text-amber-400")

                def _do_add_type(t: str = orig_art) -> None:
                    _add_doctype_to_config(t)
                    ui.notify(
                        f'"{t}" wurde zur Config hinzugefügt und mit Keywords befüllt.',
                        type="positive",
                        position="top",
                    )

                ui.button("Jetzt anlegen", on_click=_do_add_type, icon="add_circle").classes(
                    "ds-btn-secondary text-xs"
                ).props("size=sm")

        # ── Datei-Info ─────────────────────────────────────────────────────
        with ui.row().classes("w-full items-start gap-4"):
            with ui.column().classes("flex-1 gap-1"):
                with ui.row().classes("items-center gap-3"):
                    ui.label(rf["name"]).classes("font-semibold text-base")
                    ui.button(
                        "Vorschau",
                        icon="visibility",
                        on_click=lambda r=rf: _build_preview_dialog(r),
                    ).props("flat dense no-caps").classes(
                        "text-xs text-blue-600 dark:text-blue-400"
                    )
                with ui.row().classes("gap-4 text-sm text-gray-500"):
                    ui.label(f"Größe: {rf['size']}")
                    ui.label(f"Datum: {rf['date']}")
                    if rf["confidence"]:
                        variant = (
                            "success" if rf["confidence"] > 0.7
                            else "warning" if rf["confidence"] > 0.4
                            else "error"
                        )
                        status_badge(f"Sicherheit: {rf['confidence']:.0%}", variant)

                if rf["gruende"]:
                    with ui.row().classes("gap-2 mt-1"):
                        for g in rf["gruende"]:
                            status_badge(g, "warning")

                # Gematchte Keywords anzeigen (Enhancement 2/4)
                if matched_kws:
                    with ui.row().classes("items-center gap-1.5 mt-2 flex-wrap"):
                        ui.label("Erkannt durch:").classes("text-xs text-gray-400 flex-shrink-0")
                        for kw in matched_kws[:8]:
                            ui.label(kw).classes(
                                "text-xs px-2 py-0.5 rounded-full "
                                "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300"
                            )

            # ── Korrektur-Felder ───────────────────────────────────────────
            with ui.column().classes("gap-2 min-w-[300px]"):
                sel_art = ui.select(
                    label="Dokumentenart",
                    options=doc_types + (
                        [orig_art] if is_new_suggestion else []
                    ) + ["unbekannt"],
                    value=orig_art,
                    with_input=True,
                    new_value_mode="add-unique",
                ).classes("w-full ds-input")

                sel_kunde = ui.select(
                    label="Kunde",
                    options=customers + ["unbekannt"],
                    value=rf["kunde"],
                    with_input=True,
                    new_value_mode="add-unique",
                ).classes("w-full ds-input")

                sel_land = ui.select(
                    label="Land",
                    options=countries + ["unbekannt"],
                    value=rf["land"],
                ).classes("w-full ds-input")

                # ── Aktions-Buttons ────────────────────────────────────────
                with ui.row().classes("gap-2"):

                    def do_confirm(
                        path=rf["path"],
                        orig=orig_art,
                        art=sel_art,
                        k=sel_kunde,
                        la=sel_land,
                        mkws=matched_kws,
                        txt=rf.get("text_preview", ""),
                    ) -> None:
                        """Bestätigen: Klassifikation korrekt oder korrigiert."""
                        result = _reclassify_and_move(path, art.value, k.value, la.value, cfg)
                        if "Fehler" in result:
                            ui.notify(result, type="negative")
                            return

                        is_same = art.value == orig

                        # 1. Keyword-Feedback-Loop (Enhancement 1 + 2)
                        record_classification_feedback(
                            old_type=orig,
                            new_type=art.value,
                            matched_keywords=mkws,
                            is_confirmation=is_same,
                        )

                        # 2. Lern-Engine: Trainingsbeispiel hinzufügen (neu)
                        if txt and art.value not in ("unbekannt", ""):
                            le_add_example(
                                text=txt,
                                label=art.value,
                                source="review",
                                confidence=1.0,
                            )

                        # 3. Neuer Typ → dauerhaft in Config speichern (Enhancement 3)
                        if art.value not in doc_types and art.value not in ("unbekannt", ""):
                            _add_doctype_to_config(art.value)
                            ui.notify(
                                f'"{art.value}" wurde als neuer Dokumententyp gespeichert.',
                                type="info",
                                position="top",
                            )

                        if is_same:
                            ui.notify(
                                "✓ Bestätigt — Lern-Engine & Profil aktualisiert",
                                type="positive",
                            )
                        else:
                            ui.notify(
                                f"✓ Korrektur gelernt: '{orig}' → '{art.value}'",
                                type="positive",
                            )
                        on_moved()

                    def do_back_to_inbox(path=rf["path"]) -> None:
                        result = _move_to_inbox(path, cfg)
                        if "Fehler" in result:
                            ui.notify(result, type="negative")
                        else:
                            ui.notify(result, type="positive")
                            on_moved()

                    ui.button(
                        "Ins Archiv", on_click=do_confirm, icon="archive"
                    ).classes("ds-btn-success")
                    ui.button(
                        "Zurück in Inbox", on_click=do_back_to_inbox, icon="inbox"
                    ).classes("ds-btn-ghost")


# ---------------------------------------------------------------------------
# Haupt-Einstiegspunkt
# ---------------------------------------------------------------------------

def build() -> None:
    """Pruefungs-Seite aufbauen."""
    cfg = load_config()
    review_files = _get_review_files(cfg)

    page_header(
        "Pruefung",
        f"{len(review_files)} Dokumente warten auf manuelle Pruefung. "
        "Korrigiere die Erkennung und gib Dokumente fuer das Archiv frei.",
    )

    # Lern-Engine Status-Info
    le_status = le_get_status()
    if not le_status["embed_installed"] or not le_status["sklearn_installed"]:
        _missing = []
        if not le_status["embed_installed"]:
            _missing.append("sentence-transformers")
        if not le_status["sklearn_installed"]:
            _missing.append("scikit-learn")
        callout(
            f"Lern-Engine nicht installiert. Führe aus: pip install {' '.join(_missing)}"
            " — danach lernt Doc-Sorter direkt aus deinen Dokumenten.",
            "warning", "download",
        )
    elif le_status["available"]:
        callout(
            f"Lern-Engine aktiv · Trainiert auf {le_status['trained_on']} Dokumenten · "
            f"{len(le_status['classes'])} Dokumentenarten · "
            f"{le_status['new_since_train']}/{le_status['retrain_threshold']} neue Beispiele bis zum nächsten Auto-Training"
            + (f" · Genauigkeit: {le_status['cv_accuracy']:.0%}" if le_status.get('cv_accuracy') else ""),
            "positive", "psychology",
        )
    elif le_status["total_examples"] > 0:
        needed = le_status["retrain_threshold"] - le_status["new_since_train"]
        callout(
            f"Lern-Engine sammelt Daten · {le_status['total_examples']} Beispiele gespeichert · "
            f"Noch {needed} Bestätigungen bis zum ersten automatischen Training.",
            "info", "model_training",
        )
    else:
        callout(
            "Jede Bestätigung oder Korrektur wird zum Trainingsbeispiel für die eigene Lern-Engine. "
            "Ab 10 Beispielen trainiert sie sich automatisch und wird mit der Zeit unabhängig von externer KI.",
            "info", "school",
        )

    if not review_files:
        empty_state(
            "check_circle",
            "Alles erledigt!",
            "Keine Dokumente zur Pruefung vorhanden.",
        )
        return

    doc_types = list(get_document_type_keywords(cfg).keys())
    customers  = [c["name"] for c in get_known_customers(cfg)]
    countries  = list(get_country_keywords(cfg).keys())

    # ── Batch-Auswahl-State ────────────────────────────────────────────────
    selected_paths: set[str] = set()

    counter_label = ui.label(f"{len(review_files)} Dokumente").classes("text-sm text-gray-500")

    # ── Bulk-Action-Bar (erscheint wenn Dokumente ausgewaehlt) ─────────────
    @ui.refreshable
    def bulk_bar() -> None:
        if not selected_paths:
            return
        with ui.element("div").style(
            "position:sticky;top:0;z-index:50;"
            "background:linear-gradient(135deg,rgba(0,212,255,0.12),rgba(124,58,237,0.08));"
            "border:1px solid rgba(0,212,255,0.35);"
            "border-radius:12px;padding:10px 14px;margin-bottom:10px;"
            "backdrop-filter:blur(10px);"
            "box-shadow:0 4px 20px rgba(0,212,255,0.15)"
        ):
            with ui.row().classes("items-center gap-3 w-full flex-wrap"):
                ui.icon("checklist").style("color:#00d4ff;font-size:1.2rem")
                ui.label(f"{len(selected_paths)} Dokument(e) ausgew\u00e4hlt").style(
                    "font-size:0.9rem;font-weight:700;color:var(--ds-text);flex:1"
                )
                ui.button(
                    "Alle markieren",
                    icon="done_all",
                    on_click=lambda: _bulk_select_all(),
                ).props("flat dense no-caps").classes("text-xs").tooltip(
                    "Alle sichtbaren Dokumente f\u00fcr Stapel-Aktion markieren"
                )
                ui.button(
                    "Abw\u00e4hlen",
                    icon="clear",
                    on_click=lambda: _bulk_deselect_all(),
                ).props("flat dense no-caps").classes("text-xs").tooltip(
                    "Auswahl aufheben"
                )
                ui.button(
                    "Als korrekt ins Archiv",
                    icon="archive",
                    on_click=lambda: _bulk_confirm(),
                ).classes("ds-btn-success").tooltip(
                    "Alle markierten Dokumente mit ihrer aktuellen Klassifikation ins Archiv verschieben. "
                    "Lern-Engine bekommt positives Feedback."
                )
                ui.button(
                    "Zur\u00fcck in Inbox",
                    icon="inbox",
                    on_click=lambda: _bulk_back_to_inbox(),
                ).classes("ds-btn-ghost").tooltip(
                    "Alle markierten Dokumente zur\u00fcck in die Inbox verschieben (nochmal verarbeiten)"
                )

    def on_toggle(path: str, checked: bool) -> None:
        if checked:
            selected_paths.add(path)
        else:
            selected_paths.discard(path)
        bulk_bar.refresh()

    def _bulk_select_all() -> None:
        for rf in review_files:
            selected_paths.add(rf["path"])
        refresh()

    def _bulk_deselect_all() -> None:
        selected_paths.clear()
        refresh()

    def _bulk_confirm() -> None:
        """Alle markierten Dokumente mit aktueller Klassifikation ins Archiv."""
        to_move = [rf for rf in review_files if rf["path"] in selected_paths]
        if not to_move:
            return
        ok, err = 0, 0
        last_err: str = ""
        for rf in to_move:
            result = _reclassify_and_move(
                rf["path"], rf["dokumentenart"], rf["kunde"], rf["land"], cfg,
            )
            if "Fehler" in result:
                err += 1
                last_err = result
                continue
            ok += 1
            # Lern-Feedback: Bestaetigung
            try:
                record_classification_feedback(
                    old_type=rf["dokumentenart"],
                    new_type=rf["dokumentenart"],
                    matched_keywords=rf.get("matched_keywords", []),
                    is_confirmation=True,
                )
                if rf.get("text_preview") and rf["dokumentenart"] not in ("unbekannt", ""):
                    le_add_example(
                        text=rf["text_preview"],
                        label=rf["dokumentenart"],
                        source="review_bulk",
                        confidence=1.0,
                    )
            except Exception:
                pass
        selected_paths.clear()
        if err and ok == 0:
            notify_error(last_err, prefix="Stapel-Aktion fehlgeschlagen: ")
        elif err:
            ui.notify(
                f"\u2713 {ok} ins Archiv, {err} konnten nicht verschoben werden.",
                type="warning", position="top", multi_line=True,
            )
        else:
            ui.notify(
                f"\u2713 {ok} Dokument(e) ins Archiv verschoben \u2014 Lern-Engine aktualisiert",
                type="positive", position="top",
            )
        refresh()

    def _bulk_back_to_inbox() -> None:
        to_move = [rf for rf in review_files if rf["path"] in selected_paths]
        if not to_move:
            return
        ok, err = 0, 0
        for rf in to_move:
            result = _move_to_inbox(rf["path"], cfg)
            if "Fehler" in result:
                err += 1
            else:
                ok += 1
        selected_paths.clear()
        if err:
            ui.notify(f"{ok} zur\u00fcck in Inbox, {err} Fehler", type="warning")
        else:
            ui.notify(f"{ok} Dokument(e) zur\u00fcck in Inbox", type="positive")
        refresh()

    # Bulk-Bar-Slot + Cards-Container
    bulk_bar()
    container = ui.column().classes("w-full gap-3")

    def refresh() -> None:
        nonlocal review_files
        review_files = _get_review_files(cfg)
        counter_label.text = f"{len(review_files)} Dokumente"
        # Entfernte Pfade aus Selection cleanen
        valid_paths = {rf["path"] for rf in review_files}
        selected_paths.intersection_update(valid_paths)
        bulk_bar.refresh()
        container.clear()
        with container:
            if not review_files:
                empty_state(
                    "check_circle",
                    "Alle Dokumente verarbeitet!",
                    "Keine weiteren Pruefungen noetig.",
                )
                return
            for rf in review_files:
                _build_review_card(
                    rf, doc_types, customers, countries, cfg, refresh,
                    selected_paths=selected_paths,
                    on_toggle=on_toggle,
                )

    refresh()

    ui.button("Aktualisieren", on_click=refresh, icon="refresh").classes("ds-btn-secondary mt-4")
