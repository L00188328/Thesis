import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from typing import Any

from scripts.experiments.common import ensure_parent, sanitize_text, utc_now_iso


FIELDS = (
    "sequence",
    "scheduled_timestamp_utc",
    "started_timestamp_utc",
    "finished_timestamp_utc",
    "latency_ms",
    "http_status",
    "instance_id",
    "region",
    "success",
    "error_category",
    "error_detail",
)


def build_payload(shipment_id: str) -> bytes:
    query = """
    query AvailabilityProbe($shipmentId: String!) {
      shipment(shipmentId: $shipmentId) {
        shipmentId
        latestEventVersion
      }
    }
    """
    return json.dumps(
        {"query": query, "variables": {"shipmentId": shipment_id}}
    ).encode("utf-8")


def classify_response(
    status: int,
    body: bytes,
    shipment_id: str,
    expected_version: int,
) -> tuple[bool, str, str]:
    if status != 200:
        return False, "http_status", str(status)
    try:
        payload: dict[str, Any] = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return False, "invalid_json", str(exc)
    if payload.get("errors"):
        return False, "graphql_errors", json.dumps(payload["errors"])
    shipment = (payload.get("data") or {}).get("shipment")
    if not shipment:
        return False, "null_shipment", "shipment was null"
    if shipment.get("shipmentId") != shipment_id:
        return False, "shipment_mismatch", str(shipment.get("shipmentId"))
    if shipment.get("latestEventVersion") != expected_version:
        return False, "version_mismatch", str(shipment.get("latestEventVersion"))
    return True, "", ""


def execute_probe(
    endpoint: str,
    payload: bytes,
    shipment_id: str,
    expected_version: int,
    timeout_seconds: float,
) -> dict[str, Any]:
    started_wall = utc_now_iso()
    started = time.perf_counter()
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    status = 0
    instance_id = ""
    region = ""
    success = False
    error_category = ""
    error_detail = ""
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = response.status
            body = response.read()
            instance_id = response.headers.get("X-Instance-ID", "")
            region = response.headers.get("X-Region", "")
        success, error_category, error_detail = classify_response(
            status, body, shipment_id, expected_version
        )
    except urllib.error.HTTPError as exc:
        status = exc.code
        error_category = "http_status"
        error_detail = sanitize_text(exc)
    except urllib.error.URLError as exc:
        reason = exc.reason
        error_category = "timeout" if isinstance(reason, TimeoutError) else "connection"
        error_detail = sanitize_text(reason)
    except TimeoutError as exc:
        error_category = "timeout"
        error_detail = sanitize_text(exc)
    finished = time.perf_counter()
    return {
        "started_timestamp_utc": started_wall,
        "finished_timestamp_utc": utc_now_iso(),
        "latency_ms": round((finished - started) * 1000, 2),
        "http_status": status,
        "instance_id": instance_id,
        "region": region,
        "success": str(success).lower(),
        "error_category": error_category,
        "error_detail": error_detail,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record fixed-interval GraphQL probes")
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--shipment-id", required=True)
    parser.add_argument("--expected-version", type=int, required=True)
    parser.add_argument("--duration-seconds", type=float, default=600)
    parser.add_argument("--interval-seconds", type=float, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=5)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = ensure_parent(args.output)
    payload = build_payload(args.shipment_id)
    started = time.monotonic()
    end_at = started + args.duration_seconds
    sequence = 0
    with output.open("w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDS)
        writer.writeheader()
        while started + sequence * args.interval_seconds < end_at:
            scheduled = started + sequence * args.interval_seconds
            delay = scheduled - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            row = execute_probe(
                args.endpoint,
                payload,
                args.shipment_id,
                args.expected_version,
                args.timeout_seconds,
            )
            row["sequence"] = sequence + 1
            row["scheduled_timestamp_utc"] = utc_now_iso()
            writer.writerow(row)
            output_file.flush()
            sequence += 1


if __name__ == "__main__":
    main()
