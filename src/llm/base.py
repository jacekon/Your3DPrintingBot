"""Base interface for LLM providers."""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(self, messages: list[dict[str, str]], **kwargs) -> str:
        """
        Send a chat request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                     Roles: 'system', 'user', 'assistant'
            **kwargs: Provider-specific options (temperature, max_tokens, etc.)

        Returns:
            Generated text response from the LLM
        """
        pass
