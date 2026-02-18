"""SDCP client using sdcp-printer-api (SDCP V3)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

SDCP_API_PATH = Path(__file__).resolve().parent / "sdcp-printer-api" / "src"
if str(SDCP_API_PATH) not in sys.path:
    sys.path.append(str(SDCP_API_PATH))

from sdcp_printer import SDCPPrinter  # noqa: E402
from sdcp_printer.enum import SDCPFrom  # noqa: E402
from sdcp_printer.scanner import discover_devices  # noqa: E402


class SdcpClient:
    """Thin wrapper around sdcp-printer-api."""

    def __init__(self, printer_ip: Optional[str] = None, timeout: float = 5) -> None:
        self.printer_ip = printer_ip
        self.timeout = timeout
        self.printer: Optional[SDCPPrinter] = None
        self._listen_task: Optional[asyncio.Task] = None

    @staticmethod
    def discover(timeout: int = 1):
        """Discover printers via SDCP broadcast."""
        return discover_devices(timeout=timeout)

    async def connect(self) -> SDCPPrinter:
        """Connect to a printer and start listening for status messages."""
        if self.printer_ip:
            printer = await SDCPPrinter.get_printer_async(self.printer_ip, self.timeout)
        else:
            printers = discover_devices(timeout=int(self.timeout))
            if not printers:
                raise RuntimeError("No printers found on network")
            printer = printers[0]

        self.printer = printer
        self._listen_task = asyncio.create_task(printer.start_listening_async())
        await printer.wait_for_connection_async(timeout=self.timeout)
        return printer

    async def refresh_status(self) -> None:
        """Request a status update from the printer."""
        if not self.printer:
            raise RuntimeError("Printer is not connected")
        await self.printer.refresh_status_async(timeout=self.timeout, sdcp_from=SDCPFrom.PC)

    def status_snapshot(self) -> dict[str, object]:
        """Return a simple snapshot of the current status."""
        if not self.printer:
            raise RuntimeError("Printer is not connected")
        return {
            "name": self.printer.name,
            "manufacturer": self.printer.manufacturer,
            "model": self.printer.model,
            "firmware_version": self.printer.firmware_version,
            "current_status": self.printer.current_status,
            "print_status": self.printer.print_status,
            "print_error": self.printer.print_error,
            "file_name": self.printer.file_name,
            "current_layer": self.printer.current_layer,
            "total_layers": self.printer.total_layers,
        }

    async def close(self) -> None:
        """Stop listening and close the connection."""
        if self.printer:
            await self.printer.stop_listening_async()

        if self._listen_task:
            self._listen_task.cancel()
            self._listen_task = None

        self.printer = None
