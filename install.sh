#!/bin/bash
# Abyss installer — places binary, icon, and .desktop entry.

set -e

BIN_DIR="${HOME}/.local/bin"
DATA_DIR="${HOME}/.local/share/abyss"
APP_DIR="${HOME}/.local/share/applications"

mkdir -p "$BIN_DIR" "$DATA_DIR" "$APP_DIR"

# Install game
install -m 755 abyss.py "${BIN_DIR}/abyss"

# Install icon (prefer 256, fall back to 512)
if [ -f icon-256.png ]; then
    install -m 644 icon-256.png "${DATA_DIR}/icon.png"
elif [ -f icon.png ]; then
    install -m 644 icon.png "${DATA_DIR}/icon.png"
fi

# Install .desktop with absolute paths substituted
sed "s|@HOME@|${HOME}|g" abyss.desktop > "${APP_DIR}/abyss.desktop"
chmod 644 "${APP_DIR}/abyss.desktop"

# Update desktop database if available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APP_DIR}" 2>/dev/null || true
fi

echo "Installed:"
echo "  binary:   ${BIN_DIR}/abyss"
echo "  icon:     ${DATA_DIR}/icon.png"
echo "  launcher: ${APP_DIR}/abyss.desktop"
echo
echo "If ${BIN_DIR} isn't on your PATH, add this to ~/.bashrc:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo
echo "Run with: abyss"
echo "Reset save: rm -f ${DATA_DIR}/save.json"
