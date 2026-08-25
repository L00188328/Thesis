import json
import os
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread

from kafka import KafkaConsumer
import psycopg

from services.common.db_wait import database_ready
from services.common.event_schema import ShipmentEvent
from services.common.kafka_wait import kafka_ready, wait_for_kafka
from services.common.logging_utils import configure_logging, get_instance_id, utc_now_iso
from services.common.schema_init import ensure_projection_schema

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
TOPICS = [
    topic.strip()
    for topic in os.getenv(
        "KAFKA_TOPICS", "logistic-center-events,delivery-base-events"
    ).split(",")
    if topic.strip()
]
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "shipment-aggregator")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@postgres:5432/shipments",
)
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8081"))
SERVICE_NAME = "aggregator"
INSTANCE_ID = get_instance_id(SERVICE_NAME)
logger = configure_logging(SERVICE_NAME)


class ReadinessState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._consumer_started = False
        self._last_error: str | None = None

    def mark_consumer_started(self) -> None:
        with self._lock:
            self._consumer_started = True
            self._last_error = None

    def mark_success(self) -> None:
        with self._lock:
            self._last_error = None

    def mark_error(self, message: str) -> None:
        with self._lock:
            self._last_error = message

    def snapshot(self) -> tuple[bool, str | None]:
        with self._lock:
            return self._consumer_started, self._last_error


readiness_state = ReadinessState()


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
        INSERT INTO all_shipment_events (
            event_id, shipment_id, event_version, domain, event_type, occurred_at, location, details
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (event_id) DO NOTHING
        """,
        (
            event.event_id,
            event.shipment_id,
            event.event_version,
            event.domain,
            event.event_type,
            event.occurred_at,
            event.location,
            json.dumps(event.details),
        ),
    )

    cur.execute(
        """
        INSERT INTO current_shipment_state (
            shipment_id,
            latest_event_version,
            latest_event_type,
            latest_event_domain,
            latest_event_time,
            latest_location,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (shipment_id) DO UPDATE
        SET
            latest_event_version = EXCLUDED.latest_event_version,
            latest_event_type = EXCLUDED.latest_event_type,
            latest_event_domain = EXCLUDED.latest_event_domain,
            latest_event_time = EXCLUDED.latest_event_time,
            latest_location = EXCLUDED.latest_location,
            updated_at = NOW()
        WHERE
            EXCLUDED.latest_event_version > current_shipment_state.latest_event_version
            OR (
                EXCLUDED.latest_event_version = current_shipment_state.latest_event_version
                AND EXCLUDED.latest_event_time >= current_shipment_state.latest_event_time
            )
        """,
        (
            event.shipment_id,
            event.event_version,
            event.event_type,
            event.domain,
            event.occurred_at,
            event.location,
        ),
    )


def build_status_payload(ready: bool) -> bytes:
    return json.dumps(
        {
            "status": "ok" if ready else "not_ready",
            "service": SERVICE_NAME,
            "instanceId": INSTANCE_ID,
            "timestamp": utc_now_iso(),
        }
    ).encode("utf-8")


def is_ready() -> bool:
    consumer_started, last_error = readiness_state.snapshot()
    return (
        consumer_started
        and last_error is None
        and database_ready(DATABASE_URL, "SELECT 1 FROM all_shipment_events LIMIT 1")
        and kafka_ready(BOOTSTRAP)
    )


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            payload = build_status_payload(True)
            self.send_response(HTTPStatus.OK)
        elif self.path == "/ready":
            ready = is_ready()
            payload = build_status_payload(ready)
            self.send_response(HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE)
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            payload = b'{"status":"not_found"}'

        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def start_health_server() -> None:
    server = ThreadingHTTPServer(("", HEALTH_PORT), HealthHandler)
    server.serve_forever()


def main() -> None:
    Thread(target=start_health_server, daemon=True).start()
    wait_for_kafka(BOOTSTRAP)
    wait_for_db()
    ensure_projection_schema(DATABASE_URL)

    consumer = KafkaConsumer(
        *TOPICS,
        bootstrap_servers=BOOTSTRAP,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: value.decode("utf-8"),
        key_deserializer=lambda value: value.decode("utf-8") if value else None,
    )
    readiness_state.mark_consumer_started()

    logger.info("aggregator_started")
    with psycopg.connect(DATABASE_URL) as conn:
        for msg in consumer:
            try:
                event = ShipmentEvent.from_json(msg.value)
                with conn.transaction():
                    with conn.cursor() as cur:
                        project_event(cur, event)
                consumer.commit()
                readiness_state.mark_success()
                logger.info(
                    "event_projected",
                    extra={
                        "event_id": event.event_id,
                        "shipment_id": event.shipment_id,
                        "event_type": event.event_type,
                    },
                )
            except Exception as exc:
                readiness_state.mark_error(str(exc))
                logger.exception("aggregation_failed")
                raise


if __name__ == "__main__":
    main()
