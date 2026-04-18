import json
import os
import time
from typing import Dict

from kafka import KafkaConsumer
import psycopg

from services.common.event_schema import ShipmentEvent
from services.common.kafka_wait import wait_for_kafka

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "shipment-events")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "shipment-aggregator")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@postgres:5432/shipments",
)


def wait_for_db(timeout_seconds: int = 90) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                conn.execute("SELECT 1")
            return
        except Exception as exc:  # pragma: no cover - startup retry helper
            last_error = exc
            time.sleep(2)

    raise RuntimeError(f"Database did not become ready in time: {last_error}")


def project_event(cur: psycopg.Cursor, event: ShipmentEvent) -> None:
    cur.execute(
        """
        INSERT INTO shipment_events (
            event_id, shipment_id, domain, event_type, occurred_at, location, details
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (event_id) DO NOTHING
        """,
        (
            event.event_id,
            event.shipment_id,
            event.domain,
            event.event_type,
            event.occurred_at,
            event.location,
            json.dumps(event.details),
        ),
    )

    cur.execute(
        """
        INSERT INTO shipment_projection (
            shipment_id,
            latest_event_type,
            latest_event_domain,
            latest_event_time,
            latest_location,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (shipment_id) DO UPDATE
        SET
            latest_event_type = EXCLUDED.latest_event_type,
            latest_event_domain = EXCLUDED.latest_event_domain,
            latest_event_time = EXCLUDED.latest_event_time,
            latest_location = EXCLUDED.latest_location,
            updated_at = NOW()
        """,
        (
            event.shipment_id,
            event.event_type,
            event.domain,
            event.occurred_at,
            event.location,
        ),
    )


def main() -> None:
    wait_for_kafka(BOOTSTRAP)
    wait_for_db()

    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda value: value.decode("utf-8"),
        key_deserializer=lambda value: value.decode("utf-8") if value else None,
    )

    print("aggregator started")
    with psycopg.connect(DATABASE_URL) as conn:
        for msg in consumer:
            event = ShipmentEvent.from_json(msg.value)
            with conn.cursor() as cur:
                project_event(cur, event)
            conn.commit()
            print(
                f"projected event {event.event_id} for {event.shipment_id} ({event.event_type})"
            )


if __name__ == "__main__":
    main()
