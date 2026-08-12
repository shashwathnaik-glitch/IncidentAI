"""Structured logging configuration for IncidentMind Backend."""

import logging
import sys
from typing import Any, Dict


class StructuredLogFormatter(logging.Formatter):
    """Custom log formatter formatting log events into structured console output."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_data.update(record.extra_data)
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return f"[{log_data['timestamp']}] [{log_data['level']}] [{log_data['logger']}]: {log_data['message']}"


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure root logger with structured formatting."""
    logger = logging.getLogger("incidentmind")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredLogFormatter())
        logger.addHandler(handler)
        
    return logger


logger = setup_logging()
