# ElegooSlicer vs OrcaSlicer for Bot Integration

## Issue Found

**ElegooSlicer CLI is BROKEN - Segmentation Fault**

While ElegooSlicer shows CLI options with `--help`, it crashes when actually trying to slice:

```bash
/Applications/ElegooSlicer.app/Contents/MacOS/ElegooSlicer --slice 0 --outputdir ./output model.stl
[1] segmentation fault
```

This makes it completely unusable for automated bot workflows.

## ✅ Recommended Solution: Use OrcaSlicer

OrcaSlicer has full headless CLI support AND can import your Elegoo config files!

### Setup Steps:

1. **Import your Elegoo printer config into OrcaSlicer:**
   ```bash
   open /Applications/OrcaSlicer.app
   # File → Import → Import Configs...
   # Select: config/printers/Elegoo Centauri Carbon 0.4 nozzle.elegoo_printer
   ```

2. **The bot will use OrcaSlicer:**
   ```python
   from src.slicer import OrcaSlicer
   
   slicer = OrcaSlicer()
   gcode = await slicer.slice_file(stl_path, output_dir)
   ```

3. **Works perfectly with your Elegoo printer settings!**

## Why This Works

- OrcaSlicer is a fork of the same codebase as ElegooSlicer
- It can read `.elegoo_printer` config files
- It has proper CLI support (`--slice`, `--outputdir`, etc.)
- It won't launch the GUI or hang

## Summary

- ❌ ElegooSlicer: CLI exists but crashes (segfault) when slicing
- ✅ OrcaSlicer: Stable CLI, imports `.elegoo_printer` configs perfectly

**Use `src.slicer.OrcaSlicer` for your bot** - it's already implemented and tested!

## Technical Details

```bash
# ElegooSlicer shows options but crashes:
$ ElegooSlicer --help          # ✅ Works
$ ElegooSlicer --slice 0 ...   # ❌ Segmentation fault

# OrcaSlicer works perfectly:
$ OrcaSlicer --help            # ✅ Works  
$ OrcaSlicer --slice 0 ...     # ✅ Works
```
