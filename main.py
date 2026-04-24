#!/usr/bin/env python3
"""Doc-Sorter MVP -- Dokumente auslesen, umbenennen, sortieren.

Nutzung:
  python main.py --dry-run          # Nur zeigen, nichts verschieben
  python main.py --live             # Echt ausfuehren
  python main.py --undo             # Letzte Verschiebung rueckgaengig
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.config import (
    get_country_keywords,
    get_document_type_keywords,
    get_file_types,
    get_known_customers,
    get_ocr_languages,
    load_config,
)
from src.classifier import classify
from src.log_setup import setup_logging
from src.logger import LogManager, StateManager, file_hash, undo_last
from src.organizer import move_file
from src.prerequisites import print_check_results, run_all_checks
from src.reader import read_text

logger = logging.getLogger(__name__)


def print_header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def process_file(
    file_path: Path,
    cfg: dict,
    state: StateManager,
    log_mgr: LogManager,
    dry_run: bool,
    file_num: int = 0,
    total_files: int = 0,
) -> None:
    """Eine einzelne Datei verarbeiten."""
    progress = f"[{file_num}/{total_files}] " if total_files else ""

    # Dateiendung pruefen
    allowed = get_file_types(cfg)
    if file_path.suffix.lower() not in allowed:
        print(f"  {progress}SKIP (nicht unterstuetzt): {file_path.name}")
        return

    # Idempotenz: schon verarbeitet?
    sha = file_hash(file_path)
    if state.is_processed(sha):
        print(f"  {progress}SKIP (bereits verarbeitet): {file_path.name}")
        return

    print(f"\n  {progress}Datei: {file_path.name}")

    # 1. Text lesen
    ocr_langs = get_ocr_languages(cfg)
    ocr_cfg = cfg.get("ocr", {})
    text = read_text(
        file_path,
        ocr_languages=ocr_langs,
        ocr_dpi=ocr_cfg.get("dpi", 200),
        max_pages=ocr_cfg.get("max_pages", 5),
    )
    text_found = len(text.strip()) > 0
    print(f"  Text gefunden: {'ja' if text_found else 'nein (Scan/OCR?)'}")
    if text_found:
        print(f"  Text-Laenge: {len(text)} Zeichen")

    # 2. Klassifizieren
    doc_type_kw = get_document_type_keywords(cfg)
    customers = get_known_customers(cfg)
    country_kw = get_country_keywords(cfg)
    confidence_cfg = cfg.get("confidence", {})

    classification = classify(
        text=text,
        document_type_keywords=doc_type_kw,
        known_customers=customers,
        country_keywords=country_kw,
        min_text_length=confidence_cfg.get("min_text_length", 30),
        uncertain_fields=confidence_cfg.get("uncertain_if_missing", ["kunde", "dokumentenart"]),
    )

    print(f"  Dokumentenart: {classification.dokumentenart}")
    print(f"  Kunde:         {classification.kunde}")
    print(f"  Land:          {classification.land}")
    print(f"  Datum:         {classification.datum}")
    print(f"  Sprache:       {classification.sprache}")
    print(f"  Confidence:    {classification.confidence:.0%}")
    if classification.unsicher:
        print(f"  UNSICHER:      {', '.join(classification.unsicher_gruende)}")

    # 2b. LLM-Fallback bei unsicherer Klassifikation
    llm_cfg = cfg.get("llm", {})
    if llm_cfg.get("enabled", False):
        use_llm = not llm_cfg.get("fallback_only", True) or classification.unsicher
        if use_llm:
            try:
                from src.llm_classifier import classify_with_llm
                print(f"  LLM-Klassifikation ({llm_cfg.get('provider', 'openai')})...")
                llm_result = classify_with_llm(
                    text=text,
                    cfg=cfg,
                    provider=llm_cfg.get("provider", "openai"),
                    model=llm_cfg.get("model", "") or None,
                    use_cache=llm_cfg.get("cache_results", True),
                )
                if llm_result.confidence > classification.confidence:
                    # LLM-Ergebnis ist besser -> uebernehmen
                    classification.dokumentenart = llm_result.dokumentenart
                    classification.kunde = llm_result.kunde
                    classification.land = llm_result.land
                    if llm_result.datum:
                        classification.datum_full = llm_result.datum
                        parts = llm_result.datum.split(".")
                        if len(parts) == 3:
                            dd, mm, yyyy = parts
                            classification.datum = f"{dd}.{mm}.{yyyy[-2:]}"
                            classification.jahr = yyyy
                    classification.confidence = llm_result.confidence
                    classification.unsicher = False
                    classification.unsicher_gruende = []
                    print(f"  LLM uebernommen: art={llm_result.dokumentenart} kunde={llm_result.kunde} ({llm_result.confidence:.0%})")
                    if llm_result.zusammenfassung:
                        print(f"  Zusammenfassung: {llm_result.zusammenfassung[:100]}")
                elif llm_result.cached:
                    print(f"  LLM (Cache): {llm_result.dokumentenart} ({llm_result.confidence:.0%})")
                else:
                    print(f"  LLM nicht besser: {llm_result.confidence:.0%} vs {classification.confidence:.0%}")
            except Exception as e:
                print(f"  LLM-Fehler: {e}")

    if classification.unsicher:
        print(f"  -> Geht in _review/")

    # 3. Verschieben
    archive_base = Path(cfg["paths"]["archive"])
    target_path, moved = move_file(
        source=file_path,
        archive_base=archive_base,
        classification=classification,
        dry_run=dry_run,
    )

    if dry_run:
        print(f"  -> WUERDE verschieben nach: {target_path}")
        print(f"     DRY RUN -- keine Aenderung")
    elif moved:
        # Log schreiben
        log_path = log_mgr.write_log(
            source=file_path,
            destination=target_path,
            classification=classification,
            sha256=sha,
            text_preview=text,
        )
        # State aktualisieren
        state.mark_processed(sha, str(file_path), str(target_path), str(log_path))
        print(f"  -> Verschoben nach: {target_path}")
        print(f"     Log: {log_path.name}")
    else:
        print(f"  -> FEHLER: Datei konnte nicht verschoben werden")


def main() -> None:
    parser = argparse.ArgumentParser(description="Doc-Sorter MVP")
    parser.add_argument("--config", default=None, help="Pfad zur config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Nur zeigen, nichts verschieben")
    parser.add_argument("--live", action="store_true", help="Echt ausfuehren (ueberschreibt dry_run_default)")
    parser.add_argument("--undo", action="store_true", help="Letzte Verschiebung rueckgaengig")
    parser.add_argument("--check", action="store_true", help="Nur System-Voraussetzungen pruefen")
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug-Output")
    args = parser.parse_args()

    # Config laden
    config_path = Path(args.config) if args.config else None
    cfg = load_config(config_path)

    # Logging einrichten
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logs_dir = Path(cfg["paths"]["logs"])
    setup_logging(log_dir=logs_dir, level=log_level)

    # System-Check
    if args.check:
        ocr_langs = get_ocr_languages(cfg)
        results = run_all_checks(ocr_langs)
        all_ok = print_check_results(results)
        raise SystemExit(0 if all_ok else 1)

    # Pfade
    inbox = Path(cfg["paths"]["inbox"])
    archive = Path(cfg["paths"]["archive"])
    state_path = archive / "_state.json"

    # Ordner sicherstellen
    inbox.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)

    # Undo?
    if args.undo:
        result = undo_last(logs_dir, inbox, state_path)
        print(result)
        return

    # State & Logs initialisieren
    state = StateManager(state_path)
    log_mgr = LogManager(logs_dir)

    # Dateien im Inbox finden
    max_files = cfg.get("processing", {}).get("max_files_per_run", 100)
    files = sorted([f for f in inbox.rglob("*") if f.is_file()])[:max_files]

    if not files:
        print(f"\nKeine Dateien in: {inbox}")
        print("Lege Dokumente dort ab und starte erneut.")
        return

    if args.live:
        dry_run = False
    elif args.dry_run:
        dry_run = True
    else:
        dry_run = cfg.get("processing", {}).get("dry_run_default", True)

    print_header("Doc-Sorter MVP")
    print(f"  Inbox:    {inbox}")
    print(f"  Archiv:   {archive}")
    print(f"  Modus:    {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"  Dateien:  {len(files)}")

    for i, file_path in enumerate(files, 1):
        process_file(file_path, cfg, state, log_mgr, dry_run, file_num=i, total_files=len(files))

    print_header("Fertig")
    print(f"  Dateien verarbeitet: {len(files)}")
    if dry_run:
        print(f"  Hinweis: DRY RUN -- nichts wurde verschoben.")
        print(f"  Starte mit 'python main.py --live' fuer echte Ausfuehrung.")
    print(f"\n  Im Finder pruefen:")
    print(f"    Input:  {inbox}")
    print(f"    Output: {archive}")
    print(f"    Logs:   {logs_dir}")


if __name__ == "__main__":
    main()
