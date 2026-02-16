"""Security features for the bot: rate limiting, input validation, user whitelist."""
import logging
import os
import time
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

# Constants
MAX_MESSAGE_LENGTH = 2000
MAX_MESSAGES_PER_MINUTE = 10
MAX_MESSAGES_PER_HOUR = 100


class RateLimiter:
    """Rate limiter to prevent abuse."""

    def __init__(
        self,
        max_per_minute: int = MAX_MESSAGES_PER_MINUTE,
        max_per_hour: int = MAX_MESSAGES_PER_HOUR,
    ):
        """
        Initialize rate limiter.

        Args:
            max_per_minute: Maximum messages per minute per user
            max_per_hour: Maximum messages per hour per user
        """
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self._minute_counts: dict[int, list[float]] = defaultdict(list)
        self._hour_counts: dict[int, list[float]] = defaultdict(list)

    def check_rate_limit(self, user_id: int) -> tuple[bool, str | None]:
        """
        Check if user has exceeded rate limits.

        Args:
            user_id: Telegram user ID

        Returns:
            Tuple of (is_allowed, error_message)
        """
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        # Clean old entries
        self._minute_counts[user_id] = [t for t in self._minute_counts[user_id] if t > minute_ago]
        self._hour_counts[user_id] = [t for t in self._hour_counts[user_id] if t > hour_ago]

        # Check limits
        if len(self._minute_counts[user_id]) >= self.max_per_minute:
            return False, f"Rate limit exceeded: {self.max_per_minute} messages per minute"
        if len(self._hour_counts[user_id]) >= self.max_per_hour:
            return False, f"Rate limit exceeded: {self.max_per_hour} messages per hour"

        # Record this message
        self._minute_counts[user_id].append(now)
        self._hour_counts[user_id].append(now)
        return True, None


class UserWhitelist:
    """Manage allowed users."""

    def __init__(self, allowed_user_ids: list[int] | None = None):
        """
        Initialize whitelist.

        Args:
            allowed_user_ids: List of allowed Telegram user IDs. If None/empty, all users allowed.
        """
        self.allowed_user_ids = set(allowed_user_ids) if allowed_user_ids else None
        self.enabled = self.allowed_user_ids is not None and len(self.allowed_user_ids) > 0

    @classmethod
    def from_env(cls) -> "UserWhitelist":
        """Load whitelist from ALLOWED_USER_IDS environment variable (comma-separated)."""
        allowed_ids_str = os.getenv("ALLOWED_USER_IDS", "").strip()
        if not allowed_ids_str:
            logger.info("No user whitelist configured (all users allowed)")
            return cls(None)

        try:
            allowed_ids = [int(uid.strip()) for uid in allowed_ids_str.split(",") if uid.strip()]
            logger.info(f"User whitelist enabled with {len(allowed_ids)} allowed user(s)")
            return cls(allowed_ids)
        except ValueError as e:
            logger.error(f"Invalid ALLOWED_USER_IDS format: {e}. Allowing all users.")
            return cls(None)

    def is_allowed(self, user_id: int) -> tuple[bool, str | None]:
        """
        Check if user is allowed.

        Args:
            user_id: Telegram user ID

        Returns:
            Tuple of (is_allowed, error_message)
        """
        if not self.enabled:
            return True, None

        if user_id in self.allowed_user_ids:
            return True, None

        logger.warning(f"Unauthorized access attempt from user_id={user_id}")
        return False, "You are not authorized to use this bot."


def validate_message(message: str) -> tuple[bool, str | None]:
    """
    Validate user message content.

    Args:
        message: User message text

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not message or not message.strip():
        return False, "Empty message"

    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"Message too long (max {MAX_MESSAGE_LENGTH} characters)"

    # Basic sanitization checks - reject messages with suspicious patterns
    suspicious_patterns = ["<script", "javascript:", "data:text/html"]
    message_lower = message.lower()
    for pattern in suspicious_patterns:
        if pattern in message_lower:
            logger.warning(f"Suspicious pattern detected in message: {pattern}")
            return False, "Message contains suspicious content"

    return True, None


class SecurityManager:
    """Centralized security management."""

    def __init__(
        self,
        whitelist: UserWhitelist | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        """
        Initialize security manager.

        Args:
            whitelist: User whitelist instance
            rate_limiter: Rate limiter instance
        """
        self.whitelist = whitelist or UserWhitelist.from_env()
        self.rate_limiter = rate_limiter or RateLimiter()

    def check_security(self, user_id: int, message: str) -> tuple[bool, str | None]:
        """
        Perform all security checks.

        Args:
            user_id: Telegram user ID
            message: User message text

        Returns:
            Tuple of (is_allowed, error_message)
        """
        # Check whitelist
        is_allowed, error = self.whitelist.is_allowed(user_id)
        if not is_allowed:
            return False, error

        # Check rate limit
        is_allowed, error = self.rate_limiter.check_rate_limit(user_id)
        if not is_allowed:
            return False, error

        # Validate message content
        is_valid, error = validate_message(message)
        if not is_valid:
            return False, error

        return True, None
