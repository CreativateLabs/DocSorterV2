# Skill: syntax-check

Führe einen vollständigen Python-Syntax-Check aller Dateien in `src/` durch.

## Trigger

Wird automatisch ausgelöst wenn:
- Du Änderungen an mehreren `.py`-Dateien gemacht hast
- Der Nutzer `/syntax-check` eingibt
- Nach einer größeren Refactoring-Session

## Verhalten

Führe aus:
```bash
python3 -c "
import py_compile, pathlib, sys
errors = []
for p in pathlib.Path('src').rglob('*.py'):
    try:
        py_compile.compile(str(p), doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(str(e))
if errors:
    print('FEHLER:')
    for e in errors: print(e)
    sys.exit(1)
else:
    count = sum(1 for _ in pathlib.Path('src').rglob('*.py'))
    print(f'✓ Alle {count} Dateien OK')
"
```

## Ausgabe

- Bei Erfolg: `✓ Alle N Dateien OK`
- Bei Fehler: Zeige Dateiname + Zeilennummer + Fehlermeldung, dann sofort beheben
