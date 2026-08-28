import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from scripts.experiments.common import ensure_parent, write_json


FIELDS = (
    "scope",
    "shipment_id",
    "expected_events",
    "persisted_rows",
    "unique_event_ids",
    "missing_events",
    "duplicate_rows",
    "highest_expected_version",
    "materialised_version",
    "materialised_event_type",
    "materialised_domain",
    "materialised_location",
    "pass",
)


def load_expected(path: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify controlled-run database integrity")
    parser.add_argument("--expected-events", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--missing-output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL must be supplied through the environment or a mounted secret")
    expected = load_expected(args.expected_events)
    expected_ids = {event["event_id"] for event in expected}
    shipment_ids = sorted({event["shipment_id"] for event in expected})
    expected_by_shipment = {
        shipment_id: [event for event in expected if event["shipment_id"] == shipment_id]
        for shipment_id in shipment_ids
    }
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        history = connection.execute(
            """
            SELECT event_id, shipment_id, event_version, event_type, domain, location
            FROM all_shipment_events
            WHERE event_id = ANY(%s)
            """,
            (list(expected_ids),),
        ).fetchall()
        states = connection.execute(
            """
            SELECT shipment_id, latest_event_version, latest_event_type,
                   latest_event_domain, latest_location
            FROM current_shipment_state
            WHERE shipment_id = ANY(%s)
            """,
            (shipment_ids,),
        ).fetchall()

    persisted_ids = {row["event_id"] for row in history}
    missing_ids = sorted(expected_ids - persisted_ids)
    state_by_shipment = {row["shipment_id"]: row for row in states}
    output = ensure_parent(args.output)
    rows: list[dict[str, Any]] = []
    for shipment_id, shipment_expected in expected_by_shipment.items():
        shipment_history = [row for row in history if row["shipment_id"] == shipment_id]
        shipment_event_ids = [row["event_id"] for row in shipment_history]
        expected_versions = [event["event_version"] for event in shipment_expected]
        highest_event = max(shipment_expected, key=lambda event: event["event_version"])
        state = state_by_shipment.get(shipment_id, {})
        duplicate_rows = len(shipment_event_ids) - len(set(shipment_event_ids))
        shipment_missing = len(
            {event["event_id"] for event in shipment_expected} - set(shipment_event_ids)
        )
        correct_state = (
            state.get("latest_event_version") == max(expected_versions)
            and state.get("latest_event_type") == highest_event["event_type"]
            and state.get("latest_event_domain") == highest_event["domain"]
            and state.get("latest_location") == highest_event["location"]
        )
        rows.append(
            {
                "scope": "shipment",
                "shipment_id": shipment_id,
                "expected_events": len(shipment_expected),
                "persisted_rows": len(shipment_history),
                "unique_event_ids": len(set(shipment_event_ids)),
                "missing_events": shipment_missing,
                "duplicate_rows": duplicate_rows,
                "highest_expected_version": max(expected_versions),
                "materialised_version": state.get("latest_event_version", ""),
                "materialised_event_type": state.get("latest_event_type", ""),
                "materialised_domain": state.get("latest_event_domain", ""),
                "materialised_location": state.get("latest_location", ""),
                "pass": str(shipment_missing == 0 and duplicate_rows == 0 and correct_state).lower(),
            }
        )
    rows.append(
        {
            "scope": "run_total",
            "shipment_id": "",
            "expected_events": len(expected),
            "persisted_rows": len(history),
            "unique_event_ids": len(persisted_ids),
            "missing_events": len(missing_ids),
            "duplicate_rows": len(history) - len(persisted_ids),
            "highest_expected_version": "",
            "materialised_version": "",
            "materialised_event_type": "",
            "materialised_domain": "",
            "materialised_location": "",
            "pass": str(not missing_ids and all(row["pass"] == "true" for row in rows)).lower(),
        }
    )
    with output.open("w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    write_json(args.missing_output, {"missing_event_ids": missing_ids})


if __name__ == "__main__":
    main()
