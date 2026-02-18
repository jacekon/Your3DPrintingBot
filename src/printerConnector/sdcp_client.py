"""SDCP (ElegooLink) client for local network printer control.

This client is intentionally minimal:
- UDP broadcast discovery (M99999 on port 3000)
- WebSocket control/status channel (ws://{ip}:3030/websocket)

It does NOT upload or start prints yet. It only connects and queries basic status.
"""
from __future__ import annotations

import asyncio
import json
import logging
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

import paho.mqtt.client as mqtt
import websockets

logger = logging.getLogger(__name__)


@dataclass
class SdcpDevice:
    ip: str
    raw: str


class SdcpClient:
    """SDCP (ElegooLink) client.

    Supports:
    - UDP broadcast discovery (M99999 on port 3000)
    - Optional MQTT workflow (register broker via M66666 <port>)
    - WebSocket control/status channel (ws://{ip}:3030/websocket)

    Note: Some printer firmware revisions prefer MQTT for status/commands.
    """

    def __init__(self, ip: str, ws_port: int = 3030, udp_port: int = 3000) -> None:
        self.ip = ip
        self.ws_port = ws_port
        self.udp_port = udp_port
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._ws_task: Optional[asyncio.Task[None]] = None
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._status_queue: Optional[asyncio.Queue[dict[str, Any]]] = None
        self._mqtt: Optional[mqtt.Client] = None
        self._mqtt_loop: Optional[asyncio.AbstractEventLoop] = None
        self._mqtt_queue: Optional[asyncio.Queue[dict[str, Any]]] = None
        self._mqtt_connected = threading.Event()
        self._mqtt_mainboard_id: Optional[str] = None
        self._mainboard_id: Optional[str] = None
        self._mainboard_ip: Optional[str] = None

    @staticmethod
    def discover(timeout: float = 2.0) -> list[SdcpDevice]:
        """Broadcast discovery ping and return any responses."""
        msg = b"M99999"
        broadcasts = ["255.255.255.255"]
        devices: list[SdcpDevice] = []

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        try:
            for bcast in broadcasts:
                sock.sendto(msg, (bcast, 3000))

            while True:
                try:
                    data, addr = sock.recvfrom(4096)
                    devices.append(SdcpDevice(ip=addr[0], raw=data.decode(errors="ignore")))
                except socket.timeout:
                    break
        finally:
            sock.close()

        return devices

    def register_mqtt_broker(self, broker_port: int) -> None:
        """Tell the printer which MQTT broker port to use.

        SDCP expects a UDP command: M66666 <port>
        """
        msg = f"M66666 {broker_port}".encode()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(msg, (self.ip, self.udp_port))
        finally:
            sock.close()

    def connect_mqtt(
        self,
        broker_host: str,
        broker_port: int,
        mainboard_id: str,
        client_id: Optional[str] = None,
    ) -> None:
        """Connect to an MQTT broker and subscribe to SDCP response topic."""
        self._mqtt_loop = asyncio.get_event_loop()
        self._mqtt_queue = asyncio.Queue()
        self._mqtt_mainboard_id = mainboard_id

        def on_connect(client: mqtt.Client, _userdata: Any, _flags: dict[str, Any], rc: int) -> None:
            if rc == 0:
                client.subscribe(self._topic_response(mainboard_id))
                self._mqtt_connected.set()
            else:
                logger.error("MQTT connect failed: rc=%s", rc)

        def on_message(_client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
            try:
                payload = json.loads(msg.payload.decode())
            except Exception:
                payload = {"raw": msg.payload.decode(errors="ignore")}

            if self._mqtt_loop and self._mqtt_queue:
                self._mqtt_loop.call_soon_threadsafe(self._mqtt_queue.put_nowait, payload)

        self._mqtt = mqtt.Client(client_id or f"sdcp-{uuid.uuid4().hex[:8]}")
        self._mqtt.on_connect = on_connect
        self._mqtt.on_message = on_message
        self._mqtt.connect(broker_host, broker_port, keepalive=30)
        self._mqtt.loop_start()

        if not self._mqtt_connected.wait(timeout=5):
            raise RuntimeError("MQTT connection timed out")

    def disconnect_mqtt(self) -> None:
        if self._mqtt:
            self._mqtt.loop_stop()
            self._mqtt.disconnect()
            self._mqtt = None
            self._mqtt_connected.clear()

    async def mqtt_request(self, payload: dict[str, Any], timeout: float = 5.0) -> dict[str, Any]:
        """Publish a request and wait for one response message."""
        if not self._mqtt or not self._mqtt_queue or not self._mqtt_mainboard_id:
            raise RuntimeError("MQTT not connected")

        payload = {
            "request_id": payload.get("request_id") or str(uuid.uuid4()),
            "timestamp": payload.get("timestamp") or int(time.time()),
            **payload,
        }
        topic = self._topic_request(self._mqtt_mainboard_id)
        self._mqtt.publish(topic, json.dumps(payload))

        response = await asyncio.wait_for(self._mqtt_queue.get(), timeout=timeout)
        return response

    async def connect(
        self,
        ws_ports: Optional[list[int]] = None,
        paths: Optional[list[str]] = None,
    ) -> None:
        """Connect to the printer WebSocket channel.

        Tries provided ports (default: 3031 then 3030).
        """
        ports = ws_ports or [3031, self.ws_port]
        path_candidates = paths or ["/websocket", "/ws", "/"]
        last_error: Optional[Exception] = None

        for port in ports:
            for path in path_candidates:
                uri = f"ws://{self.ip}:{port}{path}"
                logger.info("Connecting to SDCP WebSocket: %s", uri)
                try:
                    self._ws = await websockets.connect(
                        uri,
                        ping_interval=30,
                        ping_timeout=10,
                        open_timeout=5,
                    )
                            self._status_queue = asyncio.Queue()
                    self._ws_task = asyncio.create_task(self._ws_reader())
                    return
                except Exception as exc:
                    if self._ws:
                        try:
                            await self._ws.close()
                        except Exception:
                            pass
                        self._ws = None
                    last_error = exc
                    logger.warning("WebSocket connect failed for %s: %s", uri, exc)

        raise TimeoutError("timed out during opening handshake") from last_error

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            await self._ws.close()
            self._ws = None
        if self._ws_task:
            self._ws_task.cancel()
            self._ws_task = None
        if self._status_queue:
            while not self._status_queue.empty():
                self._status_queue.get_nowait()
            self._status_queue = None
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()

    async def send(self, payload: dict[str, Any]) -> None:
        """Send a JSON payload to the printer."""
        if not self._ws:
            raise RuntimeError("Not connected")
        await self._ws.send(json.dumps(payload))

    async def recv(self, timeout: float = 5.0) -> dict[str, Any]:
        """Receive one JSON message from the printer."""
        if not self._ws:
            raise RuntimeError("Not connected")
        raw = await asyncio.wait_for(self._ws.recv(), timeout=timeout)
        return json.loads(raw)

    async def _ws_reader(self) -> None:
        if not self._ws:
            return
        try:
            async for message in self._ws:
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    continue

                topic = payload.get("Topic")
                if topic and topic.startswith("sdcp/status/"):
                    if self._status_queue:
                        self._status_queue.put_nowait(payload)

                data = payload.get("Data", {})
                request_id = data.get("RequestID") or data.get("request_id")
                if request_id and request_id in self._pending:
                    future = self._pending.pop(request_id)
                    if not future.done():
                        future.set_result(payload)
        except asyncio.CancelledError:
            return

    async def wait_for_status(self, timeout: float = 5.0) -> dict[str, Any]:
        """Wait for a status topic message after a Cmd 0 request."""
        if not self._ws or not self._status_queue:
            raise RuntimeError("Not connected")
        return await asyncio.wait_for(self._status_queue.get(), timeout=timeout)

    def _build_payload(self, cmd: int, data: Optional[dict[str, Any]] = None) -> tuple[str, dict[str, Any]]:
        request_id = uuid.uuid4().hex
        payload = {
            "Id": "",
            "Data": {
                "Cmd": cmd,
                "Data": data or {},
                "RequestID": request_id,
                "MainboardID": self._mainboard_id or "",
                "TimeStamp": int(time.time()),
                "From": 1,
            },
        }
        return request_id, payload

    async def send_cmd(self, cmd: int, data: Optional[dict[str, Any]] = None, timeout: float = 5.0) -> dict[str, Any]:
        """Send an SDCP command and wait for the response matching RequestID."""
        if not self._ws:
            raise RuntimeError("Not connected")

        request_id, payload = self._build_payload(cmd, data)
        future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future
        await self.send(payload)
        response = await asyncio.wait_for(future, timeout=timeout)
        return response

    async def get_status(self) -> dict[str, Any]:
        """Cmd 0: Request status update."""
        return await self.send_cmd(0)

    async def get_device_attributes(self) -> dict[str, Any]:
        """Cmd 1: Get device attributes (name, firmware, capabilities)."""
        response = await self.send_cmd(1)
        data = response.get("Data", {}) if isinstance(response, dict) else {}
        mainboard_id = response.get("MainboardID") or data.get("MainboardID")
        mainboard_ip = data.get("MainboardIP")
        if mainboard_id:
            self._mainboard_id = mainboard_id
        if mainboard_ip:
            self._mainboard_ip = mainboard_ip
        return response

    async def list_files(self, directory: str = "/local") -> dict[str, Any]:
        """Cmd 258: List files in a directory (default /local)."""
        return await self.send_cmd(258, {"Url": directory})

    @staticmethod
    def _topic_request(mainboard_id: str) -> str:
        return f"/sdcp/request/{mainboard_id}"

    @staticmethod
    def _topic_response(mainboard_id: str) -> str:
        return f"/sdcp/response/{mainboard_id}"
