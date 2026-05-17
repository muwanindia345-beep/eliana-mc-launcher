#!/bin/bash

REPO="muwanindia345-beep/eliana-mc-launcher"
VERSION_FILE="version.json"
CURRENT=$(grep '"version"' $VERSION_FILE | grep -o '[0-9.]*')

echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ElianaMC Release Tool"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"

read -p "New version (current: $CURRENT): " VERSION
VERSION=${VERSION:-$CURRENT}
read -p "Changelog: " CHANGELOG
CHANGELOG=${CHANGELOG:-"Bug fixes and improvements"}

echo ""
echo "📦 Pushing to GitHub..."
git add .
git commit -m "release: v$VERSION — $CHANGELOG"
git push origin main --force
echo "✅ GitHub push done!"

echo ""
echo "🔨 Starting EAS Build..."
npx eas-cli build --platform android --profile preview --no-wait
echo "✅ EAS Build submitted!"

echo ""
echo "📢 Notifying Discord..."
curl -s -X POST \
-H "Authorization: token $GH_TOKEN" \
-H "Accept: application/vnd.github.v3+json" \
https://api.github.com/repos/$REPO/dispatches \
-d "{\"event_type\":\"eas-build-complete\",\"client_payload\":{\"version\":\"$VERSION\",\"apk_url\":\"https://expo.dev\",\"changelog\":\"$CHANGELOG\"}}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Done! v$VERSION"
echo "📢 Discord notified!"
echo "🔨 EAS Build running..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━"
