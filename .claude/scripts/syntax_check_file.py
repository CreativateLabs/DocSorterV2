#!/usr/bin/env python3
"""PostToolUse-Hook: Syntax-Check einer einzelnen Python-Datei nach Edit/Write."""
import json
import py_compile
import sys

data = json.load(sys.stdin)
file_path = data.get("tool_input", {}).get("file_path", "")

if not file_path.endswith(".py"):
    sys.exit(0)

try:
    py_compile.compile(file_path, doraise=True)
    # Kurze Bestätigung ins Modell-Kontext injizieren
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"✓ Syntax OK: {file_path.split('/')[-1]}",
        }
    }
    print(json.dumps(out))
    sys.exit(0)
except py_compile.PyCompileError as e:
    # Fehler als blockierender Context zurück
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"❌ SYNTAXFEHLER — bitte sofort beheben:\n{e}",
        }
    }
    print(json.dumps(out))
    sys.exit(0)  # Nicht blockieren, aber Modell informieren
except FileNotFoundError:
    sys.exit(0)
