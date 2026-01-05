"""
Rate Limit Service - Business logic for rate limiting operations.

Handles rate limiting for exports and other rate-limited operations.
This service follows the pattern of other services (static methods, domain exceptions).

Note: Current implementation uses in-memory storage. For production with
multiple instances, replace with Redis-backed storage.
"""

import time
from typing import Dict, List

from models.exceptions import RateLimitExceededException


class RateLimitService:
    """Service for managing rate limits."""

    # In-memory storage for rate limits (replace with Redis in production)
    _export_limits: Dict[int, List[float]] = {}

    # Default configuration - can be moved to config.py if needed
    DEFAULT_EXPORT_LIMIT = 10  # Max exports per hour
    DEFAULT_EXPORT_WINDOW = 3600  # 1 hour in seconds

    @staticmethod
    def check_export_rate_limit(
        user_id: int,
        limit: int = DEFAULT_EXPORT_LIMIT,
        window: int = DEFAULT_EXPORT_WINDOW,
    ) -> None:
        """
        Check if user has exceeded export rate limit.

        Args:
            user_id: ID of the user making the export request
            limit: Maximum number of exports allowed in the window
            window: Time window in seconds

        Raises:
            RateLimitExceededException: If rate limit is exceeded
        """
        now = time.time()
        window_start = now - window

        # Get user's export timestamps
        timestamps = RateLimitService._export_limits.get(user_id, [])

        # Filter to recent window
        recent = [t for t in timestamps if t > window_start]

        if len(recent) >= limit:
            # Calculate retry after time
            oldest_in_window = min(recent) if recent else now
            retry_after = int(oldest_in_window + window - now)
            raise RateLimitExceededException(
                message="Export rate limit exceeded. Please try again later.",
                retry_after=retry_after,
            )

        # Record this export
        recent.append(now)
        RateLimitService._export_limits[user_id] = recent

    @staticmethod
    def reset_user_limits(user_id: int) -> None:
        """
        Reset rate limits for a specific user.

        Useful for testing or admin operations.

        Args:
            user_id: ID of the user whose limits should be reset
        """
        if user_id in RateLimitService._export_limits:
            del RateLimitService._export_limits[user_id]

    @staticmethod
    def get_remaining_exports(
        user_id: int,
        limit: int = DEFAULT_EXPORT_LIMIT,
        window: int = DEFAULT_EXPORT_WINDOW,
    ) -> int:
        """
        Get the number of remaining exports for a user.

        Args:
            user_id: ID of the user
            limit: Maximum number of exports allowed in the window
            window: Time window in seconds

        Returns:
            Number of remaining exports available
        """
        now = time.time()
        window_start = now - window

        timestamps = RateLimitService._export_limits.get(user_id, [])
        recent = [t for t in timestamps if t > window_start]

        return max(0, limit - len(recent))
