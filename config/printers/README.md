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

This will slice using the presets in [config/printers/ElegooCC0.4nozzleJK](config/printers/ElegooCC0.4nozzleJK) and generate CLI-normalized copies at runtime.

## How It Works

The bot's slicer calls OrcaSlicer via CLI with explicit presets built from bundle configs.
It also passes the OrcaSlicer data directory so inherited settings resolve correctly.

Key behavior:
- Extracts the bundle in [config/printers/ElegooCC0.4nozzleJK](config/printers/ElegooCC0.4nozzleJK)
- Writes normalized CLI presets (adds required `type`, compatibility, and `layer_gcode` with `G92 E0`) into config/printers/.orca_cli_cache
- Uses `--load-settings` and `--load-filaments` so the CLI does not depend on GUI defaults

## Files in This Directory

- [config/printers/Elegoo Centauri Carbon 0.4 nozzle.elegoo_printer](config/printers/Elegoo%20Centauri%20Carbon%200.4%20nozzle.elegoo_printer) - Printer bundle for import
- [config/printers/ElegooCC0.4nozzleJK](config/printers/ElegooCC0.4nozzleJK) - Bundle directory used by the CLI wrapper
- [config/printers/Elegoo-Centauri-Carbon-PLA-CF-Fine.3mf](config/printers/Elegoo-Centauri-Carbon-PLA-CF-Fine.3mf) - Original 3MF project file (reference)
- config/printers/.orca_cli_cache (generated at runtime; safe to delete)

## Troubleshooting

**Error: "unknown config type"**
- The CLI expects `type` fields. The wrapper generates normalized presets in config/printers/.orca_cli_cache.

**Error: "Relative extruder addressing..."**
- The wrapper injects `G92 E0` into `layer_gcode` at runtime. If you bypass the wrapper, include the same `--load-settings` args.

**Slicing works but wrong settings**
- Ensure the bundle in [config/printers/ElegooCC0.4nozzleJK](config/printers/ElegooCC0.4nozzleJK) matches your printer and filament
- The wrapper does not rely on GUI defaults
