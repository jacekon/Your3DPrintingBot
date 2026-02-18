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
from sdcp_printer.enum import SDCPFrom, SDCPCommand  # noqa: E402
from sdcp_printer.scanner import discover_devices  # noqa: E402
from sdcp_printer.request import SDCPRequest  # noqa: E402

_PRINTER_NOT_CONNECTED = "Printer is not connected"


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
            raise RuntimeError(_PRINTER_NOT_CONNECTED)
        await self.printer.refresh_status_async(timeout=self.timeout, sdcp_from=SDCPFrom.PC)

    async def request_status(self) -> None:
        """Cmd 0: Request status refresh."""
        await self.refresh_status()

    async def request_attributes(self) -> dict[str, object]:
        """Cmd 1: Request attributes refresh."""
        if not self.printer:
            raise RuntimeError(_PRINTER_NOT_CONNECTED)
        payload = SDCPRequest.build(self.printer, SDCPCommand.REQUEST_ATTRIBUTES, {}, SDCPFrom.PC)
        response = await self.printer.send_request_async(payload, timeout=self.timeout)
        if hasattr(response, "_message_json"):
            return response._message_json
        return {"response": response}

    async def start_print(self, filename: str) -> None:
        """Cmd 128: Start printing (stub)."""
        raise NotImplementedError("start_print is not implemented yet")

    async def pause_print(self) -> None:
        """Cmd 129: Pause printing (stub)."""
        raise NotImplementedError("pause_print is not implemented yet")

    async def stop_print(self) -> None:
        """Cmd 130: Stop printing (stub)."""
        raise NotImplementedError("stop_print is not implemented yet")

    async def continue_print(self) -> None:
        """Cmd 131: Continue/resume printing (stub)."""
        raise NotImplementedError("continue_print is not implemented yet")

    async def stop_feeding_material(self) -> None:
        """Cmd 132: Stop feeding material (stub)."""
        raise NotImplementedError("stop_feeding_material is not implemented yet")

    async def skip_preheating(self) -> None:
        """Cmd 133: Skip preheating (stub)."""
        raise NotImplementedError("skip_preheating is not implemented yet")

    async def change_printer_name(self, name: str) -> None:
        """Cmd 192: Change printer name (stub)."""
        raise NotImplementedError("change_printer_name is not implemented yet")

    async def retrieve_file_list(self, directory: str = "/local") -> None:
        """Cmd 258: Retrieve file list (stub)."""
        raise NotImplementedError("retrieve_file_list is not implemented yet")

    async def batch_delete_files(self, paths: list[str]) -> None:
        """Cmd 259: Batch delete files (stub)."""
        raise NotImplementedError("batch_delete_files is not implemented yet")

    async def retrieve_file_details(self, path: str) -> None:
        """Cmd 260: Retrieve file details (stub)."""
        raise NotImplementedError("retrieve_file_details is not implemented yet")

    async def retrieve_tasks(self) -> None:
        """Cmd 320: Retrieve tasks (stub)."""
        raise NotImplementedError("retrieve_tasks is not implemented yet")

    async def retrieve_task_details(self, task_id: str) -> None:
        """Cmd 321: Retrieve task details (stub)."""
        raise NotImplementedError("retrieve_task_details is not implemented yet")

    async def enable_video_stream(self, enabled: bool) -> None:
        """Cmd 386: Enable video stream (stub)."""
        raise NotImplementedError("enable_video_stream is not implemented yet")

    async def enable_timelapse(self, enabled: bool) -> None:
        """Cmd 387: Enable timelapse (stub)."""
        raise NotImplementedError("enable_timelapse is not implemented yet")

    async def set_light_status(self, enabled: bool) -> dict[str, object]:
        """Cmd 403: Set light status (Centauri Carbon, unverified payload)."""
        if not self.printer:
            raise RuntimeError(_PRINTER_NOT_CONNECTED)
        payload = SDCPRequest.build(
            self.printer,
            SDCPCommand.SET_LIGHT_STATUS,
            {"LightStatus": {"SecondLight": 1 if enabled else 0, "RgbLight": [0, 0, 0]}},
            SDCPFrom.PC,
        )
        response = await self.printer.send_request_async(payload, timeout=self.timeout)
        if hasattr(response, "_message_json"):
            return response._message_json
        return {"response": response}

    def status_snapshot(self) -> dict[str, object]:
        """Return a simple snapshot of the current status."""
        if not self.printer:
            raise RuntimeError(_PRINTER_NOT_CONNECTED)
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
