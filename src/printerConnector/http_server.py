"""Simple HTTP server for serving files from a folder."""
from __future__ import annotations

import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional


class HttpFileServer:
    def __init__(self, root_dir: Path, host: str = "0.0.0.0", port: int = 0) -> None:
        self.root_dir = Path(root_dir)
        self.host = host
        self.port = port
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        handler = self._make_handler(self.root_dir)
        self._server = ThreadingHTTPServer((self.host, self.port), handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2)
        self._server = None
        self._thread = None

    def base_url(self, host: str) -> str:
        return f"http://{host}:{self.port}"

    @staticmethod
    def _make_handler(root_dir: Path):
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(root_dir), **kwargs)

            def log_message(self, format, *args):
                return

        return Handler
