"""Intent parser: detects URLs, validates supported sites, uses LLM to extract intent."""
import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.llm.base import LLMProvider
from src.llm.ollama import OllamaProvider

logger = logging.getLogger(__name__)


def _config_path(*parts: str) -> Path:
    """Return path under config/ relative to project root."""
    return Path(__file__).resolve().parent.parent.parent / "config" / Path(*parts)


def _load_intent_prompt() -> str:
    """Load intent parser prompt from config file."""
    path = _config_path("prompts", "intent_parser.txt")
    if not path.exists():
        raise FileNotFoundError(f"Intent prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def load_supported_domains() -> tuple[set[str], list[str]]:
    """
    Load supported domains from config file.

    Returns:
        Tuple of (set of domain strings for validation, list of base domains for regex).
        Domain set includes both 'example.com' and 'www.example.com' for each entry.
    """
    path = _config_path("supported_domains.json")
    if not path.exists():
        raise FileNotFoundError(f"Supported domains file not found: {path}")
    raw: list[str] = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not all(isinstance(d, str) for d in raw):
        raise ValueError("supported_domains.json must be a list of strings")
    domain_set: set[str] = set()
    base_domains: list[str] = []
    for d in raw:
        d = d.lower().strip()
        if not d or d.startswith("www."):
            continue
        domain_set.add(d)
        domain_set.add(f"www.{d}")
        base_domains.append(d)
    return domain_set, base_domains


def load_intent_schema() -> dict[str, Any]:
    """Load intent JSON schema from config file."""
    path = _config_path("intent_schema.json")
    if not path.exists():
        raise FileNotFoundError(f"Intent schema file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class IntentParser:
    """Parses user intent from messages, detecting URLs and using LLM for intent extraction."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        prompt_template: str | None = None,
        supported_domains: tuple[set[str], list[str]] | None = None,
    ):
        """
        Initialize intent parser.

        Args:
            llm_provider: LLM provider instance (defaults to OllamaProvider)
            prompt_template: Override prompt template (defaults to config/prompts/intent_parser.txt)
            supported_domains: Override (domain_set, base_domains) (defaults to config/supported_domains.json)
        """
        self.llm = llm_provider or OllamaProvider()
        self._prompt_template = prompt_template if prompt_template is not None else _load_intent_prompt()
        domain_set, base_domains = supported_domains if supported_domains is not None else load_supported_domains()
        self._supported_domains = domain_set
        self._base_domains = base_domains
        # Build URL regex from base domains (e.g. printables\.com|thingiverse\.com)
        domain_alternation = "|".join(re.escape(d) for d in base_domains)
        self.url_pattern = re.compile(
            rf"https?://(?:www\.)?({domain_alternation})[^\s]*",
            re.IGNORECASE,
        )

    def extract_urls(self, text: str) -> list[str]:
        """
        Extract URLs from text that match supported domains.

        Args:
            text: User message text

        Returns:
            List of detected URLs
        """
        matches = self.url_pattern.findall(text)
        # Reconstruct full URLs
        urls = []
        for match in self.url_pattern.finditer(text):
            urls.append(match.group(0))
        return urls

    def validate_url(self, url: str) -> tuple[bool, str | None]:
        """
        Validate if URL is from a supported site.

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid, site_name)
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain in self._supported_domains:
                normalized = domain[4:] if domain.startswith("www.") else domain
                site = normalized.split(".", 1)[0]
                return True, site
            return False, None
        except Exception as e:
            logger.warning(f"URL validation error for {url}: {e}")
            return False, None

    async def parse(self, user_message: str) -> dict[str, Any]:
        """
        Parse user intent from message.

        Args:
            user_message: User's message text

        Returns:
            Intent dict matching the schema in config/intent_schema.json
        """
        # Extract URLs
        urls = self.extract_urls(user_message)
        urls_str = ", ".join(urls) if urls else "None"

        # Validate URLs
        validated_urls = []
        errors = []
        for url in urls:
            is_valid, site = self.validate_url(url)
            if is_valid:
                validated_urls.append(url)
            else:
                errors.append(f"Unsupported or invalid URL: {url}")

        # If we have URLs but none are valid, return error early
        if urls and not validated_urls:
            return {
                "intent": "unclear",
                "url": urls[0] if urls else None,
                "site": None,
                "confidence": 0.0,
                "material": "PLA",
                "color": "printer_default",
                "error": "; ".join(errors),
            }

        # Use first validated URL (or None)
        primary_url = validated_urls[0] if validated_urls else None
        primary_site = None
        if primary_url:
            _, primary_site = self.validate_url(primary_url)

        # Build LLM prompt
        prompt = self._prompt_template.format(
            user_message=user_message,
            urls=urls_str,
        )

        messages = [
            {"role": "system", "content": "You are a precise JSON-only intent parser. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            # Call LLM
            logger.info("Calling LLM for intent parsing (user_message=%r)", user_message[:80] + "..." if len(user_message) > 80 else user_message)
            response = await self.llm.chat(messages, temperature=0.1)  # Low temperature for consistency
            logger.info("LLM response received (length=%d)", len(response))

            # Parse JSON response
            # LLM might wrap in markdown code blocks or add extra text
            response = response.strip()
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            # Some LLMs emit \/ in URLs (invalid JSON); normalize to /
            response = response.replace(r"\/", "/")

            intent_data = json.loads(response)

            # Ensure required fields and defaults
            result = {
                "intent": intent_data.get("intent", "unclear"),
                "url": intent_data.get("url") or primary_url,
                "site": intent_data.get("site") or primary_site,
                "confidence": float(intent_data.get("confidence", 0.0)),
                "material": intent_data.get("material", "PLA"),
                "color": intent_data.get("color", "printer_default"),
                "error": intent_data.get("error"),
            }

            # Validate intent enum
            if result["intent"] not in ["print", "save", "info", "unclear"]:
                result["intent"] = "unclear"
                result["confidence"] = 0.0
                result["error"] = "Invalid intent value from LLM"

            # If we had validation errors, merge them
            if errors and not result.get("error"):
                result["error"] = "; ".join(errors)
            elif errors and result.get("error"):
                result["error"] = result["error"] + "; " + "; ".join(errors)

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}\nResponse: {response}")
            return {
                "intent": "unclear",
                "url": primary_url,
                "site": primary_site,
                "confidence": 0.0,
                "material": "PLA",
                "color": "printer_default",
                "error": f"Failed to parse LLM response as JSON: {e}",
            }
        except Exception as e:
            logger.error(f"Intent parsing error: {e}")
            return {
                "intent": "unclear",
                "url": primary_url,
                "site": primary_site,
                "confidence": 0.0,
                "material": "PLA",
                "color": "printer_default",
                "error": f"Intent parsing failed: {e}",
            }
