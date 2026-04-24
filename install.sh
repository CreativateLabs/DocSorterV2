#!/usr/bin/env bash
# Doc-Sorter Installations-Script
# Erstellt venv, installiert Dependencies, prueft Voraussetzungen
#
# Nutzung: bash install.sh
#          bash install.sh --with-llm   (mit LLM-Unterstuetzung)

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Doc-Sorter Installation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Projekt-Verzeichnis bestimmen
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
echo -e "${GREEN}Projekt-Verzeichnis:${NC} $SCRIPT_DIR"

# Python pruefen
PYTHON=""
for cmd in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | awk '{print $2}')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$cmd"
            echo -e "${GREEN}Python gefunden:${NC} $cmd ($version)"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}FEHLER: Python 3.10+ nicht gefunden!${NC}"
    echo "Bitte installieren: https://python.org/downloads/"
    exit 1
fi

# Virtual Environment erstellen
echo ""
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Erstelle Virtual Environment...${NC}"
    "$PYTHON" -m venv .venv
    echo -e "${GREEN}Virtual Environment erstellt.${NC}"
else
    echo -e "${GREEN}Virtual Environment existiert bereits.${NC}"
fi

# Aktivieren
source .venv/bin/activate
echo -e "${GREEN}Virtual Environment aktiviert.${NC}"

# Pip aktualisieren
echo ""
echo -e "${YELLOW}Aktualisiere pip...${NC}"
pip install --upgrade pip -q

# Dependencies installieren
echo ""
echo -e "${YELLOW}Installiere Dependencies...${NC}"
pip install -r requirements.txt -q

# Optional: LLM-Unterstuetzung
if [[ "$1" == "--with-llm" ]]; then
    echo ""
    echo -e "${YELLOW}Installiere LLM-Dependencies...${NC}"
    pip install openai anthropic -q
    echo -e "${GREEN}LLM-Unterstuetzung installiert.${NC}"
fi

# System-Checks
echo ""
echo -e "${BLUE}System-Check:${NC}"

# Tesseract
if command -v tesseract &>/dev/null; then
    tess_version=$(tesseract --version 2>&1 | head -1)
    echo -e "  ${GREEN}[+]${NC} Tesseract: $tess_version"
else
    echo -e "  ${RED}[!]${NC} Tesseract: Nicht installiert"
    echo -e "      ${YELLOW}Installation:${NC}"
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "        brew install tesseract tesseract-lang"
    elif [[ -f /etc/debian_version ]]; then
        echo "        sudo apt install tesseract-ocr tesseract-ocr-deu tesseract-ocr-sqi"
    else
        echo "        Siehe: https://github.com/tesseract-ocr/tesseract"
    fi
fi

# Poppler
if command -v pdftoppm &>/dev/null; then
    echo -e "  ${GREEN}[+]${NC} Poppler: OK"
else
    echo -e "  ${RED}[!]${NC} Poppler: Nicht installiert"
    echo -e "      ${YELLOW}Installation:${NC}"
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "        brew install poppler"
    elif [[ -f /etc/debian_version ]]; then
        echo "        sudo apt install poppler-utils"
    else
        echo "        Siehe: https://poppler.freedesktop.org"
    fi
fi

# Ordner erstellen
echo ""
echo -e "${YELLOW}Erstelle Standard-Ordner...${NC}"
mkdir -p ~/Documents/DocSorter/input
mkdir -p ~/Documents/DocSorter/output
mkdir -p ~/Documents/DocSorter/logs
echo -e "${GREEN}Ordner erstellt:${NC}"
echo "  ~/Documents/DocSorter/input   (Inbox)"
echo "  ~/Documents/DocSorter/output  (Archiv)"
echo "  ~/Documents/DocSorter/logs    (Logs)"

# Abschluss
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  Installation abgeschlossen!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Starten mit:"
echo -e "  ${BLUE}Dashboard:${NC}    .venv/bin/python dashboard.py"
echo -e "  ${BLUE}CLI Dry Run:${NC}  .venv/bin/python main.py --dry-run"
echo -e "  ${BLUE}CLI Live:${NC}     .venv/bin/python main.py --live"
echo -e "  ${BLUE}System Check:${NC} .venv/bin/python main.py --check"
echo ""
echo "Dashboard oeffnet sich unter: http://localhost:8080"
echo ""
