import json
import logging
import os
import sys
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_instance_id(service_name: str) -> str:
    return os.getenv("INSTANCE_ID", f"{service_name}-{os.getpid()}")


class ServiceLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg: object, kwargs: dict) -> tuple[object, dict]:
        extra = dict(self.extra)
        extra.update(kwargs.get("extra", {}))
        kwargs["extra"] = extra
        return msg, kwargs


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": utc_now_iso(),
            "level": record.levelname,
            "service": getattr(record, "service_name", record.name),
            "message": record.getMessage(),
        }

        for key in (
            "event_id",
            "shipment_id",
            "event_type",
            "instance_id",
            "request_timestamp",
            "response_status",
            "latency_ms",
            "method",
            "path",
            "ready",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload)


def configure_logging(service_name: str) -> logging.Logger:
    root_logger = logging.getLogger()
    if not getattr(root_logger, "_thesis_json_logging", False):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        root_logger.handlers = [handler]
        root_logger.setLevel(logging.INFO)
        root_logger._thesis_json_logging = True

    logger = logging.getLogger(service_name)
    logger = ServiceLoggerAdapter(
        logger,
        {
            "service_name": service_name,
            "instance_id": get_instance_id(service_name),
        },
    )
    return logger
