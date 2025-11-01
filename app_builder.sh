#!/bin/bash

# ----------------------------
# ✅ Einstellungen
# ----------------------------
APP_NAME="Video Analyse"
SPEC_FILE="build.spec"
DIST_DIR="dist"
BUILD_DIR="build"
DMG_NAME="Video_Analyse.dmg"

# Architektur setzen (x86_64 = Intel, arm64 = M1/M2)
ARCH=${1:-"arm64"}   # Standard: Apple Silicon, per Parameter überschreibbar

echo "🛠 Starte Build für Architektur: $ARCH"

# ----------------------------
# ✅ 1. Python Virtual Env prüfen/erstellen
# ----------------------------
# if [ ! -d "venv" ]; then
#     echo "🐍 Erstelle Python virtual environment..."
#     python3 -m venv venv
# fi

echo "✅ Aktiviere venv..."
# source venv/bin/activate
conda activate Video_Analyse

# ----------------------------
# ✅ 2. Dependencies installieren
# ----------------------------
# echo "📦 Installiere Requirements..."
# pip install --upgrade pip
# pip install -r requirements.txt

# ----------------------------
# ✅ 3. Alte Builds löschen
# ----------------------------
echo "🧹 Lösche alte Build-Dateien..."
rm -rf "$DIST_DIR" "$BUILD_DIR" "$DMG_NAME"

# ----------------------------
# ✅ 4. App mit PyInstaller bauen
# ----------------------------
echo "🏗 Baue App mit PyInstaller..."
arch -$ARCH python3 -m PyInstaller "$SPEC_FILE" --noconfirm

if [ ! -d "$DIST_DIR/$APP_NAME.app" ]; then
    echo "❌ Fehler: App wurde nicht erzeugt."
    exit 1
fi

echo "✅ App erfolgreich gebaut!"

# ----------------------------
# ✅ 5. DMG erstellen
# ----------------------------
echo "📦 Erstelle DMG..."
npx create-dmg "$DIST_DIR/$APP_NAME.app" "$DIST_DIR" --overwrite

# Standard-Dateiname anpassen
if [ -f "$DIST_DIR/$APP_NAME.dmg" ]; then
    mv "$DIST_DIR/$APP_NAME.dmg" "$DMG_NAME"
    echo "✅ DMG erstellt: $DMG_NAME"
else
    echo "❌ Fehler: DMG wurde nicht erzeugt!"
    exit 1
fi

echo "🎉 Build abgeschlossen!"