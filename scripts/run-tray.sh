#!/usr/bin/env bash
# Doc-Sorter Tray starten (nur macOS).
#
# Nutzung:
#   bash scripts/run-tray.sh              # Default-Port 1991
#   DOCSORTER_PORT=8080 bash scripts/run-tray.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Venv nutzen, wenn vorhanden
if [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
else
    PY="python3"
fi

exec "$PY" -m src.tray_app "$@"
