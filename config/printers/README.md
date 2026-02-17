# Printer Configuration for OrcaSlicer

## ⚠️ Important: Use OrcaSlicer, NOT ElegooSlicer

**ElegooSlicer's CLI is broken** - it crashes with segmentation fault when slicing.
Use **OrcaSlicer** instead - it's stable and can import your `.elegoo_printer` files!

## Quick Setup (Recommended)

Run the setup helper:
```bash
./config/printers/setup_orcaslicer.sh
```

Or follow these manual steps:

### 1. Import Your Printer into OrcaSlicer

1. **Open OrcaSlicer** application
2. **Import the printer config**:
   - Go to: `File → Import → Import Configs...`
   - Select: `config/printers/Elegoo Centauri Carbon 0.4 nozzle.elegoo_printer`
   - Click "Import"

3. **Select the printer**:
   - Top-right dropdown: Choose `Elegoo Centauri Carbon 0.4 nozzle`

4. **Configure filament** (if not already set):
   - Create or select a PLA filament profile
   - Set as default for this printer

5. **Configure print settings**:
   - Select or create `0.20mm Standard` print profile
   - Adjust layer height, infill, supports as needed

6. **Save** - OrcaSlicer remembers these as defaults

### 2. Test the Slicer

```bash
python -m tests.test_slicer
```

This will use whatever printer/filament/print settings are currently selected in your OrcaSlicer installation.

## How It Works

The bot's slicer calls OrcaSlicer via CLI:
```bash
orcaslicer --slice 0 --outputdir ./output model.stl
```

OrcaSlicer uses the **last selected settings** from the GUI as defaults for CLI slicing.

## Files in This Directory

- **`Elegoo Centauri Carbon 0.4 nozzle.json`** - Printer-only config (not sufficient alone)
- **`Elegoo Centauri Carbon 0.4 nozzle.elegoo_printer`** - Printer bundle for import
- **`Elegoo-Centauri-Carbon-PLA-CF-Fine.3mf`** - Original 3MF project file (reference)

## Troubleshooting

**Error: "unknown config type"**
- The JSON file is printer-only. Import the `.elegoo_printer` file instead.

**Error: "Relative extruder addressing..."**
- Import the `.elegoo_printer` file - it has the correct G-code settings.

**Slicing works but wrong settings**
- Open OrcaSlicer GUI and verify the selected printer/filament/print profile
- These selections become the CLI defaults
