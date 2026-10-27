import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# Request ID bieżącego requestu, widoczny w całym kodzie obsługującym ten request
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    """Zamienia każdy rekord logu na jedną linię JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": "payments",
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }

        # Dodatkowe pola przekazane przez extra={"fields": {...}}
        fields = getattr(record, "fields", None)
        if fields:
            log.update(fields)

        # Pełny traceback, jeśli logujemy wyjątek
        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        return json.dumps(log, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
