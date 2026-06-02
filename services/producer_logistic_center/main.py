import os
import random
import time

from kafka import KafkaProducer
import psycopg

from services.common.db_wait import get_database_url, wait_for_db
from services.common.event_schema import ShipmentEvent
from services.common.kafka_wait import wait_for_kafka
from services.common.simulation_state import (
    claim_next_for_logistics,
    init_state_table,
    recycle_delivered,
    seed_shipments,
    update_state,
)

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "logistic-center-events")
INTERVAL_SECONDS = float(os.getenv("PRODUCER_INTERVAL_SECONDS", "2.0"))
DATABASE_URL = get_database_url()

SHIPMENT_IDS = [f"SHP-{i:04d}" for i in range(1, 31)]
CITY_TO_HUB = {
    "Dublin": "Dublin Hub",
    "Cork": "Cork Hub",
    "Galway": "Galway Hub",
    "Athlone": "Athlone Hub",
}
WORKER_SHIFTS = ["A", "B", "C"]


def build_logistics_event(state: dict) -> tuple[ShipmentEvent, int, str, str, int]:
    shipment_id = state["shipment_id"]
    stage = int(state["stage"])
    destination_city = state.get("destination_city")
    hub = state.get("hub")

    if stage == 0:
        destination_city = random.choice(list(CITY_TO_HUB.keys()))
        hub = CITY_TO_HUB[destination_city]
        event_type = "ParcelReceivedAtHub"
        next_stage = 1
    elif stage == 1:
        event_type = "ParcelSorted"
        next_stage = 2
    else:
        event_type = "ParcelLoadedForTransit"
        next_stage = 3

    event = ShipmentEvent.create(
        shipment_id=shipment_id,
        domain="LogisticCenter",
        event_type=event_type,
        location=hub,
        details={
            "workerShift": random.choice(WORKER_SHIFTS),
            "destinationCity": destination_city,
        },
    )

    return event, next_stage, destination_city, hub, 0


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

        print("logistic-center producer started (stateful)")
        while True:
            recycle_delivered(conn)
            state = claim_next_for_logistics(conn)
            if not state:
                time.sleep(INTERVAL_SECONDS)
                continue

            event, next_stage, destination_city, hub, attempts = build_logistics_event(state)
            producer.send(TOPIC, key=event.shipment_id, value=event.to_json())
            producer.flush()

            update_state(
                conn=conn,
                shipment_id=event.shipment_id,
                stage=next_stage,
                destination_city=destination_city,
                hub=hub,
                attempts=attempts,
            )

            print(f"published: {event.event_type} for {event.shipment_id}")
            time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
