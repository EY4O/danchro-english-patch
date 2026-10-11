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
echo "  2 = Translation only: English text and images, gameplay unchanged"
while true; do
  read -r -p "Press 1 or 2, then Return: " pick
  case "$pick" in 1) LIST=files-full.txt; break;; 2) LIST=files-translation.txt; break;; esac
done
# back up any original not yet in backup/ (an older patch's backup may hold fewer files)
mkdir -p backup
new=0
while IFS='|' read -r name rel; do
  [ -f "backup/$name" ] && continue
  want=$(awk -F'|' -v n="$name" '$1==n {print $2}' original-sizes.txt)
  if [ -n "$want" ] && [ "$(stat -f%z "$GAME/$rel")" != "$want" ]; then
    echo "$rel is not the original game file - an earlier version of the patch seems to be installed."
    echo "Run that version's uninstaller first, or unzip this patch over the old DanChro-English-Patch folder"
    echo "so its backup folder is kept. Nothing was changed."
    pause; exit 1
  fi
done < files-all.txt
while IFS='|' read -r name rel; do
  [ -f "backup/$name" ] || { cp "$GAME/$rel" "backup/$name"; new=$((new+1)); }
done < files-all.txt
[ "$new" -gt 0 ] && echo "Backed up $new original files to $(pwd)/backup"
# start from the originals so switching versions leaves nothing behind
while IFS='|' read -r name rel; do cp "backup/$name" "$GAME/$rel"; done < files-all.txt
while IFS='|' read -r src rel; do cp "$src" "$GAME/$rel"; done < "$LIST"
echo "English patch installed."
pause
