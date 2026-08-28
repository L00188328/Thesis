import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any

from kafka import KafkaAdminClient, KafkaConsumer, TopicPartition
from kafka.coordinator.protocol import ConsumerProtocolMemberAssignment

from scripts.experiments.common import (
    add_kafka_arguments,
    ensure_parent,
    kafka_client_config,
    sanitize_text,
    utc_now_iso,
)


PROGRESS_FIELDS = (
    "sample_timestamp_utc",
    "group_id",
    "topic",
    "partition",
    "committed_offset",
    "end_offset",
    "lag",
    "total_lag",
    "assignment_source",
    "collector_error",
)


def discover_partitions(consumer: KafkaConsumer, topics: list[str]) -> list[TopicPartition]:
    partitions: list[TopicPartition] = []
    for topic in topics:
        topic_partitions = consumer.partitions_for_topic(topic)
        if not topic_partitions:
            raise RuntimeError(f"topic has no partitions or is unavailable: {topic}")
        partitions.extend(
            TopicPartition(topic, partition) for partition in sorted(topic_partitions)
        )
    return partitions


def decode_assignment(member: Any) -> list[dict[str, Any]]:
    raw_assignment = getattr(member, "member_assignment", b"")
    if not raw_assignment:
        return []
    decoded = (
        raw_assignment
        if isinstance(raw_assignment, ConsumerProtocolMemberAssignment)
        else ConsumerProtocolMemberAssignment.decode(raw_assignment)
    )
    assignments: list[dict[str, Any]] = []
    for topic, partitions in decoded.assignment:
        assignments.extend(
            {"topic": topic, "partition": int(partition)} for partition in partitions
        )
    return assignments


def describe_assignments(admin: KafkaAdminClient, group_id: str) -> list[dict[str, Any]]:
    descriptions = admin.describe_consumer_groups([group_id])
    snapshots: list[dict[str, Any]] = []
    for description in descriptions:
        for member in getattr(description, "members", []):
            snapshots.append(
                {
                    "sample_timestamp_utc": utc_now_iso(),
                    "group_id": group_id,
                    "member_id": getattr(member, "member_id", ""),
                    "client_id": getattr(member, "client_id", ""),
                    "host": getattr(member, "client_host", ""),
                    "instance_id": getattr(member, "group_instance_id", None),
                    "region": None,
                    "assignments": decode_assignment(member),
                    "source": "kafka_admin",
                }
            )
    return snapshots


def sample_offsets(
    consumer: KafkaConsumer,
    partitions: list[TopicPartition],
    group_id: str,
    assignment_source: str,
) -> list[dict[str, Any]]:
    timestamp = utc_now_iso()
    end_offsets = consumer.end_offsets(partitions)
    rows: list[dict[str, Any]] = []
    total_lag = 0
    all_lag_known = True
    for partition in partitions:
        error = ""
        committed = consumer.committed(partition)
        end_offset = end_offsets.get(partition)
        lag: int | None = None
        if committed is None:
            error = "no_committed_offset"
            all_lag_known = False
        elif end_offset is None:
            error = "no_end_offset"
            all_lag_known = False
        else:
            lag = max(0, int(end_offset) - int(committed))
            total_lag += lag
        rows.append(
            {
                "sample_timestamp_utc": timestamp,
                "group_id": group_id,
                "topic": partition.topic,
                "partition": partition.partition,
                "committed_offset": committed,
                "end_offset": end_offset,
                "lag": lag,
                "total_lag": "",
                "assignment_source": assignment_source,
                "collector_error": error,
            }
        )
    rows.append(
        {
            "sample_timestamp_utc": timestamp,
            "group_id": group_id,
            "topic": "__TOTAL__",
            "partition": -1,
            "committed_offset": "",
            "end_offset": "",
            "lag": "",
            "total_lag": total_lag if all_lag_known else "",
            "assignment_source": assignment_source,
            "collector_error": "" if all_lag_known else "partial_lag",
        }
    )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect read-only Kafka group progress")
    add_kafka_arguments(parser)
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--topic", action="append", required=True)
    parser.add_argument("--interval-seconds", type=float, default=5)
    parser.add_argument("--duration-seconds", type=float, default=600)
    parser.add_argument("--progress-output", required=True)
    parser.add_argument("--assignment-output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client_config = kafka_client_config(args)
    consumer = KafkaConsumer(
        group_id=args.group_id,
        enable_auto_commit=False,
        request_timeout_ms=30000,
        **client_config,
    )
    admin = KafkaAdminClient(**client_config)
    progress_output = ensure_parent(args.progress_output)
    assignment_output = ensure_parent(args.assignment_output)
    partitions = discover_partitions(consumer, args.topic)
    started = time.monotonic()
    sequence = 0
    try:
        with progress_output.open("w", newline="") as progress_file, assignment_output.open(
            "w"
        ) as assignment_file:
            writer = csv.DictWriter(progress_file, fieldnames=PROGRESS_FIELDS)
            writer.writeheader()
            while started + sequence * args.interval_seconds < started + args.duration_seconds:
                scheduled = started + sequence * args.interval_seconds
                delay = scheduled - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                assignment_source = "unavailable"
                try:
                    assignments = describe_assignments(admin, args.group_id)
                    if assignments:
                        assignment_source = "kafka_admin"
                        for assignment in assignments:
                            assignment_file.write(json.dumps(assignment, sort_keys=True) + "\n")
                        assignment_file.flush()
                except Exception as exc:
                    assignment_file.write(
                        json.dumps(
                            {
                                "sample_timestamp_utc": utc_now_iso(),
                                "group_id": args.group_id,
                                "source": "unavailable",
                                "error": sanitize_text(exc),
                            },
                            sort_keys=True,
                        )
                        + "\n"
                    )
                    assignment_file.flush()
                for row in sample_offsets(
                    consumer, partitions, args.group_id, assignment_source
                ):
                    writer.writerow(row)
                progress_file.flush()
                sequence += 1
    finally:
        admin.close()
        consumer.close()


if __name__ == "__main__":
    main()
