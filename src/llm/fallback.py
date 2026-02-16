"""Fallback LLM provider when primary LLM is unavailable."""
import logging
import re
from typing import Any

from src.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class FallbackLLMProvider(LLMProvider):
    """Simple rule-based fallback when LLM is unavailable."""

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> str:
        """
        Simple rule-based intent detection as fallback.

        Args:
            messages: List of message dicts (we'll use the last user message)
            **kwargs: Ignored

        Returns:
            JSON string with intent data
        """
        # Extract last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        # Extract URLs using simple regex
        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, user_message)
        
        # Determine intent based on simple keywords
        message_lower = user_message.lower()
        intent = "unclear"
        confidence = 0.5
        
        if any(word in message_lower for word in ["print", "make", "create"]):
            intent = "print"
            confidence = 0.7
        elif any(word in message_lower for word in ["save", "bookmark", "later"]):
            intent = "save"
            confidence = 0.7
        elif any(word in message_lower for word in ["what", "info", "tell", "show", "details"]):
            intent = "info"
            confidence = 0.7
        elif urls:
            # If there's a URL but no clear intent keyword, assume print
            intent = "print"
            confidence = 0.6
        
        # Detect site
        site = None
        url = urls[0] if urls else None
        if url:
            if "printables.com" in url.lower():
                site = "printables"
            elif "thingiverse.com" in url.lower():
                site = "thingiverse"
        
        # Build JSON response
        result = {
            "intent": intent,
            "url": url,
            "site": site,
            "confidence": confidence,
            "material": "PLA",
            "color": "printer_default",
            "error": None,
        }
        
        import json
        return json.dumps(result)
