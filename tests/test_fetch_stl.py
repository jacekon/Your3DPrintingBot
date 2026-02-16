#!/usr/bin/env python3
"""
Test fetching STL files from a Printables model URL.
Run from project root: python tests/test_fetch_stl.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.downloads.fetcher import fetch_model_files

TEST_URL = "https://www.printables.com/model/285921-wifi-climate-sensor-enclosure-for-esp32-or-esp8266"


async def main():
    print(f"Fetching STLs from: {TEST_URL}\n")
    job_id, stl_paths = await fetch_model_files(TEST_URL)
    print(f"Job ID: {job_id}")
    print(f"Saved {len(stl_paths)} STL file(s):")
    for p in stl_paths:
        print(f"  {p} ({p.stat().st_size} bytes)")
    return 0 if stl_paths else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
