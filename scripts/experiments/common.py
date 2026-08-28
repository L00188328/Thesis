import argparse
import ipaddress
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)(sharedaccesskey|password|passwd|token|secret|api[_-]?key|sig|subscription[_-]?id)"
    r"([\"']?\s*[=:]\s*)([\"']?)([^\s,;\"']+)([\"']?)"
)
EVENT_HUBS_ENDPOINT_PATTERN = re.compile(r"(?i)Endpoint=sb://[^;\s]+")
URI_CREDENTIAL_PATTERN = re.compile(
    r"(?P<prefix>[a-z][a-z0-9+.-]*://[^\s:/@]+:)(?P<password>[^\s@]+)(?P<suffix>@)",
    re.IGNORECASE,
)
SUBSCRIPTION_PATTERN = re.compile(
    r"(?i)(/subscriptions/)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
IPV4_PATTERN = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_text(value: object) -> str:
    text = str(value)
    text = URI_CREDENTIAL_PATTERN.sub(r"\g<prefix>[REDACTED]\g<suffix>", text)
    text = EVENT_HUBS_ENDPOINT_PATTERN.sub("Endpoint=[REDACTED]", text)
    text = SENSITIVE_VALUE_PATTERN.sub(r"\1\2\3[REDACTED]\5", text)
    text = SUBSCRIPTION_PATTERN.sub(r"\1[REDACTED]", text)

    def replace_ip(match: re.Match[str]) -> str:
        candidate = match.group(0)
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            return candidate
        return "[REDACTED_PUBLIC_IP]" if address.is_global else candidate

    return IPV4_PATTERN.sub(replace_ip, text)


def ensure_parent(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def write_json(path: str | Path, payload: Any) -> None:
    resolved = ensure_parent(path)
    resolved.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def add_kafka_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092"),
    )
    parser.add_argument(
        "--security-protocol",
        choices=("PLAINTEXT", "SASL_SSL"),
        default=os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
    )
    parser.add_argument(
        "--sasl-mechanism",
        default=os.getenv("KAFKA_SASL_MECHANISM", "PLAIN"),
    )


def kafka_client_config(args: argparse.Namespace) -> dict[str, Any]:
    config: dict[str, Any] = {
        "bootstrap_servers": args.bootstrap_servers,
        "security_protocol": args.security_protocol,
    }
    if args.security_protocol == "SASL_SSL":
        username = os.getenv("KAFKA_SASL_USERNAME", "$ConnectionString")
        password = os.getenv("KAFKA_SASL_PASSWORD")
        if not password:
            raise ValueError("KAFKA_SASL_PASSWORD is required for SASL_SSL")
        config.update(
            {
                "sasl_mechanism": args.sasl_mechanism,
                "sasl_plain_username": username,
                "sasl_plain_password": password,
            }
        )
    return config


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())
