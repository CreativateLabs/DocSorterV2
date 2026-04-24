# Doc-Sorter MVP

Lokaler, privater Dokumenten-Assistent: heute sortieren, morgen analysieren, uebermorgen Fragen beantworten.

## Scope

Ein System das einen Datenraum ausliest, Dokumente inhaltlich versteht, nach eigener Taxonomie umbenennt und in eine definierte Ordnerstruktur verschiebt -- alles lokal, Finder-sichtbar, ohne externe APIs.

## Naming-Taxonomie

```
Dateiname:    Projekt_Kunden-Name_Dokumentenart_DD.MM.YY.ext
Ordner:       Archiv/Projekt/Kunde/Dokumentenart/Jahr/
```

## Ausbaustufen

1. **Basis** -- Lesen, Umbenennen, Sortieren, OCR, Review-Ordner, Logs, Undo
2. **Analyse** -- Zusammenfassung, Entitaeten-Extraktion, Duplikate, Volltext-Suche
3. **Prognose** -- Fristenueberwachung, Zahlungsmuster, Anomalien
4. **Decision Intelligence** -- Vertrags-Cockpit, Kunden-Akte, Compliance-Check
5. **Knowledge Graph** -- Semantische Suche, RAG, Beziehungsnetz

## Tech-Stack (lokal, kein Cloud-Zwang)

- Python 3.11+
- Tesseract OCR (eng + deu + sqi)
- pypdf, python-docx, Pillow, pytesseract
- langdetect
- Optional: Ollama (lokales LLM)

## Projektstruktur

```
src/
  reader.py        # PDF, DOCX, TXT, Bilder lesen + OCR
  classifier.py    # Dokumenttyp, Kunde, Land, Datum erkennen
  organizer.py     # Umbenennen + Verschieben + Ordnerstruktur
  logger.py        # Logs, State, Undo
  config.py        # Konfiguration laden
main.py            # CLI-Einstieg
config.yaml        # Einstellungen (Pfade, Taxonomie, Sprachen)
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install tesseract tesseract-lang poppler
python main.py --dry-run
```
