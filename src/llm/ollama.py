"""Ollama LLM provider (localhost default)."""
import logging
import os
from typing import Any

import httpx

from src.llm.base import LLMProvider

logger = logging.getLogger(__name__)

# Constants
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_OLLAMA_TIMEOUT = 30.0


class OllamaProvider(LLMProvider):
    """Ollama LLM provider for localhost or remote Ollama instance."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = DEFAULT_OLLAMA_TIMEOUT,
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama API base URL (default: http://localhost:11434)
            model: Model name to use (default: llama3.2)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Send chat request to Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Optional: temperature, top_p, etc.

        Returns:
            Generated text response
        """
        # Convert messages to Ollama format
        # Ollama expects 'role' and 'content' which matches our format
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            **kwargs,  # Allow passing temperature, top_p, etc.
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            raw_content = data.get("message", {}).get("content", "")
            logger.info("LLM raw response: %s", raw_content)
            return raw_content
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise RuntimeError(f"Failed to call Ollama: {e}") from e

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
