#!/bin/bash
# DanChro English Patch installer (macOS). Put this folder inside the game folder (next to danchro.exe).
cd "$(dirname "$0")"
GAME="$(cd .. && pwd)"
pause() { read -r -p "Press Return to close"; }
[ -f "$GAME/danchro.exe" ] || { echo "Could not find danchro.exe. Put this folder inside the game folder."; pause; exit 1; }
while IFS='|' read -r name rel; do
  [ -f "$GAME/$rel" ] || { echo "This patch is for a different game version: $rel not found."; pause; exit 1; }
done < files-all.txt
echo "Which version do you want?"
echo "  1 = Full patch: English + fairer gacha, more crystals, less grind, smarter auto-battle, higher detail"
echo "  2 = Translation only: English text and tutorial images, gameplay unchanged"
while true; do
  read -r -p "Press 1 or 2, then Return: " pick
  case "$pick" in 1) LIST=files-full.txt; break;; 2) LIST=files-translation.txt; break;; esac
done
if [ ! -d backup ]; then
  mkdir backup
  while IFS='|' read -r name rel; do cp "$GAME/$rel" "backup/$name"; done < files-all.txt
  echo "Backed up original files to $(pwd)/backup"
fi
# start from the originals so switching versions leaves nothing behind
while IFS='|' read -r name rel; do cp "backup/$name" "$GAME/$rel"; done < files-all.txt
while IFS='|' read -r src rel; do cp "$src" "$GAME/$rel"; done < "$LIST"
echo "English patch installed."
pause
