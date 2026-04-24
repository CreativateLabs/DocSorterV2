#!/usr/bin/env python3
"""Stop-Hook: Vollständiger Syntax-Check aller src/**/*.py vor Session-Ende."""
import json
import pathlib
import py_compile
import sys

project_dir = pathlib.Path(__file__).resolve().parent.parent.parent
src_dir = project_dir / "src"

if not src_dir.exists():
    sys.exit(0)

errors = []
checked = 0
for p in sorted(src_dir.rglob("*.py")):
    checked += 1
    try:
        py_compile.compile(str(p), doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(str(e))

if errors:
    msg = f"⚠️  {len(errors)} SYNTAXFEHLER in {checked} Dateien:\n" + "\n".join(errors)
    print(json.dumps({"systemMessage": msg}))
    sys.exit(0)
else:
    print(json.dumps({"systemMessage": f"✓ Alle {checked} Python-Dateien fehlerfrei"}))
    sys.exit(0)
