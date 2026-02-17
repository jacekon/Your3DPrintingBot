# Slicer Setup Guide

## Problem

The OrcaSlicer slicer needs proper printer configuration to work. The error "Relative extruder addressing requires resetting the extruder position..." means the printer profile is missing the `G92 E0` command in the layer change G-code.

## Solution

Import the `.orca_printer` preset file into OrcaSlicer GUI. This is a **one-time setup** that fixes the configuration.

## Quick Setup (5 minutes)

### Step 1: Import the Preset

1. **Open OrcaSlicer** application
   ```bash
   open -a OrcaSlicer
   ```

2. **Import the config bundle:**
   - Go to: **File → Import → Import Configs...**
   - Navigate to: `config/printers/`
   - Select: `Elegoo Centauri Carbon 0.4 nozzle - JK.orca_printer`
   - Click **Import**

3. **Select the printer:**
   - In the top-right dropdown, select: `Elegoo Centauri Carbon 0.4 nozzle - JK`
   - The filament and print settings will be selected automatically

### Step 2: Verify It Works

Run the test:
```bash
source env/bin/activate
python -m tests.test_slicer
```

You should see:
```
✅ Sliced dhtCaseTopSolder.stl -> dhtCaseTopSolder.gcode (XXX KB)
```

## What's in the Preset?

The `.orca_printer` file is a configuration bundle containing:
- **Printer settings**: Elegoo Centauri Carbon specs, bed size, nozzle size
- **Filament settings**: PLA-CF filament profile
- **Process settings**: 0.12mm Fine print profile with proper layer G-code

The critical fix is in the printer's `before_layer_change_gcode`:
```gcode
;BEFORE_LAYER_CHANGE
;[layer_z]
G92 E0
```

This resets the extruder position at each layer to prevent floating-point accuracy loss.

## Alternative: Use .elegoo_printer

If you don't have the `-JK` preset, you can also import:
```
config/printers/Elegoo Centauri Carbon 0.4 nozzle.elegoo_printer
```

This is the older preset that should also work.

## Troubleshooting

### "OrcaSlicer binary not found"
Install OrcaSlicer:
```bash
brew install --cask orcaslicer
```

### "Still getting G92 E0 error after import"
Make sure you:
1. Actually clicked "Import" in the dialog (not just "Open")
2. Selected the imported printer in the top-right dropdown
3. The printer name should show: `Elegoo Centauri Carbon 0.4 nozzle - JK`

### "How do I know if it's imported?"
Check in OrcaSlicer:
- The printer dropdown should list the imported printer name
- You can verify the G-code by going to: Printer Settings → Machine G-code → Before layer change G-code

## Technical Details

### Why can't we load configs via CLI?

OrcaSlicer's `--load-settings` flag only works with properly formatted config files that have a `type` field. The individual JSON files extracted from `.orca_printer` bundles don't have this metadata, so OrcaSlicer rejects them.

The bundle itself is a ZIP archive but OrcaSlicer expects it to be imported through the GUI, not loaded directly via CLI.

### Why not use --no-check?

The `--no-check` flag skips G-code validation AFTER slicing, but the G92 E0 error happens during the config validation phase BEFORE slicing starts. So `--no-check` doesn't help.

## Summary

**TL;DR**: Import the `.orca_printer` file once through OrcaSlicer GUI (File → Import → Import Configs). After that, the CLI will use those settings automatically.
