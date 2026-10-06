import json
import logging
import sys
import time
import uuid
from collections import Counter
from typing import Any

_metrics: Counter = Counter()
_started_at = time.time()

_LOG_STANDARD_ATTRS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "message", "module",
    "msecs", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": record.created,
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _LOG_STANDARD_ATTRS or key.startswith("_"):
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_json_logging(level: str = "INFO") -> None:
    """Route all logs to stdout as one JSON object per line. Idempotent."""
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)
    root.setLevel(level)


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def incr(event: str, **labels: str) -> None:
    _metrics[_key(event, labels)] += 1


def snapshot() -> dict[str, int]:
    """Return a plain-dict copy of the counter for JSON serialization."""
    return dict(_metrics)


def reset_metrics() -> None:
    """Test helper. Do not call from production paths."""
    _metrics.clear()


def uptime_seconds() -> float:
    return time.time() - _started_at


def _key(event: str, labels: dict[str, str]) -> str:
    if not labels:
        return event
    label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    return f"{event}{{{label_str}}}"
