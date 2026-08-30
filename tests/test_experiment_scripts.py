import argparse
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from kafka.coordinator.protocol import ConsumerProtocolMemberAssignment

from scripts.experiments.availability_probe import classify_response
from scripts.experiments.common import load_json, sanitize_text
from scripts.experiments.controlled_workload import build_events
from scripts.experiments.create_freeze import validate_settings
from scripts.experiments.evidence_export import export_evidence
from scripts.experiments.estimate_azure_burn import calculate
from scripts.experiments.kafka_consumer_progress import decode_assignment
from scripts.experiments.partition_key_manifest import (
    KAFKA_PRODUCER_VERSION,
    build_entries,
    key_partition,
    select_pair,
)
from scripts.experiments.workload_freshness import response_rows


class AvailabilityProbeTests(unittest.TestCase):
    def test_valid_graphql_response(self) -> None:
        body = json.dumps(
            {
                "data": {
                    "shipment": {
                        "shipmentId": "SHP-TEST",
                        "latestEventVersion": 5,
                    }
                }
            }
        ).encode("utf-8")
        self.assertEqual(
            classify_response(200, body, "SHP-TEST", 5),
            (True, "", ""),
        )

    def test_version_mismatch_fails(self) -> None:
        body = b'{"data":{"shipment":{"shipmentId":"SHP-TEST","latestEventVersion":4}}}'
        success, category, _ = classify_response(200, body, "SHP-TEST", 5)
        self.assertFalse(success)
        self.assertEqual(category, "version_mismatch")


class ControlledWorkloadTests(unittest.TestCase):
    def test_frozen_workload_distribution(self) -> None:
        args = argparse.Namespace(
            run_id="E1-R1",
            shipment_a="SHIP-A",
            shipment_b="SHIP-B",
            logistic_topic="logistic",
            delivery_topic="delivery",
            event_count=600,
            interval_seconds=1,
        )
        events = build_events(args)
        self.assertEqual(len(events), 600)
        for shipment_id in ("SHIP-A", "SHIP-B"):
            shipment_events = [event for _, event in events if event["shipment_id"] == shipment_id]
            self.assertEqual(len(shipment_events), 300)
            self.assertEqual(
                [event["event_version"] for event in shipment_events],
                list(range(1, 301)),
            )
            self.assertEqual(
                {topic for topic, event in events if event["shipment_id"] == shipment_id},
                {"logistic", "delivery"},
            )


class PartitionManifestTests(unittest.TestCase):
    def test_pair_maps_to_both_partitions(self) -> None:
        shipment_a, shipment_b = select_pair("E1-R1", 2)
        self.assertEqual(key_partition(shipment_a, 2), 0)
        self.assertEqual(key_partition(shipment_b, 2), 1)
        self.assertNotEqual(shipment_a, shipment_b)

    def test_pinned_producer_version_is_available(self) -> None:
        self.assertEqual(KAFKA_PRODUCER_VERSION, "2.2.3")

    def test_each_key_records_producer_and_partitioner(self) -> None:
        entries = build_entries(["E1-r01"], 2)
        self.assertEqual(len(entries), 2)
        for entry in entries:
            self.assertEqual(entry["producer_version"], "kafka-python-ng 2.2.3")
            self.assertEqual(entry["partitioner"], "kafka-python-ng murmur2")


class ConsumerProgressTests(unittest.TestCase):
    def test_empty_member_assignment_decodes_to_empty_list(self) -> None:
        member = argparse.Namespace(member_assignment=b"")
        self.assertEqual(decode_assignment(member), [])

    def test_decoded_member_assignment_is_supported(self) -> None:
        member = argparse.Namespace(
            member_assignment=ConsumerProtocolMemberAssignment(
                0,
                [("logistic-events", [0, 1])],
                b"",
            )
        )
        self.assertEqual(
            decode_assignment(member),
            [
                {"topic": "logistic-events", "partition": 0},
                {"topic": "logistic-events", "partition": 1},
            ],
        )


class WorkloadFreshnessTests(unittest.TestCase):
    def test_two_controlled_shipments_are_recorded(self) -> None:
        latest_time = datetime.now(timezone.utc).isoformat()
        body = json.dumps(
            {
                "data": {
                    "shipmentA": {
                        "shipmentId": "SHIP-A",
                        "latestEventVersion": 12,
                        "latestEventTime": latest_time,
                    },
                    "shipmentB": {
                        "shipmentId": "SHIP-B",
                        "latestEventVersion": 11,
                        "latestEventTime": latest_time,
                    },
                }
            }
        ).encode()
        previous = {"SHIP-A": 10, "SHIP-B": 11}
        rows = response_rows(
            200,
            body,
            ("SHIP-A", "SHIP-B"),
            previous,
            300,
            "api-1",
            "westeurope",
        )
        self.assertEqual([row["shipment_id"] for row in rows], ["SHIP-A", "SHIP-B"])
        self.assertEqual([row["version_advanced"] for row in rows], ["true", "false"])
        self.assertEqual(previous, {"SHIP-A": 12, "SHIP-B": 11})


class EvidenceSanitizationTests(unittest.TestCase):
    def test_sensitive_values_are_redacted(self) -> None:
        example_password = "example-" + "password"
        example_key = "example-" + "key"
        source = (
            f'password="{example_password}" '
            f"postgresql://user:{example_password}@database.example/shipments "
            f"Endpoint=sb://example.servicebus.windows.net/;SharedAccessKey={example_key} "
            "subscription_id=11111111-1111-1111-1111-111111111111 8.8.8.8"
        )
        sanitized = sanitize_text(source)
        self.assertNotIn(example_password, sanitized)
        self.assertNotIn(example_key, sanitized)
        self.assertNotIn("11111111-1111-1111-1111-111111111111", sanitized)
        self.assertNotIn("8.8.8.8", sanitized)

    def test_export_sanitizes_text_and_rejects_binary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            destination = root / "export"
            source.mkdir()
            example_password = "example-" + "password"
            (source / "evidence.json").write_text(json.dumps({"password": example_password}))
            (source / "screenshot.png").write_bytes(b"not-a-real-image")
            manifest = export_evidence(source, destination)
            exported = (destination / "evidence.json").read_text()
            self.assertNotIn(example_password, exported)
            self.assertIn("[REDACTED]", exported)
            self.assertEqual(manifest["rejected_files"][0]["reason"], "binary_or_unsupported")


class BurnEstimateTests(unittest.TestCase):
    def test_repeat_affordability(self) -> None:
        result = calculate(
            {
                "budget": 10,
                "currency": "EUR",
                "requested_repeat_count": 2,
                "fixed_costs": [{"estimated_cost": 2}],
                "configurations": [
                    {
                        "configuration": "E1",
                        "measured_hours_per_repeat": 1,
                        "resources": [{"hourly_rate": 2, "quantity": 1}],
                    }
                ],
            }
        )
        self.assertTrue(result["requested_repeat_count_affordable"])
        self.assertEqual(result["estimated_total"], 6)


class FreezeValidationTests(unittest.TestCase):
    def test_frozen_values_validate(self) -> None:
        settings = load_json("infra/azure/experiment-settings.json")
        validate_settings(settings, allow_live_placeholders=True)

    def test_final_freeze_live_gates_are_satisfied(self) -> None:
        settings = load_json("infra/azure/experiment-settings.json")
        validate_settings(settings, allow_live_placeholders=False)


if __name__ == "__main__":
    unittest.main()
