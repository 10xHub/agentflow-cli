from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitDecision:
    """Result of a single rate-limit check."""

    allowed: bool
    remaining: int
    reset_after: int


class BaseRateLimitBackend(ABC):
    """Abstract base class for rate-limit backends.

    Users can implement this class and bind an instance into InjectQ when they
    need a backend other than the built-in memory or Redis implementations.
    """

    @abstractmethod
    async def check(self, key: str, *, limit: int, window: int) -> RateLimitDecision:
        """Atomically check and record a request for *key*."""

    @abstractmethod
    async def close(self) -> None:
        """Release resources held by the backend, if any."""
