"""
Loguru logging configuration with Sentry integration.

Features:
- Structured JSON logging for production
- Console logging for development
- Automatic Sentry breadcrumb integration
- Correlation ID in all log messages
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from core.correlation import get_correlation_id

if TYPE_CHECKING:
    from loguru import Record


def correlation_filter(record: "Record") -> bool:
    """
    Add correlation ID to log record.

    Args:
        record: Loguru log record.

    Returns:
        Always True (filter never drops messages).
    """
    record["extra"]["correlation_id"] = get_correlation_id() or "-"
    return True


def configure_logging(environment: str = "development") -> None:
    """
    Configure Loguru for the application.

    Args:
        environment: "development" for console, "production" for JSON.
    """
    # Remove default handler
    logger.remove()

    # Log format with correlation ID
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[correlation_id]}</cyan> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    if environment == "development":
        # Human-readable format for development
        logger.add(
            sys.stderr,
            format=log_format,
            level="DEBUG",
            filter=correlation_filter,
            colorize=True,
        )
    else:
        # JSON format for production (machine-parseable)
        logger.add(
            sys.stderr,
            format="{message}",
            level="INFO",
            filter=correlation_filter,
            serialize=True,  # JSON output
        )

    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Log to file with rotation
    logger.add(
        "logs/app.log",
        format=log_format if environment == "development" else "{message}",
        level="INFO",
        filter=correlation_filter,
        rotation="10 MB",
        retention="7 days",
        serialize=(environment != "development"),
    )
