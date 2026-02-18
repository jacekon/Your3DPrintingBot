"""Run Cassini client to upload and optionally start printing a G-code file."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from src.printerConnector import CassiniClient


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload G-code using CassiniClient")
    parser.add_argument("gcode", help="Path to the G-code file to upload")
    parser.add_argument("--printer-ip", help="Printer IP address (optional if auto-discovery works)")
    parser.add_argument(
        "--start-print",
        action="store_true",
        help="Start printing after upload completes",
    )
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    gcode_path = Path(args.gcode).expanduser().resolve()
    if not gcode_path.exists():
        raise FileNotFoundError(f"G-code not found: {gcode_path}")

    client = CassiniClient(printer_ip=args.printer_ip)
    await client.connect()
    try:
        uploaded_name = await client.upload_gcode(str(gcode_path))
        print(f"Upload complete: {uploaded_name}")
        if args.start_print:
            started = await client.start_print(uploaded_name)
            print(f"Print start result: {started}")
    finally:
        await client.close()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
