import os
from typing import Any


def kafka_security_config() -> dict[str, Any]:
    security_protocol = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
    config: dict[str, Any] = {"security_protocol": security_protocol}
    if security_protocol == "SASL_SSL":
        password = os.getenv("KAFKA_SASL_PASSWORD")
        if not password:
            raise RuntimeError("KAFKA_SASL_PASSWORD is required for SASL_SSL")
        config.update(
            {
                "sasl_mechanism": os.getenv("KAFKA_SASL_MECHANISM", "PLAIN"),
                "sasl_plain_username": os.getenv(
                    "KAFKA_SASL_USERNAME", "$ConnectionString"
                ),
                "sasl_plain_password": password,
            }
        )
    return config
