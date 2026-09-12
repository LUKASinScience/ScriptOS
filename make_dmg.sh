#!/bin/bash
# Packages dist/ScriptOS.app into a drag-to-Applications ScriptOS.dmg.
# Uses hdiutil (built into macOS) — no extra tooling needed.
set -e
cd "$(dirname "$0")"

APP="dist/ScriptOS.app"
DMG="ScriptOS.dmg"
STAGING="$(mktemp -d)"

if [ ! -d "$APP" ]; then
  echo "Build the app first: ./build.sh"
  exit 1
fi

cp -R "$APP" "$STAGING/ScriptOS.app"
ln -s /Applications "$STAGING/Applications"

rm -f "$DMG"
hdiutil create -volname "ScriptOS" -srcfolder "$STAGING" -ov -format UDZO "$DMG"
rm -rf "$STAGING"

echo "Built: $DMG"
