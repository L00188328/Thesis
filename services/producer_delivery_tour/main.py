import os
import random
import time

from kafka import KafkaProducer
import psycopg

from services.common.db_wait import get_database_url, wait_for_db
from services.common.event_schema import ShipmentEvent
from services.common.kafka_wait import wait_for_kafka
from services.common.simulation_state import (
    claim_next_for_delivery,
    init_state_table,
    seed_shipments,
    update_state,
)

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "shipment-events")
INTERVAL_SECONDS = float(os.getenv("PRODUCER_INTERVAL_SECONDS", "3.5"))
DATABASE_URL = get_database_url()

SHIPMENT_IDS = [f"SHP-{i:04d}" for i in range(1, 31)]
ATTEMPT_REASONS = ["RecipientUnavailable", "AddressIssue"]


def build_delivery_event(state: dict) -> tuple[ShipmentEvent, int, int]:
    shipment_id = state["shipment_id"]
    stage = int(state["stage"])
    destination_city = state.get("destination_city") or "Unknown"
    attempts = int(state.get("attempts") or 0)

    if stage == 3:
        event_type = "OutForDelivery"
        next_stage = 4
        next_attempts = attempts
        details = {
            "driverId": f"DRV-{random.randint(1, 50):03d}",
            "destinationCity": destination_city,
        }
    else:
        if attempts >= 2 or random.random() < 0.65:
            event_type = "Delivered"
            next_stage = 5
            next_attempts = attempts
            details = {
                "driverId": f"DRV-{random.randint(1, 50):03d}",
                "proofOfDelivery": random.choice(["Signature", "Photo"]),
                "destinationCity": destination_city,
            }
        else:
            event_type = "DeliveryAttempted"
            next_stage = 4
            next_attempts = attempts + 1
            details = {
                "driverId": f"DRV-{random.randint(1, 50):03d}",
                "reason": random.choice(ATTEMPT_REASONS),
                "attemptNumber": next_attempts,
                "destinationCity": destination_city,
            }

    event = ShipmentEvent.create(
        shipment_id=shipment_id,
        domain="DeliveryTour",
        event_type=event_type,
        location=destination_city,
        details=details,
    )
    return event, next_stage, next_attempts


def main() -> None:
    wait_for_kafka(BOOTSTRAP)
    wait_for_db(DATABASE_URL)

    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda value: value.encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8"),
    )

    with psycopg.connect(DATABASE_URL) as conn:
        init_state_table(conn)
        seed_shipments(conn, SHIPMENT_IDS)

        print("delivery-tour producer started (stateful)")
        while True:
            state = claim_next_for_delivery(conn)
            if not state:
                time.sleep(INTERVAL_SECONDS)
                continue

            event, next_stage, next_attempts = build_delivery_event(state)
            producer.send(TOPIC, key=event.shipment_id, value=event.to_json())
            producer.flush()

            update_state(
                conn=conn,
                shipment_id=event.shipment_id,
                stage=next_stage,
                destination_city=state.get("destination_city"),
                hub=state.get("hub"),
                attempts=next_attempts,
            )

            print(f"published: {event.event_type} for {event.shipment_id}")
            time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
