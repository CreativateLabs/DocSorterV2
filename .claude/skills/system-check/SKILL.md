# Skill: system-check

Vollständige Schwachstellenanalyse des gesamten doc-sorter-mvp Codebases.

## Trigger

- Nutzer schreibt `/system-check`
- Nutzer fragt nach "Bugs suchen", "Schwachstellen prüfen", "System analysieren"
- Nach größeren Feature-Implementierungen

## Ablauf

1. **Syntax-Check** aller 63 src/**/*.py Dateien (py_compile)
2. **Import-Check** – relative Imports korrekt? Fehlende Module?
3. **NiceGUI-Muster** – Closure-Bugs in `@ui.refreshable` Funktionen?
4. **Config-Keys** – werden Keys benutzt die in `_DEFAULTS` fehlen?
5. **Race Conditions** – direktes `write_text()` auf JSON-Dateien ohne atomic write?
6. **Fehlende None-Checks** – `float(x.get("key", 0))` wenn key=None möglich?
7. **Fehlende Aufrufe** – Funktionen definiert aber nie aufgerufen?
8. **Exception-Handling** – bare `except: pass` ohne Logging?

## Besondere Prüfpunkte für dieses Projekt

### NiceGUI Closure-Bugs (häufigster Fehler!)
```python
# FALSCH — _func wird erst nach der Schleife aufgelöst:
for item in items:
    ui.button(on_click=lambda: _func(item))  # BUG: immer letzter item

# RICHTIG — Default-Argument captured:
for item in items:
    ui.button(on_click=lambda x=item: _func(x))  # OK

# RICHTIG — Factory-Funktion:
def make_handler(x):
    return lambda: _func(x)
```

### Atomic Write Pattern (Pflicht für alle JSON-Stores)
```python
# FALSCH — kann Datei korrumpieren bei gleichzeitigem Zugriff:
p.write_text(json.dumps(data))

# RICHTIG — temp file + os.replace() ist atomar:
tmp_fd, tmp_path = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
with os.fdopen(tmp_fd, "w") as f:
    f.write(json.dumps(data))
os.replace(tmp_path, p)
```

### Config-Key-Zugriff
```python
# FALSCH — KeyError wenn Sektion fehlt:
cfg["llm"]["openai_api_key"]

# RICHTIG — immer mit .get():
cfg.get("llm", {}).get("openai_api_key", "")
```

## Ausgabe

Strukturierte Liste aller gefundenen Probleme sortiert nach Schwere:
- 🔴 Kritisch (Crash-Risiko)
- 🟡 Mittel (Datenverlust/Fehlfunktion)
- 🟢 Klein (Qualität/Konsistenz)
