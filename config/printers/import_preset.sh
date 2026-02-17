#!/bin/bash
# Helper script to import OrcaSlicer preset

PRESET_FILE="Elegoo Centauri Carbon 0.4 nozzle - JK.orca_printer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRESET_PATH="$SCRIPT_DIR/$PRESET_FILE"

echo "=================================================="
echo "OrcaSlicer Preset Import Helper"
echo "=================================================="
echo ""
echo "This script will help you import the preset:"
echo "  $PRESET_FILE"
echo ""
echo "Steps to import manually:"
echo "  1. Open OrcaSlicer application"
echo "  2. Go to: File → Import → Import Configs..."
echo "  3. Navigate to: $PRESET_PATH"
echo "  4. Click 'Import'"
echo "  5. Select the imported printer in the top-right dropdown"
echo ""
echo "After importing, the preset will be used automatically"
echo "when running the bot's slicer."
echo ""
echo "Would you like to open OrcaSlicer now? (y/n)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    if [ -d "/Applications/OrcaSlicer.app" ]; then
        open -a OrcaSlicer
        echo "✅ OrcaSlicer opened!"
        echo ""
        echo "Now follow the import steps above."
    else
        echo "❌ OrcaSlicer not found in /Applications/"
        echo "Please install it first: brew install --cask orcaslicer"
    fi
else
    echo "Skipped. You can import manually later."
fi

echo ""
echo "Preset location: $PRESET_PATH"
