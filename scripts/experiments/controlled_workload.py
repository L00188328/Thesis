import argparse
import csv
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from kafka import KafkaProducer

from scripts.experiments.common import (
    add_kafka_arguments,
    ensure_parent,
    kafka_client_config,
    load_json,
    utc_now_iso,
)


PUBLISHED_FIELDS = (
    "sequence",
    "event_id",
    "shipment_id",
    "event_version",
    "domain",
    "event_type",
    "topic",
    "partition",
    "offset",
    "scheduled_timestamp_utc",
    "acknowledged_timestamp_utc",
)


def event_for_sequence(
    run_id: str,
    sequence: int,
    shipment_a: str,
    shipment_b: str,
    logistic_topic: str,
    delivery_topic: str,
    occurred_at: str,
) -> tuple[str, dict[str, Any]]:
    cycle_position = (sequence - 1) % 4
    shipment_id = shipment_a if cycle_position in (0, 2) else shipment_b
    event_version = ((sequence - 1) // 4) * 2 + (1 if cycle_position in (0, 1) else 2)
    if cycle_position in (0, 1):
        topic = logistic_topic
        domain = "LogisticCenter"
        event_type = "ParcelReceivedAtHub"
        location = "Azure Controlled Hub"
    else:
        topic = delivery_topic
        domain = "DeliveryBase"
        event_type = "OutForDelivery"
        location = "Azure Controlled Delivery Base"
    event = {
        "event_id": f"az-{run_id}-evt-{sequence:04d}",
        "shipment_id": shipment_id,
        "event_version": event_version,
        "domain": domain,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "location": location,
        "details": {
            "runId": run_id,
            "sequence": sequence,
            "controlledWorkload": True,
        },
    }
    return topic, event


def build_events(args: argparse.Namespace) -> list[tuple[str, dict[str, Any]]]:
    start = datetime.now(timezone.utc)
    return [
        event_for_sequence(
            args.run_id,
            sequence,
            args.shipment_a,
            args.shipment_b,
            args.logistic_topic,
            args.delivery_topic,
            (start + timedelta(seconds=(sequence - 1) * args.interval_seconds)).isoformat(),
        )
        for sequence in range(1, args.event_count + 1)
    ]


def expected_partitions(mapping_path: str | None, run_id: str) -> dict[str, int]:
    if not mapping_path:
        return {}
    payload = load_json(mapping_path)
    entries = payload.get("entries", payload) if isinstance(payload, dict) else payload
    return {
        entry["shipment_id"]: int(entry["expected_partition"])
        for entry in entries
        if entry["run_id"] == run_id
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish the frozen controlled workload")
    add_kafka_arguments(parser)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--shipment-a", required=True)
    parser.add_argument("--shipment-b", required=True)
    parser.add_argument("--logistic-topic", required=True)
    parser.add_argument("--delivery-topic", required=True)
    parser.add_argument("--event-count", type=int, default=600)
    parser.add_argument("--interval-seconds", type=float, default=1)
    parser.add_argument("--expected-events", required=True)
    parser.add_argument("--published-events", required=True)
    parser.add_argument("--partition-key-map")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.event_count % 4 != 0:
        raise ValueError("event-count must be divisible by four")
    events = build_events(args)
    expected_output = ensure_parent(args.expected_events)
    with expected_output.open("w") as expected_file:
        for topic, event in events:
            expected_file.write(json.dumps({"topic": topic, **event}, sort_keys=True) + "\n")

    partition_expectations = expected_partitions(args.partition_key_map, args.run_id)
    producer = KafkaProducer(
        **kafka_client_config(args),
        key_serializer=lambda value: value.encode("utf-8"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        acks="all",
    )
    published_output = ensure_parent(args.published_events)
    started = time.monotonic()
    try:
        with published_output.open("w", newline="") as published_file:
            writer = csv.DictWriter(published_file, fieldnames=PUBLISHED_FIELDS)
            writer.writeheader()
            for index, (topic, event) in enumerate(events):
                scheduled = started + index * args.interval_seconds
                delay = scheduled - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                metadata = producer.send(
                    topic,
                    key=event["shipment_id"],
                    value=event,
                ).get(timeout=30)
                expected_partition = partition_expectations.get(event["shipment_id"])
                if expected_partition is not None and metadata.partition != expected_partition:
                    raise RuntimeError(
                        f"partition mismatch for {event['shipment_id']}: "
                        f"expected {expected_partition}, observed {metadata.partition}"
                    )
                writer.writerow(
                    {
                        "sequence": index + 1,
                        "event_id": event["event_id"],
                        "shipment_id": event["shipment_id"],
                        "event_version": event["event_version"],
                        "domain": event["domain"],
                        "event_type": event["event_type"],
                        "topic": topic,
                        "partition": metadata.partition,
                        "offset": metadata.offset,
                        "scheduled_timestamp_utc": event["occurred_at"],
                        "acknowledged_timestamp_utc": utc_now_iso(),
                    }
                )
                published_file.flush()
    finally:
        producer.flush(timeout=30)
        producer.close(timeout=30)


if __name__ == "__main__":
    main()
