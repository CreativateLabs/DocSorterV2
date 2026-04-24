# legacy/

Archivierte Dateien aus früheren Projekt-Iterationen — **nicht mehr aktiv**.
Hier landen Scripts/Module/Configs die nicht gelöscht werden sollen (historischer
Kontext, Ideen, Referenz), aber nirgendwo im aktiven Code mehr referenziert werden.

## Enthalten

| Datei | Herkunft | Zweck |
|-------|----------|-------|
| `docsorter_v0_single_user.py` | `~/Documents/DocSorter/docsorter.py` | Allererster MVP: Single-User, simpel, keine Lern-Engine |
| `docsorter_v0_variant.py` | `~/Documents/DocSorter/docsorte1r.py` | Variante davon (Tippo im Namen — wahrscheinlich Backup) |

Beide wurden bis April 2026 im Kunden-Datenordner `~/Documents/DocSorter/`
liegen gelassen. Da der Kunden-Ordner **keine Entwickler-Dateien** enthalten
soll, wurden sie hierher verschoben.

## Regel

Inhalt dieses Ordners wird **nicht** vom aktuellen Code importiert. Wenn du
Ideen daraus übernehmen willst: kopieren, anpassen, in `src/` einchecken.
Direkt importieren würde Verwirrung stiften.
