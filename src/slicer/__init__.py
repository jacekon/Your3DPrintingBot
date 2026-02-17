"""
Slicer module for converting STL files to G-code.

Use OrcaSlicer - it's stable and works with .elegoo_printer configs.
ElegooSlicer CLI is broken (segfaults).
"""
from src.slicer.orca_slicer import OrcaSlicer

# Note: ElegooSlicer exists but crashes (segfault) - do not use
# from src.slicer.elegoo_slicer import ElegooSlicer

__all__ = ["OrcaSlicer"]
