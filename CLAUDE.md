# DocSorterV2 — Projektgedächtnis

> **Dieses Repo ist V2** — ein frisch aufgesetzter Fork von `doc-sorter-mvp` (v0.7.0)
> mit Fokus ausschließlich auf den Kernprozess: **Input → Struktur vorschlagen →
> Bestätigen → Output/Archiv**. Alles andere (Chat, Sprachmemo, Kalender, Finanzen,
> Bank, Nachrichten) ist **versteckt, nicht gelöscht** — wird bei Bedarf aus dem
> alten Repo zurückgezogen.

## Was ist dieses Projekt?

**DocSorterV2** ist ein lokales Dokumenten-Verwaltungs-System. Der Kern:
- Dokumente **auslesen** (PDF, DOCX, Bilder via OCR, TXT)
- Dokumente **umbenennen** nach festem Schema (`art_kunde_land_datum.ext`)
- Dokumente **sortieren** in eine strukturierte Ordnerhierarchie
- **Selbst lernen** aus Nutzer-Feedback (je mehr Korrekturen, desto besser)

UI-Gerüst: Header-Navigation (Input | Output | Profil), keine Sidebar, Onboarding im Fullscreen, Dark-Theme als Default.

---

## Die wichtigsten Regeln

### Regel 1 — Niemals bestehende Lern-Mechanismen entfernen
> Das Hit-Counter-System, die Keyword-Scores und alle Learning-Engine-Daten
> dürfen nur erweitert oder umgebaut werden — niemals gelöscht.
> **Nur hinzufügen oder umstrukturieren, nie entfernen.**

### Regel 2 — Jedes Update muss sofort auch online downloadbar sein
> Jede Änderung am Code, die für Endnutzer sichtbar ist (Bugfix, Feature,
> Berechtigung, UI), MUSS über einen neuen Release auch in der
> **downloadbaren Binary auf der Landing-Page** landen. Niemals nur lokal
> oder nur auf GitHub.
>
> **Release-Schritte (ab v0.6.7 vollautomatisch):**
> 1. `src/version.py` → neue Version (z. B. `0.6.7`)
> 2. Commit + Push auf `main`
> 3. `git tag vX.Y.Z && git push --tags`
> 4. Rest erledigt CI automatisch: Build macOS+Windows → GitHub Release →
>    `landing/version.json` + Binaries in `landing/downloads/` via LFS →
>    Push auf `main` → Netlify deployed → Download auf Landing-Page aktuell.
>
> Siehe `.github/workflows/release.yml` (Job `update-landing`).

---

## Tech Stack (Kurzfassung)

| Schicht | Technologie |
|---------|-------------|
| UI/Dashboard | NiceGUI ≥ 2.0 (Python → Browser, ASGI) |
| Dokument-Lesen | pypdf, python-docx, pytesseract (OCR), pdf2image |
| Klassifikation Stufe 1 | Keyword-Matching (classifier.py, immer aktiv) |
| Klassifikation Stufe 2 | sentence-transformers + scikit-learn LogReg (learning_engine.py) |
| Klassifikation Stufe 3 | OpenAI / Anthropic / Ollama (llm_classifier.py, optional) |
| Datei-Organisation | organizer.py (pathlib + shutil, atomic writes) |
| Konfiguration | config.yaml + config.py (_DEFAULTS dict) |
| Datenspeicher | JSON-Dateien (atomic: temp + os.replace) |
| HTTP | httpx (Ollama, externe APIs) |
| Inbox-Watch | watchdog |
| Sprache | Python ≥ 3.10 |

---

## Klassifikations-Pipeline

```
reader.py → classifier.py → learning_engine.py → llm_classifier.py → organizer.py → brain.py
```

Schwellenwerte:
- `_HIGH_CONFIDENCE = 0.70` — ab wann Lern-Engine Ergebnis nutzen
- `_MIN_EXAMPLES_PER_CLASS = 2` — Minimum pro Dokumentenart
- `_RETRAIN_THRESHOLD = 10` — neue Beispiele bis Auto-Training
- `confidence < 0.4` → Dokument geht in `_review/`

---

## Dateinamen-Taxonomie

```
Datei:   {dokumentenart}_{kunde}_{land}_{datum}.{ext}
Ordner:  archiv/{dokumentenart}/{land}/{kunde}/{jahr}/
Review:  archiv/_review/{dokumentenart}/
```

---

## Wichtige Datei-Struktur

```
src/
├── config.py              — Config laden, _DEFAULTS dict, load_config_raw(), save_config()
├── classifier.py          — Keyword-Klassifikation, Classification dataclass
├── llm_classifier.py      — OpenAI/Anthropic/Ollama, LLMResult, _safe_float()
├── learning_engine.py     — sentence-transformers + LogReg, atomic JSON writes
├── organizer.py           — safe_name(), build_filename(), move_file()
├── user_profile.py        — Hit-Counter, Keyword-Scores, atomic _save()
├── brain.py               — Rechnungen → Todos → Feed
├── reader.py              — Text-Extraktion (PDF/DOCX/IMG/TXT)
├── watcher.py             — Inbox-Überwachung (watchdog)
└── dashboard/
    ├── layout.py          — NiceGUI Routen, 3-Panel Layout, Sidebar
    ├── theme.py           — callout(), page_header(), section_title(), status_badge()
    └── pages/
        ├── system.py      — System-Status, Lern-Engine, KI-Anbieter-Kacheln
        ├── review.py      — Prüfungs-Seite für unsichere Dokumente
        ├── keywords_hub.py — Schlagwörter, Kunden, Länder verwalten
        ├── config_editor.py — YAML-Konfigurations-Editor
        └── ...            — weitere Seiten
```

---

## NiceGUI — Kritische Muster

### 1. Closure-Bug in Schleifen (häufigster Fehler!)
```python
# FALSCH:
for item in items:
    ui.button(on_click=lambda: do(item))  # immer letzter item!

# RICHTIG:
for item in items:
    ui.button(on_click=lambda x=item: do(x))  # sofortiges Binden
```

### 2. Innere Hilfsfunktionen VOR Lambda-Referenzen definieren
```python
@ui.refreshable
def render():
    def _remove(idx):      # ← ZUERST definieren
        items.pop(idx)
        render.refresh()

    for i, _ in enumerate(items):
        ui.button(on_click=lambda idx=i: _remove(idx))  # dann benutzen
```

### 3. Refreshable-Funktion aufrufen
```python
@ui.refreshable
def my_section():
    ...

my_section()  # ← nicht vergessen!
```

---

## Config-Management-Regeln

1. Neue Config-Keys **immer** in `_DEFAULTS` in `config.py` eintragen
2. Zugriff **immer** mit `.get()` + Fallback: `cfg.get("llm", {}).get("key", "")`
3. Schreiben über `load_config_raw()` → ändern → `save_config()`
4. Nie `load_config()` zum Schreiben benutzen (expandiert Pfade!)

---

## Atomic Write — Pflicht für alle JSON-Stores

```python
# IMMER so für kritische JSON-Dateien:
import os, tempfile
tmp_fd, tmp_path = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
try:
    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))
    os.replace(tmp_path, p)  # atomic!
except Exception:
    os.unlink(tmp_path)
    raise
```

Betrifft: `user_profile.py`, `assistant_store.py`, `learning_engine.py` (meta + training_data)

---

## Lern-System — Datenfluss

```
Review-Seite: Nutzer bestätigt/korrigiert Dokument
    ↓
record_classification_feedback()  — user_profile.py
    ↓ keyword_scores[doctype][keyword].hits/decisive/corrections
    ↓
learning_engine.add_example(text, label)
    ↓ training_data.json
    ↓ (nach 10 neuen Beispielen: Auto-Retrain)
    ↓
learning_engine.train()  — Embedding + LogReg
    ↓ model.pkl + meta.json
    ↓
learning_engine.predict(text)  — conf ≥ 0.70 → Ergebnis nutzen
```

---

## API-Key-Muster (system.py)

```python
# Sofort wirksam machen (kein Neustart nötig):
os.environ["OPENAI_API_KEY"] = k

# Masked für Anzeige:
key[:4] + "·" * 6 + key[-4:]  # sk-p·······xxxx

# In config.yaml schreiben:
_save_llm("openai_api_key", k)  # via load_config_raw() + save_config()
```

---

## Aktuelle Skills

| Skill | Befehl | Zweck |
|-------|--------|-------|
| syntax-check | `/syntax-check` | Alle 63 src/**/*.py prüfen |
| system-check | `/system-check` | Vollständige Schwachstellen-Analyse |
| nicegui-review | `/nicegui-review` | NiceGUI Closure- und Muster-Bugs |
| doc-pipeline | `/doc-pipeline` | Klassifikations-Pipeline erklären/debuggen |

---

## Aktive Hooks

| Hook | Trigger | Aktion |
|------|---------|--------|
| PostToolUse | Edit/Write auf `.py` | Sofortiger Syntax-Check der geänderten Datei |
| Stop | Session-Ende | Vollständiger Syntax-Check aller 63 Dateien |

---

## Versionierung

- Version: 0.6.7
- Python: ≥ 3.10
- Letzter System-Check: 2026-04-03 (13 Schwachstellen behoben)
- Letzte große Ergänzungen: Lern-Engine, KI-Anbieter-Kacheln, atomic writes

---

## Was NICHT zu diesem Projekt gehört

- Keine Datenbank (alles JSON-basiert, lokal)
- Kein Docker / keine Container
- Kein React / kein JavaScript-Framework (NiceGUI = Python-Only)
- Keine externe Authentifizierung (lokale Anwendung)
- Kein Build-System (direktes Python)
