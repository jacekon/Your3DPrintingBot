"""Tests for the SDCP V3 client wrapper."""
import asyncio
import importlib.util
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _load_sdcp_client_module():
    module_path = Path(__file__).resolve().parents[1] / "src" / "printerConnector" / "sdcp_client.py"
    spec = importlib.util.spec_from_file_location("sdcp_client", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("Failed to load sdcp_client module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sdcp_client_module = _load_sdcp_client_module()
SdcpClient = sdcp_client_module.SdcpClient


class _FakePrinter:
    def __init__(self):
        self.started = False
        self.waited = False
        self.refreshed = False
        self.name = "TestPrinter"
        self.manufacturer = "TestCo"
        self.model = "ModelX"
        self.firmware_version = "1.0"
        self.current_status = ["IDLE"]
        self.print_status = "IDLE"
        self.print_error = None
        self.file_name = None
        self.current_layer = 0
        self.total_layers = 0

    async def start_listening_async(self):
        await asyncio.sleep(0)
        self.started = True

    async def wait_for_connection_async(self, *args, **kwargs):
        await asyncio.sleep(0)
        self.waited = True

    async def refresh_status_async(self, *args, **kwargs):
        await asyncio.sleep(0)
        self.refreshed = True

    async def stop_listening_async(self):
        await asyncio.sleep(0)
        return None


def test_discover_uses_scanner(monkeypatch):
    fake_printers = [object(), object()]

    def _fake_discover(timeout=1):
        return fake_printers

    monkeypatch.setattr(sdcp_client_module, "discover_devices", _fake_discover)
    result = SdcpClient.discover(timeout=1)
    assert result == fake_printers


def test_connect_and_refresh(monkeypatch):
    fake_printer = _FakePrinter()

    async def _fake_get_printer_async(ip_address, *args, **kwargs):
        await asyncio.sleep(0)
        return fake_printer

    monkeypatch.setattr(
        sdcp_client_module.SDCPPrinter,
        "get_printer_async",
        staticmethod(_fake_get_printer_async),
    )

    async def _run():
        client = SdcpClient(printer_ip="192.168.1.2", timeout=1)
        await client.connect()
        await client.refresh_status()
        snapshot = client.status_snapshot()
        await client.close()
        return snapshot

    snapshot = asyncio.run(_run())
    assert fake_printer.started is True
    assert fake_printer.waited is True
    assert fake_printer.refreshed is True
    assert snapshot["name"] == "TestPrinter"


def test_connects_to_real_printer():
    """Integration test that connects to the configured printer IP in .env."""
    load_dotenv()
    printer_ip = os.getenv("PRINTER_IP")
    assert printer_ip, "PRINTER_IP must be set in .env to run this test"

    print(f"Using PRINTER_IP={printer_ip}")

    async def _run():
        client = SdcpClient(printer_ip=printer_ip, timeout=5)
        print("Connecting...")
        await client.connect()
        print("Connected, requesting status...")
        await client.refresh_status()
        snapshot = client.status_snapshot()
        print(f"Status snapshot: {snapshot}")
        await client.close()
        print("Connection closed")
        return snapshot

    snapshot = asyncio.run(_run())
    assert snapshot["name"] is not None


if __name__ == "__main__":
    test_connects_to_real_printer()
