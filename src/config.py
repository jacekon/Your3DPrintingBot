"""Centralized configuration and logging setup."""
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


# Constants
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str | None = None, format_str: str | None = None) -> None:
    """
    Setup centralized logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_str: Log message format
    """
    log_level = level or os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    log_format = format_str or os.getenv("LOG_FORMAT", DEFAULT_LOG_FORMAT)
    
    logging.basicConfig(
        format=log_format,
        level=getattr(logging, log_level, logging.INFO),
        datefmt=DEFAULT_LOG_DATE_FORMAT,
        force=True,  # Override any existing configuration
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_level}")


class Config:
    """Application configuration with validation."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        # Load .env file if it exists
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        
        # Required settings
        self.telegram_bot_token = self._get_required("TELEGRAM_BOT_TOKEN")
        
        # Optional LLM settings
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        
        # Optional security settings
        self.allowed_user_ids = self._parse_user_ids(os.getenv("ALLOWED_USER_IDS", ""))
        
        # Optional printer settings
        self.printer_ip = os.getenv("PRINTER_IP")
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

    def _get_required(self, key: str) -> str:
        """Get required environment variable or exit."""
        value = os.getenv(key)
        if not value:
            print(f"ERROR: Required environment variable {key} not set", file=sys.stderr)
            print(f"Please set {key} in your .env file or environment", file=sys.stderr)
            sys.exit(1)
        return value

    def _parse_user_ids(self, ids_str: str) -> list[int]:
        """Parse comma-separated user IDs."""
        if not ids_str.strip():
            return []
        try:
            return [int(uid.strip()) for uid in ids_str.split(",") if uid.strip()]
        except ValueError:
            logger = logging.getLogger(__name__)
            logger.error(f"Invalid ALLOWED_USER_IDS format: {ids_str}")
            return []

    def validate(self) -> list[str]:
        """
        Validate configuration.

        Returns:
            List of validation warnings (empty if all OK)
        """
        warnings = []

        # Check Ollama connectivity (optional warning)
        if not self.ollama_base_url.startswith("http"):
            warnings.append(f"OLLAMA_BASE_URL should start with http:// or https://: {self.ollama_base_url}")

        # Warn if no user whitelist is configured
        if not self.allowed_user_ids:
            warnings.append("No ALLOWED_USER_IDS configured - bot is accessible to all users")

        return warnings

    def __repr__(self) -> str:
        """String representation (hiding sensitive data)."""
        return (
            f"Config(telegram_bot_token=*****, "
            f"ollama_base_url={self.ollama_base_url}, "
            f"ollama_model={self.ollama_model}, "
            f"allowed_users={len(self.allowed_user_ids)}, "
            f"printer_ip={self.printer_ip or 'not set'})"
        )


def load_config() -> Config:
    """Load and validate configuration."""
    config = Config()
    
    logger = logging.getLogger(__name__)
    logger.info(f"Configuration loaded: {config}")
    
    warnings = config.validate()
    for warning in warnings:
        logger.warning(warning)
    
    return config
