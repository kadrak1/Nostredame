"""Structlog configuration for HookahBook.

Development  → colorized, human-readable console output.
Production   → JSON Lines — machine-parseable, suited for log aggregation.

Call ``setup_logging()`` exactly once at application startup.
"""

import logging
import sys
from typing import Any

import structlog


def setup_logging(*, debug: bool = False) -> None:
    """Configure structlog.  Must be called before any logger is used."""

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        # add_logger_name removed: incompatible with PrintLoggerFactory (no .name attr)
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    if debug:
        processors: list[Any] = shared_processors + [
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = shared_processors + [
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Silence noisy stdlib loggers that would duplicate output
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
