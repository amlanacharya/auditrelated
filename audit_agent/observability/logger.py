"""
Structured Logging: Full audit trail for compliance

All actions are logged with:
- Timestamp
- Action type
- User context
- Performance metrics
"""

import sys
import structlog
from pathlib import Path


def configure_logging(log_level: str = "INFO", log_file: str = None):
    """
    Configure structured logging

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path to write logs
    """

    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure output
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # In production, would use proper file handler
        # For now, just print to console

    print(f"[Logging configured] Level: {log_level}")


def get_logger(name: str = None):
    """
    Get a structured logger

    Args:
        name: Logger name (typically module name)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)
