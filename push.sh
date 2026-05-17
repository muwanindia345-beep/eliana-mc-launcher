#!/bin/bash

# ElianaMC Smart Auto-Push Script
VERSION_FILE="version.json"
CURRENT=$(grep '"version"' $VERSION_FILE | grep -o '[0-9.]*')

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ElianaMC Auto-Push v$CURRENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Changed files check
CHANGED=$(git status --porcelain | wc -l)
if [ "$CHANGED" -eq 0 ]; then
  echo "✅ Nothing to push — already up to date!"
  exit 0
fi

echo "📝 Changed files:"
git status --short

# Version bump
echo ""
echo "Current version: v$CURRENT"
read -p "New version (Enter = keep $CURRENT): " NEW_VERSION
NEW_VERSION=${NEW_VERSION:-$CURRENT}

# Changelog
read -p "Changelog message: " CHANGELOG
CHANGELOG=${CHANGELOG:-"Minor updates and improvements"}

# Update version.json
DATE=$(date +%Y-%m-%d)
cat > $VERSION_FILE << JSONEOF
{
  "version": "$NEW_VERSION",
  "size_mb": "54.2",
  "changelog": "$CHANGELOG",
  "apk_url": "https://github.com/muwanindia345-beep/eliana-mc-launcher/releases/download/v$NEW_VERSION/eliana.apk",
  "date": "$DATE"
}
JSONEOF

echo ""
echo "🚀 Pushing to GitHub..."
git add .
git commit -m "release: v$NEW_VERSION — $CHANGELOG"
git push origin main

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Pushed! v$NEW_VERSION → GitHub"
echo "🔄 EAS build trigger karo:"
echo "   npx eas-cli build --platform android --profile preview"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
