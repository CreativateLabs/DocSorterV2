#!/usr/bin/env bash
# build_mac.sh — Doc-Sorter macOS Release Build
# Erstellt: DocSorter.app + DocSorter-{version}-{arch}.dmg
#
# Voraussetzungen:
#   brew install create-dmg
#   pip install pyinstaller nicegui pywebview
#
# Verwendung:
#   chmod +x build_mac.sh
#   ./build_mac.sh                    # Universal (arm64 + x86_64)
#   ./build_mac.sh --arch arm64       # Nur Apple Silicon
#   ./build_mac.sh --arch x86_64      # Nur Intel

set -euo pipefail

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
APP_NAME="DocSorter"
VERSION=$(python3 -c "from src.version import __version__; print(__version__)")
ARCH="${2:-$(uname -m)}"   # arm64 oder x86_64
DIST_DIR="dist/mac"
BUILD_DIR="build/mac"
DMG_NAME="${APP_NAME}-${VERSION}-mac-${ARCH}.dmg"
STAGING_DIR="dist/dmg_staging"

echo "🔨 Doc-Sorter macOS Build"
echo "   Version: ${VERSION}"
echo "   Arch:    ${ARCH}"
echo ""

# ---------------------------------------------------------------------------
# Pre-Build-Check: Sicherstellen dass KEINE Nutzerdaten gebundelt werden
# ---------------------------------------------------------------------------
echo "🔍 Prüfe auf Nutzerdaten …"
python3 pre_build_check.py
echo ""

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
rm -rf "${DIST_DIR}" "${BUILD_DIR}" "${STAGING_DIR}"

# ---------------------------------------------------------------------------
# PyInstaller Build
# ---------------------------------------------------------------------------
echo "📦 Erstelle App-Bundle mit PyInstaller..."
pyinstaller docsorter.spec \
    --distpath "${DIST_DIR}" \
    --workpath "${BUILD_DIR}" \
    --noconfirm \
    --clean \
    --target-arch "${ARCH}"

APP_PATH="${DIST_DIR}/${APP_NAME}.app"
if [ ! -d "${APP_PATH}" ]; then
    echo "❌ ${APP_PATH} nicht gefunden — PyInstaller fehlgeschlagen?"
    exit 1
fi
echo "✓ App-Bundle erstellt: ${APP_PATH}"

# ---------------------------------------------------------------------------
# Code-Signierung (optional — nur wenn APPLE_SIGNING_IDENTITY gesetzt)
# ---------------------------------------------------------------------------
if [ -n "${APPLE_SIGNING_IDENTITY:-}" ]; then
    echo "🔏 Code-Signierung mit: ${APPLE_SIGNING_IDENTITY}"
    codesign \
        --deep \
        --force \
        --verify \
        --verbose \
        --sign "${APPLE_SIGNING_IDENTITY}" \
        --options runtime \
        --entitlements "assets/entitlements.plist" \
        "${APP_PATH}"
    echo "✓ Code-Signierung abgeschlossen"
else
    echo "⚠ APPLE_SIGNING_IDENTITY nicht gesetzt — App nicht signiert (Gatekeeper-Warnung möglich)"
fi

# ---------------------------------------------------------------------------
# DMG erstellen
# ---------------------------------------------------------------------------
echo "💿 Erstelle DMG..."
mkdir -p "${STAGING_DIR}"
cp -R "${APP_PATH}" "${STAGING_DIR}/"

if command -v create-dmg &>/dev/null; then
    create-dmg \
        --volname "${APP_NAME} ${VERSION}" \
        --volicon "assets/icon.icns" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 128 \
        --icon "${APP_NAME}.app" 170 190 \
        --hide-extension "${APP_NAME}.app" \
        --app-drop-link 430 190 \
        --background "assets/dmg_background.png" \
        --no-internet-enable \
        "dist/${DMG_NAME}" \
        "${STAGING_DIR}"
else
    echo "⚠ create-dmg nicht gefunden — einfaches DMG via hdiutil"
    hdiutil create \
        -srcfolder "${STAGING_DIR}" \
        -volname "${APP_NAME} ${VERSION}" \
        -fs HFS+ \
        -fsargs "-c c=64,a=16,b=16" \
        -format UDZO \
        -imagekey zlib-level=6 \
        "dist/${DMG_NAME}"
fi

rm -rf "${STAGING_DIR}"

# ---------------------------------------------------------------------------
# Notarization (optional — nur wenn APPLE_ID und APPLE_TEAM_ID gesetzt)
# ---------------------------------------------------------------------------
if [ -n "${APPLE_ID:-}" ] && [ -n "${APPLE_TEAM_ID:-}" ]; then
    echo "📋 Notarization..."
    xcrun notarytool submit "dist/${DMG_NAME}" \
        --apple-id "${APPLE_ID}" \
        --team-id "${APPLE_TEAM_ID}" \
        --password "${APPLE_APP_PASSWORD}" \
        --wait
    xcrun stapler staple "dist/${DMG_NAME}"
    echo "✓ Notarization abgeschlossen"
fi

# ---------------------------------------------------------------------------
# Ergebnis
# ---------------------------------------------------------------------------
echo ""
echo "✅ Build abgeschlossen!"
echo "   DMG: dist/${DMG_NAME}"
ls -lh "dist/${DMG_NAME}"
