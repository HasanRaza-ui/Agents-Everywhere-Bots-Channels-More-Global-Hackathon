"""Environment-backed configuration and OpenAI key-pool plumbing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Mapping, TypeVar

from dotenv import load_dotenv
import structlog


T = TypeVar("T")
logger = structlog.get_logger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when required local configuration is missing."""


def _should_rotate(error: BaseException | None) -> bool:
    if error is None:
        return False
    if getattr(error, "status_code", None) == 429:
        return True
    if getattr(error, "code", None) == "insufficient_quota":
        return True
    body = getattr(error, "body", None)
    if isinstance(body, Mapping) and body.get("code") == "insufficient_quota":
        return True
    return "insufficient_quota" in str(error)


class OpenAIKeyPool:
    """Sticky failover pool that never exposes key material in diagnostics."""

    def __init__(self, keys: list[str]) -> None:
        self._keys = [key for key in keys if key.strip()]
        self._current_index = 0
        if not self._keys:
            raise ConfigurationError(
                "No OpenAI API key is configured. Set OPENAI_API_KEY (or _2/_3) in .env."
            )

    def next_key(self, error: BaseException | None = None) -> str:
        """Return the current key, failing over only after quota/rate-limit errors."""
        if _should_rotate(error):
            self._current_index = (self._current_index + 1) % len(self._keys)
            logger.warning("openai_key_rotated", key_index=self._current_index)
        return self._keys[self._current_index]


@dataclass(frozen=True)
class Settings:
    openrouter_configured: bool
    challenger_model_configured: bool

    @property
    def services(self) -> dict[str, bool]:
        return {
            "OpenAI": True,
            "OpenRouter": self.openrouter_configured,
            "Challenger model": self.challenger_model_configured,
            "Telegram": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
            "Slack": bool(os.getenv("SLACK_BOT_TOKEN")),
        }


_pool: OpenAIKeyPool | None = None


def load_settings() -> Settings:
    """Load .env and validate required startup configuration."""
    load_dotenv()
    _get_pool()
    return Settings(
        openrouter_configured=bool(os.getenv("OPENROUTER_API_KEY")),
        challenger_model_configured=bool(os.getenv("CHALLENGER_MODEL")),
    )


def _get_pool() -> OpenAIKeyPool:
    global _pool
    if _pool is None:
        _pool = OpenAIKeyPool(
            [
                os.getenv("OPENAI_API_KEY", ""),
                os.getenv("OPENAI_API_KEY_2", ""),
                os.getenv("OPENAI_API_KEY_3", ""),
            ]
        )
    return _pool


def next_openai_key(error: BaseException | None = None) -> str:
    """Get the sticky key, failing over after a rate-limit or quota failure."""
    return _get_pool().next_key(error)


def call_with_key_rotation(
    fn: Callable[[str], T], *, max_attempts: int | None = None
) -> T:
    """Call ``fn`` with the sticky key and retry rate/quota failures after failover."""
    pool = _get_pool()
    attempts = max_attempts if max_attempts is not None else len(pool._keys)
    if attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    for attempt in range(attempts):
        try:
            return fn(next_openai_key())
        except BaseException as error:
            if not _should_rotate(error) or attempt == attempts - 1:
                raise
            next_openai_key(error)

    raise RuntimeError("Key rotation retry loop ended unexpectedly")


def reset_key_pool_for_tests() -> None:
    """Clear process-local state for isolated tests."""
    global _pool
    _pool = None
