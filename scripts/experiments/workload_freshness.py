import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from scripts.experiments.common import ensure_parent, sanitize_text, utc_now_iso


FIELDS = (
    "sample_timestamp_utc",
    "shipment_id",
    "latest_event_version",
    "previous_event_version",
    "version_advanced",
    "remaining_versions",
    "latest_event_time",
    "freshness_seconds",
    "http_status",
    "instance_id",
    "region",
    "success",
    "error_category",
    "error_detail",
)


def build_payload(shipment_a: str, shipment_b: str) -> bytes:
    query = """
    query WorkloadFreshness($shipmentA: String!, $shipmentB: String!) {
      shipmentA: shipment(shipmentId: $shipmentA) {
        shipmentId
        latestEventVersion
        latestEventTime
      }
      shipmentB: shipment(shipmentId: $shipmentB) {
        shipmentId
        latestEventVersion
        latestEventTime
      }
    }
    """
    return json.dumps(
        {
            "query": query,
            "variables": {"shipmentA": shipment_a, "shipmentB": shipment_b},
        }
    ).encode("utf-8")


def freshness_seconds(latest_event_time: str, sampled_at: datetime) -> float:
    event_time = datetime.fromisoformat(latest_event_time.replace("Z", "+00:00"))
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    return round(max(0.0, (sampled_at - event_time).total_seconds()), 3)


def response_rows(
    status: int,
    body: bytes,
    shipment_ids: tuple[str, str],
    previous_versions: dict[str, int],
    expected_final_version: int,
    instance_id: str,
    region: str,
) -> list[dict[str, Any]]:
    sampled_at = datetime.now(timezone.utc)
    sampled_timestamp = sampled_at.isoformat()
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"invalid_json: {sanitize_text(exc)}") from exc
    if status != 200:
        raise ValueError(f"http_status: {status}")
    if payload.get("errors"):
        raise ValueError(f"graphql_errors: {sanitize_text(json.dumps(payload['errors']))}")

    data = payload.get("data") or {}
    rows: list[dict[str, Any]] = []
    for alias, expected_id in zip(("shipmentA", "shipmentB"), shipment_ids):
        shipment = data.get(alias)
        if not shipment or shipment.get("shipmentId") != expected_id:
            raise ValueError(f"shipment_mismatch: {expected_id}")
        version = int(shipment["latestEventVersion"])
        previous = previous_versions.get(expected_id)
        latest_time = str(shipment["latestEventTime"])
        rows.append(
            {
                "sample_timestamp_utc": sampled_timestamp,
                "shipment_id": expected_id,
                "latest_event_version": version,
                "previous_event_version": "" if previous is None else previous,
                "version_advanced": "" if previous is None else str(version > previous).lower(),
                "remaining_versions": max(0, expected_final_version - version),
                "latest_event_time": latest_time,
                "freshness_seconds": freshness_seconds(latest_time, sampled_at),
                "http_status": status,
                "instance_id": instance_id,
                "region": region,
                "success": "true",
                "error_category": "",
                "error_detail": "",
            }
        )
        previous_versions[expected_id] = version
    return rows


def error_rows(
    shipment_ids: tuple[str, str],
    status: int,
    category: str,
    detail: object,
) -> list[dict[str, Any]]:
    timestamp = utc_now_iso()
    return [
        {
            "sample_timestamp_utc": timestamp,
            "shipment_id": shipment_id,
            "latest_event_version": "",
            "previous_event_version": "",
            "version_advanced": "",
            "remaining_versions": "",
            "latest_event_time": "",
            "freshness_seconds": "",
            "http_status": status,
            "instance_id": "",
            "region": "",
            "success": "false",
            "error_category": category,
            "error_detail": sanitize_text(detail),
        }
        for shipment_id in shipment_ids
    ]


def sample(
    endpoint: str,
    request_payload: bytes,
    shipment_ids: tuple[str, str],
    previous_versions: dict[str, int],
    expected_final_version: int,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        endpoint,
        data=request_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            return response_rows(
                response.status,
                body,
                shipment_ids,
                previous_versions,
                expected_final_version,
                response.headers.get("X-Instance-ID", ""),
                response.headers.get("X-Region", ""),
            )
    except urllib.error.HTTPError as exc:
        return error_rows(shipment_ids, exc.code, "http_status", exc)
    except urllib.error.URLError as exc:
        category = "timeout" if isinstance(exc.reason, TimeoutError) else "connection"
        return error_rows(shipment_ids, 0, category, exc.reason)
    except (TimeoutError, ValueError, KeyError, TypeError) as exc:
        category = str(exc).split(":", 1)[0] if isinstance(exc, ValueError) else "response"
        return error_rows(shipment_ids, 0, category, exc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record controlled-shipment GraphQL progress")
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--shipment-a", required=True)
    parser.add_argument("--shipment-b", required=True)
    parser.add_argument("--expected-final-version", type=int, default=300)
    parser.add_argument("--duration-seconds", type=float, default=600)
    parser.add_argument("--interval-seconds", type=float, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=5)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.shipment_a == args.shipment_b:
        raise ValueError("controlled shipment IDs must be unique")
    output = ensure_parent(args.output)
    shipment_ids = (args.shipment_a, args.shipment_b)
    payload = build_payload(*shipment_ids)
    previous_versions: dict[str, int] = {}
    started = time.monotonic()
    sequence = 0
    with output.open("w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDS)
        writer.writeheader()
        while started + sequence * args.interval_seconds < started + args.duration_seconds:
            scheduled = started + sequence * args.interval_seconds
            delay = scheduled - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            writer.writerows(
                sample(
                    args.endpoint,
                    payload,
                    shipment_ids,
                    previous_versions,
                    args.expected_final_version,
                    args.timeout_seconds,
                )
            )
            output_file.flush()
            sequence += 1


if __name__ == "__main__":
    main()
