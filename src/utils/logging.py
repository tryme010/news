"""Structured logging setup for the pipeline."""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(log_dir: str = "logs", run_id: str = "run") -> logging.Logger:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("news_bot")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JsonFormatter())
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(f"{log_dir}/{run_id}.log", encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
