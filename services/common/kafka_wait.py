import time
from kafka import KafkaProducer

from services.common.kafka_config import kafka_security_config


def wait_for_kafka(bootstrap_servers: str, timeout_seconds: int = 90) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        try:
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                **kafka_security_config(),
            )
            producer.close()
            return
        except Exception as exc:  # pragma: no cover - startup retry helper
            last_error = exc
            time.sleep(2)

    raise RuntimeError(f"Kafka did not become ready in time: {last_error}")


def kafka_ready(bootstrap_servers: str) -> bool:
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            **kafka_security_config(),
        )
        producer.close()
        return True
    except Exception:
        return False
