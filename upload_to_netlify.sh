#!/usr/bin/env bash
# upload_to_netlify.sh — Neues Release auf Netlify hochladen
#
# Was dieses Script macht:
#   1. Installer-Dateien von GitHub Actions herunterladen
#   2. In landing/downloads/ ablegen
#   3. version.json aktualisieren (Landing Page zeigt automatisch neue Version)
#   4. Netlify neu deployen → alles sofort live
#
# Verwendung:
#   ./upload_to_netlify.sh 0.6.0
#   ./upload_to_netlify.sh 0.7.0

set -euo pipefail

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  # Version aus src/version.py lesen
  VERSION=$(python3 -c "from src.version import __version__; print(__version__)" 2>/dev/null || echo "")
fi
if [ -z "$VERSION" ]; then
  echo "❌ Keine Version angegeben. Verwendung: ./upload_to_netlify.sh 0.6.0"
  exit 1
fi

REPO="ninoborn1-stack/doc-sorter-mvp"
DOWNLOADS="landing/downloads"

echo "════════════════════════════════════════"
echo "📦 Doc-Sorter v${VERSION} → Netlify"
echo "════════════════════════════════════════"
echo ""

# ── 1. Warten bis GitHub Actions fertig ist ──────────────────────────────
echo "⏳ Prüfe ob GitHub Actions Build fertig ist..."
MAX_WAIT=1800  # 30 Minuten
WAITED=0
while true; do
  STATUS=$(gh run list --repo "$REPO" --limit 1 --json status,conclusion \
    2>/dev/null | python3 -c "import sys,json; runs=json.load(sys.stdin); print(runs[0]['status'] if runs else 'unknown')" 2>/dev/null || echo "unknown")

  if [ "$STATUS" = "completed" ]; then
    CONCLUSION=$(gh run list --repo "$REPO" --limit 1 --json conclusion \
      2>/dev/null | python3 -c "import sys,json; runs=json.load(sys.stdin); print(runs[0]['conclusion'] if runs else 'unknown')" 2>/dev/null || echo "unknown")
    if [ "$CONCLUSION" = "success" ]; then
      echo "✓ Build erfolgreich abgeschlossen"
      break
    else
      echo "⚠ Build abgeschlossen mit Status: $CONCLUSION"
      echo "  Trotzdem versuche ich Artifacts herunterzuladen..."
      break
    fi
  elif [ "$STATUS" = "in_progress" ] || [ "$STATUS" = "queued" ]; then
    echo "  ⏳ Build läuft noch... (${WAITED}s gewartet)"
    sleep 30
    WAITED=$((WAITED + 30))
    if [ $WAITED -ge $MAX_WAIT ]; then
      echo "❌ Timeout nach ${MAX_WAIT}s — Build dauert zu lange"
      exit 1
    fi
  else
    echo "  Status: $STATUS — fahre fort"
    break
  fi
done
echo ""

# ── 2. Installer herunterladen ────────────────────────────────────────────
mkdir -p "$DOWNLOADS"

echo "📥 Lade Installer herunter..."
DOWNLOADED=0

# Mac arm64
if gh run download --repo "$REPO" --name "mac-arm64" --dir "$DOWNLOADS" 2>/dev/null; then
  echo "  ✓ Mac Apple Silicon (arm64)"
  DOWNLOADED=$((DOWNLOADED + 1))
else
  echo "  ⚠ Mac arm64 nicht verfügbar"
fi

# Mac x64
if gh run download --repo "$REPO" --name "mac-x64" --dir "$DOWNLOADS" 2>/dev/null; then
  echo "  ✓ Mac Intel (x86_64)"
  DOWNLOADED=$((DOWNLOADED + 1))
else
  echo "  ⚠ Mac x64 nicht verfügbar"
fi

# Windows
if gh run download --repo "$REPO" --name "windows" --dir "$DOWNLOADS" 2>/dev/null; then
  echo "  ✓ Windows Setup"
  DOWNLOADED=$((DOWNLOADED + 1))
else
  echo "  ⚠ Windows nicht verfügbar"
fi

echo ""
if [ $DOWNLOADED -eq 0 ]; then
  echo "❌ Keine Dateien heruntergeladen. Build vielleicht noch nicht fertig?"
  echo "   Nochmal versuchen: ./upload_to_netlify.sh $VERSION"
  exit 1
fi

echo "Dateien in $DOWNLOADS/:"
ls -lh "$DOWNLOADS/"*.dmg "$DOWNLOADS/"*.exe 2>/dev/null | awk '{print "  "$NF, $5}'
echo ""

# ── 3. version.json aktualisieren (mit SHA256-Checksummen) ───────────────
echo "📝 Aktualisiere version.json (inkl. SHA256-Checksummen)..."
NOTES=$(git log -1 --pretty=format:"%s" 2>/dev/null || echo "Doc-Sorter v${VERSION}")
python3 -c "
import json, os, hashlib

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

version = '${VERSION}'
downloads_dir = '${DOWNLOADS}'

files = sorted(os.listdir(downloads_dir)) if os.path.exists(downloads_dir) else []
downloads = {}
checksums = {}

for fname in files:
    path = os.path.join(downloads_dir, fname)
    if not os.path.isfile(path):
        continue
    if fname.endswith('.dmg') and 'arm64' in fname and version in fname:
        downloads['mac-arm64'] = f'/downloads/{fname}'
        checksums['mac-arm64'] = sha256_file(path)
    elif fname.endswith('.dmg') and ('x86_64' in fname or 'intel' in fname.lower()) and version in fname:
        downloads['mac-intel'] = f'/downloads/{fname}'
        checksums['mac-intel'] = sha256_file(path)
    elif fname.endswith('.exe') and version in fname:
        downloads['win'] = f'/downloads/{fname}'
        checksums['win'] = sha256_file(path)

data = {
    'version': version,
    'downloads': downloads,
    'checksums': checksums,
    'release_notes': '${NOTES}'
}
with open('landing/version.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('  ✓ Downloads:', list(downloads.keys()))
print('  ✓ Checksums:', {k: v[:16]+'...' for k, v in checksums.items()})
"

# ── 4. Netlify deployen ───────────────────────────────────────────────────
echo ""
echo "🚀 Deploye auf Netlify..."
npx netlify deploy --dir=landing --prod --message="Release v${VERSION}" 2>&1 | grep -E "✔|Deploy|URL|Error|fail" || true

echo ""
echo "════════════════════════════════════════"
echo "✅ Release v${VERSION} ist live!"
echo ""
echo "   🌍 Landing Page:  https://doc-sorter-app.netlify.app"
echo "   📥 Downloads:     https://doc-sorter-app.netlify.app/downloads/"
echo "   📋 version.json:  https://doc-sorter-app.netlify.app/version.json"
echo "════════════════════════════════════════"
