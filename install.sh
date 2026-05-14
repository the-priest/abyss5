#!/bin/sh
# ABYSS — one-shot installer.
#
# Fresh install (one command):
#     curl -sL https://raw.githubusercontent.com/the-priest/abyss5/main/install.sh | sh
#
# Re-running is safe: clones if missing, otherwise updates.

set -e

REPO_URL="${ABYSS_REPO:-https://github.com/the-priest/abyss5.git}"
INSTALL_DIR="${ABYSS_DIR:-$HOME/abyss5}"

echo "==> ABYSS installer"
echo "    repo: $REPO_URL"
echo "    dir : $INSTALL_DIR"
echo

# 1. clone or pull
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "[1/3] updating existing clone ..."
    cd "$INSTALL_DIR"
    git pull --ff-only
else
    if [ -d "$INSTALL_DIR" ]; then
        echo "    $INSTALL_DIR exists but is not a git repo. aborting."
        exit 1
    fi
    echo "[1/3] cloning ..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 2. dependency: pygame
echo "[2/3] checking pygame ..."
if ! python3 -c "import pygame" >/dev/null 2>&1; then
    pip install --break-system-packages pygame 2>/dev/null \
        || pip install pygame \
        || pip3 install --break-system-packages pygame 2>/dev/null \
        || pip3 install pygame
else
    echo "    pygame already present"
fi

# 3. music
echo "[3/3] fetching public-domain music ..."
python3 fetch_music.py || true

echo
echo "==> done."
echo "    play:  cd $INSTALL_DIR && python3 abyss.py"
