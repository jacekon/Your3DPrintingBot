"""
Cassini-based printer client wrapper.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from src.printerConnector.cassini.saturn_printer import SaturnPrinter
from src.printerConnector.cassini.simple_http_server import SimpleHTTPServer
from src.printerConnector.cassini.simple_mqtt_server import SimpleMQTTServer


class CassiniClient:
    def __init__(self, printer_ip: Optional[str] = None, timeout: int = 5, broadcast: Optional[str] = None) -> None:
        self.printer_ip = printer_ip
        self.broadcast = broadcast
        self.timeout = timeout
        self.printer: Optional[SaturnPrinter] = None
        self.mqtt: Optional[SimpleMQTTServer] = None
        self.http: Optional[SimpleHTTPServer] = None
        self._tasks: list[asyncio.Task] = []

    @staticmethod
    def discover(broadcast: Optional[str] = None, timeout: int = 1) -> list[SaturnPrinter]:
        return SaturnPrinter.find_printers(timeout=timeout, broadcast=broadcast)

    async def connect(self) -> None:
        if self.printer_ip:
            printer = SaturnPrinter.find_printer(self.printer_ip)
            if printer is None:
                raise RuntimeError(f"No response from printer at {self.printer_ip}")
        else:
            printers = SaturnPrinter.find_printers(broadcast=self.broadcast)
            if not printers:
                raise RuntimeError("No printers found on network")
            printer = printers[0]

        self.printer = printer

        self.mqtt = SimpleMQTTServer("0.0.0.0", 0)
        await self.mqtt.start()
        self._tasks.append(asyncio.create_task(self.mqtt.serve_forever()))

        self.http = SimpleHTTPServer("0.0.0.0", 0)
        await self.http.start()
        self._tasks.append(asyncio.create_task(self.http.serve_forever()))

        connected = await self.printer.connect(self.mqtt, self.http)
        if not connected:
            raise RuntimeError("Failed to connect to printer")

    async def upload_gcode(self, gcode_path: str) -> str:
        if not self.printer:
            raise RuntimeError("Printer is not connected")
        path = Path(gcode_path)
        await self.printer.upload_file(str(path), start_printing=False)
        return path.name

    async def start_print(self, filename: str) -> bool:
        if not self.printer:
            raise RuntimeError("Printer is not connected")
        return await self.printer.print_file(filename)

    async def close(self) -> None:
        if self.printer:
            try:
                await self.printer.disconnect()
            except Exception:
                pass

        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

        if self.http and self.http.server:
            self.http.server.close()
            await self.http.server.wait_closed()
        if self.mqtt and self.mqtt.server:
            self.mqtt.server.close()
            await self.mqtt.server.wait_closed()

        self.printer = None
        self.http = None
        self.mqtt = None
