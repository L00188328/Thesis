import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median

from scripts.experiments.common import write_json


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentile_value * len(ordered)) - 1)
    return round(ordered[index], 2)


def longest_failure_sequence(rows: list[dict[str, str]]) -> int:
    longest = 0
    current = 0
    for row in rows:
        if row["success"] == "true":
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize availability probe CSV")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with Path(args.input).open(newline="") as input_file:
        rows = list(csv.DictReader(input_file))
    successes = [row for row in rows if row["success"] == "true"]
    failures = [row for row in rows if row["success"] != "true"]
    latencies = [float(row["latency_ms"]) for row in successes]
    payload = {
        "total_probes": len(rows),
        "successful_probes": len(successes),
        "failed_probes": len(failures),
        "availability_percent": round(100 * len(successes) / len(rows), 5) if rows else None,
        "longest_consecutive_failure_sequence": longest_failure_sequence(rows),
        "failure_timestamps_utc": [row["started_timestamp_utc"] for row in failures],
        "latency_ms": {
            "p50": round(median(latencies), 2) if latencies else None,
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
            "max": round(max(latencies), 2) if latencies else None,
        },
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
