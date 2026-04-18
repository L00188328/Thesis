import os
import random
import time
from kafka import KafkaProducer

from services.common.event_schema import ShipmentEvent
from services.common.kafka_wait import wait_for_kafka

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "shipment-events")
INTERVAL_SECONDS = float(os.getenv("PRODUCER_INTERVAL_SECONDS", "3.5"))

SHIPMENT_IDS = [f"SHP-{i:04d}" for i in range(1, 31)]
CITIES = ["Vienna", "Linz", "Graz", "Salzburg", "Innsbruck"]
EVENT_TYPES = [
    "OutForDelivery",
    "DeliveryAttempted",
    "Delivered",
]


def main() -> None:
    wait_for_kafka(BOOTSTRAP)
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda value: value.encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8"),
    )

    print("delivery-tour producer started")
    while True:
        shipment_id = random.choice(SHIPMENT_IDS)
        event_type = random.choice(EVENT_TYPES)
        location = random.choice(CITIES)

        details = {"driverId": f"DRV-{random.randint(1, 50):03d}"}
        if event_type == "DeliveryAttempted":
            details["reason"] = random.choice(["RecipientUnavailable", "AddressIssue"])

        event = ShipmentEvent.create(
            shipment_id=shipment_id,
            domain="DeliveryTour",
            event_type=event_type,
            location=location,
            details=details,
        )

        producer.send(TOPIC, key=shipment_id, value=event.to_json())
        producer.flush()
        print(f"published: {event.event_type} for {event.shipment_id}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
