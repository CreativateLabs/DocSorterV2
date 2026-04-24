# Skill: doc-pipeline

Erklärt und debuggt die Dokument-Klassifikations-Pipeline von Doc-Sorter.

## Trigger

- Nutzer fragt "warum wird das Dokument falsch klassifiziert"
- Nutzer fragt nach der Pipeline / dem Verarbeitungsfluss
- `/doc-pipeline`
- Nach Änderungen an `classifier.py`, `learning_engine.py`, `llm_classifier.py`, `organizer.py`

## Pipeline-Überblick

```
📥 Datei in Inbox
    ↓
reader.py          → Text extrahieren (PDF/DOCX/IMG/TXT)
    ↓
classifier.py      → Keywords → Dokumentenart + Confidence
    ↓
learning_engine.py → Embedding + LogReg predict (wenn trainiert + confidence ≥ 0.70)
    ↓
llm_classifier.py  → Cloud/lokal LLM (nur wenn alles andere unsicher)
    ↓
organizer.py       → Dateinamen + Zielordner berechnen + Datei verschieben
    ↓
brain.py           → Rechnungen/Todos/Feed-Einträge erzeugen
```

## Wichtige Schwellenwerte

| Wert | Konstante | Datei |
|------|-----------|-------|
| Lern-Engine Konfidenz-Schwelle | `_HIGH_CONFIDENCE = 0.70` | learning_engine.py |
| Mindest-Beispiele pro Klasse | `_MIN_EXAMPLES_PER_CLASS = 2` | learning_engine.py |
| Auto-Retrain Schwelle | `_RETRAIN_THRESHOLD = 10` | learning_engine.py |
| Unsichere Klassifikation ab | `confidence < 0.4` | brain.py |

## Dateinamen-Taxonomie

```
{dokumentenart}_{kunde}_{land}_{datum}.{ext}
Beispiel: rechnung_gasag_deutschland_15.03.25.pdf

Ordner: archiv/dokumentenart/land/kunde/jahr/
```

## Debug-Checkliste bei falsch klassifizierten Dokumenten

1. Hat die Dokumentenart Keywords in `config.yaml` → `document_types`?
2. Hat der Kunde Aliases in `known_customers`?
3. Welche Keywords haben gematcht? → `Classification.matched_keywords`
4. Ist die Lern-Engine trainiert? → `learning_engine.get_status()`
5. Ist ein LLM Provider aktiv? → `llm.enabled` in config.yaml
6. Ist das Dokument im `_review/` Ordner gelandet? → `classification.unsicher == True`

## Konfigurationsregel

**WICHTIG: Niemals bestehende Lern-Mechanismen entfernen.**
Das Hit-Counter-System (`keyword_scores` in user_profile) und die
Learning-Engine-Daten dürfen nur erweitert, nie gelöscht werden.
