#!/bin/sh
# Update ABYSS to the latest commit + grab any newly-added music tracks.
# Run from inside your clone:  ./update.sh
set -e
cd "$(dirname "$0")"
echo "[1/2] git pull ..."
git pull --ff-only
echo "[2/2] fetch music (skips already-downloaded) ..."
python3 fetch_music.py || true
echo
echo "done. play with:  python3 abyss.py"
