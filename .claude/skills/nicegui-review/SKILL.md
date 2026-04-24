# Skill: nicegui-review

Überprüft NiceGUI-Code auf typische Muster-Fehler in diesem Projekt.

## Trigger

- Nutzer schreibt `/nicegui-review`
- Nach Änderungen in `src/dashboard/pages/*.py` oder `src/dashboard/layout.py`
- Bei Berichten über "Button funktioniert nicht" oder "falscher Wert beim Klick"

## Die 5 häufigsten NiceGUI-Fehler in diesem Projekt

### 1. Lambda in Schleife ohne Default-Capture
```python
# BUG: alle Buttons rufen denselben letzten `item` auf
for item in items:
    ui.button(on_click=lambda: do_something(item))

# FIX: Default-Argument erzwingt sofortiges Binden
for item in items:
    ui.button(on_click=lambda x=item: do_something(x))
```

### 2. Innere Funktion vor Lambda-Referenz definieren
```python
# BUG: _remove ist noch nicht definiert wenn lambda erzeugt wird
@ui.refreshable
def render():
    for i, item in enumerate(items):
        ui.button(on_click=lambda idx=i: _remove(idx))  # NameError!

    def _remove(idx):  # zu spät!
        ...

# FIX: innere Hilfsfunktion IMMER zuerst definieren
@ui.refreshable
def render():
    def _remove(idx):  # ← ERSTE Zeile der Funktion
        items.pop(idx)
        render.refresh()

    for i, item in enumerate(items):
        ui.button(on_click=lambda idx=i: _remove(idx))  # OK
```

### 3. `_le_card.refresh()` in innerer Funktion
```python
# Innere Funktionen können auf äußere @ui.refreshable zugreifen:
@ui.refreshable
def _le_card():
    def _toggle(v):  # innere Funktion
        set_enabled(v)
        _le_card.refresh()  # OK — Closure auf äußere Funktion
```

### 4. `ui.input` Wert in async Handler
```python
# Das input-Element muss als Default-Arg gebunden werden:
inp = ui.input()
async def _save(inp_ref=inp):  # ← Default-Bind
    value = inp_ref.value  # sicher
```

### 5. Refreshable-Funktion nie aufgerufen
```python
@ui.refreshable
def render_section():
    ...

render_section()  # ← MUSS aufgerufen werden!
```

## Prüfmethode

Durchsuche alle Dashboard-Dateien nach:
- `lambda:` ohne Default-Argument in Schleifen
- Funktionsdefinitionen die nach Lambda-Referenzen stehen
- `@ui.refreshable` Funktionen die nie aufgerufen werden
- Fehlende `.refresh()` Aufrufe nach State-Änderungen
