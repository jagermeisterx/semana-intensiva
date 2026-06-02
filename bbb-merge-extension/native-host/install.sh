#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST_SCRIPT="$SCRIPT_DIR/bbb-merge-host.py"
MANIFEST_TEMPLATE="$SCRIPT_DIR/com.bbb.merge.json"
HOST_NAME="com.bbb.merge"

if ! command -v python3 &>/dev/null; then
  echo "Error: python3 is required but not installed."
  exit 1
fi

# Get extension ID from argument, or prompt user
EXTENSION_ID="${1:-}"
if [ -z "$EXTENSION_ID" ]; then
  echo ""
  echo "=== BBB Merge - Native Host Installation ==="
  echo ""
  echo "To find your Extension ID:"
  echo "  1. Go to chrome://extensions"
  echo "  2. Enable 'Developer mode'"
  echo "  3. Load the 'bbb-merge-extension' folder (unpacked)"
  echo "  4. Copy the ID shown under the extension name"
  echo ""
  read -r -p "Enter Chrome Extension ID: " EXTENSION_ID
  EXTENSION_ID="${EXTENSION_ID:-}"
fi

if [ -z "$EXTENSION_ID" ]; then
  echo "Error: Extension ID is required."
  exit 1
fi

# Determine native messaging hosts directory
case "$(uname -s)" in
  Linux*)
    HOST_DIR="${HOME}/.config/google-chrome/NativeMessagingHosts"
    CHROMIUM_DIR="${HOME}/.config/chromium/NativeMessagingHosts"
    ;;
  Darwin*)
    HOST_DIR="${HOME}/Library/Application Support/Google/Chrome/NativeMessagingHosts"
    CHROMIUM_DIR="${HOME}/Library/Application Support/Chromium/NativeMessagingHosts"
    ;;
  *)
    echo "Unsupported OS: $(uname -s)"
    exit 1
    ;;
esac

# Create manifest with correct paths
MANIFEST=$(cat "$MANIFEST_TEMPLATE" \
  | sed "s|__HOST_PATH__|${HOST_SCRIPT}|g" \
  | sed "s|__EXTENSION_ID__|${EXTENSION_ID}|g")

# Install for Chrome
mkdir -p "$HOST_DIR"
echo "$MANIFEST" > "${HOST_DIR}/${HOST_NAME}.json"
echo "Installed: ${HOST_DIR}/${HOST_NAME}.json"

# Also install for Chromium if directory exists
if [ -d "$CHROMIUM_DIR" ] || [ ! -e "$CHROMIUM_DIR" ]; then
  mkdir -p "$CHROMIUM_DIR"
  echo "$MANIFEST" > "${CHROMIUM_DIR}/${HOST_NAME}.json"
  echo "Installed: ${CHROMIUM_DIR}/${HOST_NAME}.json"
fi

# Make host script executable
chmod +x "$HOST_SCRIPT"

echo ""
echo "=== Installation complete ==="
echo ""
echo "Make sure you have ffmpeg installed:"
echo "  sudo apt install ffmpeg   # Debian/Ubuntu"
echo "  brew install ffmpeg       # macOS"
echo "  winget install ffmpeg     # Windows"
echo ""
echo "Then reload the extension in chrome://extensions"
