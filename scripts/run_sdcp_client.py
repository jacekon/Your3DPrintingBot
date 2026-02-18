"""Run the SDCP (ElegooLink) client against PRINTER_IP.

Usage:
    /env/bin/python scripts/run_sdcp_client.py
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.printerConnector.sdcp_client import SdcpClient


def main() -> None:
    config = load_config()
    if not config.printer_ip:
        raise SystemExit("PRINTER_IP not set")

    print("Discovery:", SdcpClient.discover())

    async def run() -> None:
        discovery = SdcpClient.discover()
        device_ip = discovery[0].ip if discovery else config.printer_ip

        client = SdcpClient(device_ip)
        await client.connect(ws_ports=[3031, 3030], paths=["/websocket", "/ws", "/"])
        try:
            attrs = await client.get_device_attributes()
            print("Device attributes:", attrs)
            status = await client.get_status()
            print("Status:", status)
        finally:
            await client.close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
