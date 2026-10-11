#!/bin/bash
# Restores the original game files saved by install-mac.command.
cd "$(dirname "$0")"
GAME="$(cd .. && pwd)"
[ -d backup ] || { echo "No backup found - nothing to restore."; read -r -p "Press Return"; exit 1; }
while IFS='|' read -r name rel; do
  [ -f "backup/$name" ] && cp "backup/$name" "$GAME/$rel"
done < files-all.txt
echo "Original files restored."
read -r -p "Press Return to close"
