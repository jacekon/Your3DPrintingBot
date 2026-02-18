"""Integration test for the SDCP V3 client wrapper (real printer only)."""
import asyncio
import importlib.util
import os
import socket
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


def _load_http_server_module():
    module_path = Path(__file__).resolve().parents[1] / "src" / "printerConnector" / "http_server.py"
    spec = importlib.util.spec_from_file_location("http_server", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("Failed to load http_server module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


http_server_module = _load_http_server_module()
HttpFileServer = http_server_module.HttpFileServer


def _local_ip_for(printer_ip: str) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((printer_ip, 1))
        return sock.getsockname()[0]
    finally:
        sock.close()


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


def test_request_attributes_real_printer():
    """Integration test that requests attributes from the configured printer IP in .env."""
    load_dotenv()
    printer_ip = os.getenv("PRINTER_IP")
    assert printer_ip, "PRINTER_IP must be set in .env to run this test"

    print(f"Using PRINTER_IP={printer_ip} (attributes)")

    async def _run():
        client = SdcpClient(printer_ip=printer_ip, timeout=5)
        print("Connecting...")
        await client.connect()
        print("Connected, requesting attributes...")
        response = await client.request_attributes()
        print(f"Attributes response: {response}")
        await client.close()
        print("Connection closed")

    asyncio.run(_run())


def test_upload_gcode_real_printer():
    """Integration test that serves a G-code file and sends Cmd 256."""
    load_dotenv()
    printer_ip = os.getenv("PRINTER_IP")
    assert printer_ip, "PRINTER_IP must be set in .env to run this test"

    gcode_dir = Path(__file__).resolve().parents[1] / "data" / "test_gcode"
    gcode_path = gcode_dir / "plate_1.gcode"
    assert gcode_path.exists(), f"Missing G-code file: {gcode_path}"

    server = HttpFileServer(gcode_dir)
    server.start()
    server_host = _local_ip_for(printer_ip)
    file_url = f"http://${{ipaddr}}:{server.port}/{gcode_path.name}"

    print(f"Serving {gcode_path.name} at {server.base_url(server_host)}/{gcode_path.name}")
    print(f"Upload URL sent to printer: {file_url}")

    async def _run():
        client = SdcpClient(printer_ip=printer_ip, timeout=10)
        print("Connecting...")
        await client.connect()
        print("Connected, sending upload request...")
        try:
            response = await client.upload_gcode(str(gcode_path), file_url)
            print(f"Upload request sent: {response}")
            await client.request_status()
            print(f"Status snapshot: {client.status_snapshot()}")
        finally:
            await client.close()
            print("Connection closed")

    try:
        asyncio.run(_run())
    finally:
        server.stop()


def test_set_light_status_real_printer():
    """Integration test that toggles light status via SDCP Cmd 403."""
    load_dotenv()
    printer_ip = os.getenv("PRINTER_IP")
    assert printer_ip, "PRINTER_IP must be set in .env to run this test"

    print(f"Using PRINTER_IP={printer_ip} (light status)")

    async def _run():
        client = SdcpClient(printer_ip=printer_ip, timeout=5)
        print("Connecting...")
        await client.connect()
        print("Connected, setting light status ON...")
        on_response = await client.set_light_status(True)
        print(f"Light status ON response: {on_response}")
        await asyncio.sleep(3)
        print("Setting light status OFF...")
        off_response = await client.set_light_status(False)
        print(f"Light status OFF response: {off_response}")
        await client.close()
        print("Connection closed")
        return on_response, off_response

    on_response, off_response = asyncio.run(_run())
    assert "Data" in on_response
    assert "Data" in off_response


if __name__ == "__main__":
    test_connects_to_real_printer()
    test_request_attributes_real_printer()
    test_set_light_status_real_printer()
    test_upload_gcode_real_printer()
