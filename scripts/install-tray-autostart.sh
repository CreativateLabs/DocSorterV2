#!/usr/bin/env bash
# Doc-Sorter Tray: LaunchAgent einrichten (macOS).
#
# Installiert/aktiviert/deaktiviert den Tray beim Login-Autostart.
#
# Nutzung:
#   bash scripts/install-tray-autostart.sh install      # einrichten + starten
#   bash scripts/install-tray-autostart.sh uninstall    # entfernen

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="$ROOT/scripts/com.docsorter.tray.plist"
TARGET="$HOME/Library/LaunchAgents/com.docsorter.tray.plist"
LABEL="com.docsorter.tray"

cmd="${1:-install}"

case "$cmd" in
    install)
        if [ ! -f "$TEMPLATE" ]; then
            echo "Template nicht gefunden: $TEMPLATE" >&2
            exit 1
        fi
        mkdir -p "$HOME/Library/LaunchAgents"
        sed "s|{{PROJECT_ROOT}}|$ROOT|g" "$TEMPLATE" > "$TARGET"
        chmod 644 "$TARGET"
        chmod +x "$ROOT/scripts/run-tray.sh"

        # Falls bereits geladen: zuerst entladen
        launchctl unload "$TARGET" 2>/dev/null || true
        launchctl load "$TARGET"
        echo "\u2713 Tray-Autostart eingerichtet: $TARGET"
        echo "  Logs: /tmp/docsorter-tray.log + /tmp/docsorter-tray.err"
        ;;
    uninstall)
        if [ -f "$TARGET" ]; then
            launchctl unload "$TARGET" 2>/dev/null || true
            rm -f "$TARGET"
            echo "\u2713 Tray-Autostart entfernt."
        else
            echo "Nichts zu entfernen: $TARGET existiert nicht."
        fi
        ;;
    status)
        if launchctl list | grep -q "$LABEL"; then
            echo "\u2713 Aktiv"
            launchctl list | grep "$LABEL"
        else
            echo "Inaktiv"
        fi
        ;;
    *)
        echo "Nutzung: $0 {install|uninstall|status}" >&2
        exit 1
        ;;
esac
