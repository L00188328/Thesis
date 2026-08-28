import argparse
import json
from pathlib import Path
from typing import Any

from kafka import KafkaProducer
from kafka.partitioner.default import murmur2

from scripts.experiments.common import (
    add_kafka_arguments,
    kafka_client_config,
    utc_now_iso,
    write_json,
)


def key_partition(shipment_id: str, partition_count: int) -> int:
    key = shipment_id.encode("utf-8")
    return (murmur2(key) & 0x7FFFFFFF) % partition_count


def select_pair(run_id: str, partition_count: int) -> tuple[str, str]:
    selected: dict[int, str] = {}
    candidate = 1
    while len(selected) < 2:
        shipment_id = f"AZ-{run_id.upper()}-KEY-{candidate:04d}"
        partition = key_partition(shipment_id, partition_count)
        selected.setdefault(partition, shipment_id)
        candidate += 1
    return selected[0], selected[1]


def verify_entries(
    entries: list[dict[str, Any]],
    verification_topic: str,
    producer: KafkaProducer,
) -> None:
    for entry in entries:
        payload = {
            "record_type": "partition_mapping_verification",
            "run_id": entry["run_id"],
            "shipment_id": entry["shipment_id"],
            "expected_partition": entry["expected_partition"],
            "timestamp_utc": utc_now_iso(),
        }
        metadata = producer.send(
            verification_topic,
            key=entry["shipment_id"],
            value=payload,
        ).get(timeout=30)
        entry.update(
            {
                "verification_topic": verification_topic,
                "observed_partition": metadata.partition,
                "acknowledged_offset": metadata.offset,
                "acknowledged_timestamp_utc": utc_now_iso(),
                "verified": metadata.partition == entry["expected_partition"],
            }
        )
        if not entry["verified"]:
            raise RuntimeError(
                f"partition verification failed for {entry['shipment_id']}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the frozen partition-key map")
    add_kafka_arguments(parser)
    parser.add_argument("--run-id", action="append", required=True)
    parser.add_argument("--partition-count", type=int, default=2)
    parser.add_argument("--verification-topic")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.partition_count != 2:
        raise ValueError("methodology v1.0 requires exactly two partitions")
    entries: list[dict[str, Any]] = []
    for run_id in args.run_id:
        shipment_a, shipment_b = select_pair(run_id, args.partition_count)
        entries.extend(
            [
                {
                    "run_id": run_id,
                    "shipment_id": shipment_a,
                    "key_role": "A",
                    "expected_partition": 0,
                    "observed_partition": None,
                    "verified": False,
                },
                {
                    "run_id": run_id,
                    "shipment_id": shipment_b,
                    "key_role": "B",
                    "expected_partition": 1,
                    "observed_partition": None,
                    "verified": False,
                },
            ]
        )

    if args.verification_topic:
        producer = KafkaProducer(
            **kafka_client_config(args),
            key_serializer=lambda value: value.encode("utf-8"),
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            acks="all",
        )
        try:
            verify_entries(entries, args.verification_topic, producer)
        finally:
            producer.flush(timeout=30)
            producer.close(timeout=30)

    payload = {
        "schema_version": 1,
        "generated_timestamp_utc": utc_now_iso(),
        "partition_count": args.partition_count,
        "partitioner": "kafka-python-ng murmur2",
        "broker_verified": bool(args.verification_topic),
        "entries": entries,
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
