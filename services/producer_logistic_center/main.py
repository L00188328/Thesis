import os
import random
import time
from kafka import KafkaProducer

from services.common.event_schema import ShipmentEvent
from services.common.kafka_wait import wait_for_kafka

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "shipment-events")
INTERVAL_SECONDS = float(os.getenv("PRODUCER_INTERVAL_SECONDS", "2.0"))

SHIPMENT_IDS = [f"SHP-{i:04d}" for i in range(1, 31)]
HUBS = ["Vienna Hub", "Linz Hub", "Graz Hub", "Salzburg Hub"]
EVENT_TYPES = [
    "ParcelReceivedAtHub",
    "ParcelSorted",
    "ParcelLoadedForTransit",
]


def main() -> None:
    wait_for_kafka(BOOTSTRAP)
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda value: value.encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8"),
    )

    print("logistic-center producer started")
    while True:
        shipment_id = random.choice(SHIPMENT_IDS)
        event_type = random.choice(EVENT_TYPES)
        location = random.choice(HUBS)

        event = ShipmentEvent.create(
            shipment_id=shipment_id,
            domain="LogisticCenter",
            event_type=event_type,
            location=location,
            details={"workerShift": random.choice(["A", "B", "C"])},
        )

        producer.send(TOPIC, key=shipment_id, value=event.to_json())
        producer.flush()
        print(f"published: {event.event_type} for {event.shipment_id}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
