"""
Structured JSON logging (blueprint §9, Twelve-Factor logs to stdout).

One setup shared by every service so logs are consistent and machine-parseable
(and so Cloud Logging log-based metrics can extract fields like groundedness).
PII is redacted upstream (safety_policy.redact) before anything is logged.
"""
from __future__ import annotations

import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def setup_logging(service_name: str, level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Route uvicorn through the same JSON handler.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
