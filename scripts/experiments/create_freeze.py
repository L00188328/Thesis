import argparse
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from scripts.experiments.common import load_json, utc_now_iso, write_json


REQUIRED_TOP_LEVEL = {
    "billing",
    "regions",
    "skus",
    "event_hubs",
    "front_door",
    "probe_transport",
    "warm_up_runs_per_configuration",
    "repeat_count",
    "fault_mechanisms",
    "external_host",
}


def require_keys(payload: dict[str, Any], path: str, keys: set[str]) -> None:
    missing = sorted(keys - payload.keys())
    if missing:
        raise ValueError(f"{path} missing required fields: {', '.join(missing)}")


def git_output(arguments: list[str]) -> str:
    return subprocess.run(
        ["git", *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def validate_settings(
    settings: dict[str, Any], allow_live_placeholders: bool = True
) -> None:
    missing = sorted(REQUIRED_TOP_LEVEL - settings.keys())
    if missing:
        raise ValueError(f"missing freeze settings: {', '.join(missing)}")
    if int(settings["repeat_count"]) != 3:
        raise ValueError("methodology v1.0.2 requires exactly three measured repeats")
    if int(settings["warm_up_runs_per_configuration"]) != 1:
        raise ValueError("methodology v1.0.2 requires one discarded warm-up per configuration")
    if settings["event_hubs"].get("partitions_per_entity") != 2:
        raise ValueError("methodology v1.0.2 requires two partitions per Event Hub")
    if settings["event_hubs"].get("assignment_strategy") != "RoundRobinPartitionAssignor":
        raise ValueError("methodology v1.0.2 requires RoundRobinPartitionAssignor")
    require_keys(
        settings["event_hubs"],
        "event_hubs",
        {
            "namespace_tier",
            "throughput_units",
            "entities",
            "partitions_per_entity",
            "retention_days",
            "consumer_group",
            "producer_client",
            "partitioner",
            "assignment_strategy",
        },
    )
    if settings["event_hubs"]["entities"] != [
        "logistic-center-events",
        "delivery-base-events",
    ]:
        raise ValueError("event_hubs.entities must contain the two frozen entities in order")

    require_keys(
        settings["billing"],
        "billing",
        {
            "subscription_reference",
            "currency",
            "gross_spend_ceiling",
            "credits_or_discounts_assumed",
            "price_query_date",
            "live_price_confirmation_status",
        },
    )
    require_keys(
        settings["regions"],
        "regions",
        {"region_a", "region_b", "external_probe_location"},
    )
    skus = settings["skus"]
    require_keys(
        skus,
        "skus",
        {
            "aks_tier",
            "aks_kubernetes_minor",
            "aks_exact_patch",
            "event_hubs",
            "front_door",
            "cluster_configurations",
            "postgresql",
            "postgresql_storage_gib",
            "container_registry",
        },
    )
    if skus["aks_kubernetes_minor"] != "1.35":
        raise ValueError("skus.aks_kubernetes_minor must remain 1.35")
    if skus["event_hubs"] != "Standard" or skus["front_door"] != "Standard_AzureFrontDoor":
        raise ValueError("skus must include the frozen Event Hubs and Front Door tiers")
    if not allow_live_placeholders:
        exact_patch = str(skus["aks_exact_patch"])
        if not re.fullmatch(r"1\.35\.\d+", exact_patch):
            raise ValueError("select one exact AKS 1.35 patch available in both regions")
        if settings["billing"]["live_price_confirmation_status"] != "confirmed":
            raise ValueError("live Azure prices must be confirmed before final freeze generation")
    for index, cluster in enumerate(skus["cluster_configurations"]):
        require_keys(
            cluster,
            f"skus.cluster_configurations[{index}]",
            {
                "configuration",
                "region",
                "cluster_name",
                "parameter_file",
                "node_autoprovisioning",
                "system_pool",
                "application_pools",
            },
        )
        if cluster["node_autoprovisioning"] is not False:
            raise ValueError(f"skus.cluster_configurations[{index}] must disable node autoprovisioning")
        if not cluster["application_pools"]:
            raise ValueError(f"skus.cluster_configurations[{index}] must declare application pools")
        for pool_kind in ("system_pool",):
            require_keys(
                cluster[pool_kind],
                f"skus.cluster_configurations[{index}].{pool_kind}",
                {"name", "mode", "vm_size", "zones", "desired", "min", "max", "autoscaling"},
            )
        for pool_index, pool in enumerate(cluster["application_pools"]):
            require_keys(
                pool,
                f"skus.cluster_configurations[{index}].application_pools[{pool_index}]",
                {"name", "mode", "vm_size", "zones", "desired", "min", "max", "autoscaling"},
            )
    configurations = {cluster["configuration"] for cluster in skus["cluster_configurations"]}
    expected_configurations = {"E1", "E2-A/E2-B", "F1/G1/G2 Region A", "G1/G2 Region B"}
    if configurations != expected_configurations:
        raise ValueError("skus.cluster_configurations must define E1, E2, F1/Region A, and Region B")
    e1 = next(cluster for cluster in skus["cluster_configurations"] if cluster["configuration"] == "E1")
    if len(e1["application_pools"]) != 1 or e1["application_pools"][0]["zones"]:
        raise ValueError("E1 must use one non-zonal application pool")
    front_door = settings["front_door"]
    required_front_door = {
        "tier": "Standard_AzureFrontDoor",
        "probe_protocol": "Http",
        "probe_method": "GET",
        "probe_path": "/ready",
        "probe_interval_seconds": 10,
        "sample_size": 4,
        "successful_samples_required": 3,
        "additional_latency_milliseconds": 1000,
        "session_affinity": "Disabled",
        "profile_name": "thesis-ha-frontdoor",
        "endpoint_name": "thesis-ha",
        "origin_group_name": "thesis-origins",
        "route_name": "graphql-and-ui",
        "client_protocol": "Https",
        "health_probe_enabled": True,
        "forwarding_protocol": "HttpOnly",
        "origin_http_port": 80,
        "certificate_name_check": False,
        "origin_weight": 1000,
        "graphql_caching": "Disabled",
    }
    for key, expected in required_front_door.items():
        if front_door.get(key) != expected:
            raise ValueError(f"front_door.{key} must equal {expected!r}")
    require_keys(front_door, "front_door", {"origins", "client_protocol", "forwarding_protocol"})
    if len(front_door["origins"]) != 2:
        raise ValueError("front_door.origins must contain Region A and Region B")
    for index, origin in enumerate(front_door["origins"]):
        require_keys(
            origin,
            f"front_door.origins[{index}]",
            {"name", "enabled", "host_header_reference", "http_port", "weight", "priorities"},
        )
        if origin["enabled"] is not True:
            raise ValueError(f"front_door.origins[{index}] must remain enabled")
        require_keys(origin["priorities"], f"front_door.origins[{index}].priorities", {"G1", "G2"})
    origin_by_name = {origin["name"]: origin for origin in front_door["origins"]}
    if set(origin_by_name) != {"region-a", "region-b"}:
        raise ValueError("front_door.origins must be named region-a and region-b")
    if origin_by_name["region-a"]["priorities"] != {"G1": 1, "G2": 1}:
        raise ValueError("Region A Front Door priorities do not match G1/G2")
    if origin_by_name["region-b"]["priorities"] != {"G1": 2, "G2": 1}:
        raise ValueError("Region B Front Door priorities do not match G1/G2")

    require_keys(
        settings["fault_mechanisms"],
        "fault_mechanisms",
        {"E2-A", "E2-B", "F1", "region_a_failure", "G1", "G2"},
    )
    required_transports = {
        "E1": "HttpDirectRegionA",
        "E2-A": "HttpDirectRegionA",
        "E2-B": "HttpDirectRegionA",
        "F1": "HttpDirectRegionA",
        "G1": "HttpsFrontDoorToHttpOrigin",
        "G2": "HttpsFrontDoorToHttpOrigin",
    }
    if settings["probe_transport"] != required_transports:
        raise ValueError("probe_transport must match methodology v1.0.2")
    require_keys(
        settings["fault_mechanisms"]["region_a_failure"],
        "fault_mechanisms.region_a_failure",
        {"script", "ordered_application_pools", "command"},
    )
    require_keys(settings["fault_mechanisms"]["E2-A"], "fault_mechanisms.E2-A", {"action", "command"})
    require_keys(settings["fault_mechanisms"]["E2-B"], "fault_mechanisms.E2-B", {"action", "command"})
    require_keys(
        settings["fault_mechanisms"]["F1"],
        "fault_mechanisms.F1",
        {"script", "eligible_application_pools", "selection", "command"},
    )
    if settings["fault_mechanisms"]["F1"]["eligible_application_pools"] != ["appzone1", "appzone2"]:
        raise ValueError("F1 eligible application pools must match the zonal IaC topology")
    require_keys(
        settings["fault_mechanisms"]["G1"],
        "fault_mechanisms.G1",
        {"region_a_failure_reference", "region_b_activation_script", "ordered_region_b_application_pools"},
    )
    require_keys(
        settings["fault_mechanisms"]["G2"],
        "fault_mechanisms.G2",
        {"region_a_failure_reference", "region_b_state"},
    )
    if settings["fault_mechanisms"]["G1"].get("region_a_failure_reference") != settings["fault_mechanisms"]["G2"].get("region_a_failure_reference"):
        raise ValueError("G1 and G2 must use the same Region A failure action")
    require_keys(
        settings["external_host"],
        "external_host",
        {
            "host_id",
            "physical_location",
            "operating_system",
            "kernel",
            "connection_type",
            "network_interface",
            "isp_arrangement",
            "public_egress_label",
            "dns_arrangement",
            "time_synchronisation",
            "power",
            "sleep_policy_during_runs",
            "vpn_proxy",
            "tool_versions",
        },
    )
    require_keys(
        settings["external_host"]["tool_versions"],
        "external_host.tool_versions",
        {"docker", "kubectl", "python", "kafka_python_ng", "azure_cli_container", "bicep"},
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create methodology v1.0.2 freeze evidence")
    parser.add_argument("--settings", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--burn-estimate", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--checksum-output", required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_json(args.settings)
    validate_settings(settings, allow_live_placeholders=args.allow_dirty)
    protocol_path = Path(args.protocol)
    protocol_text = protocol_path.read_text()
    if "**Methodology version:** 1.0.2" not in protocol_text or "**Status:** Frozen" not in protocol_text:
        raise ValueError("protocol is not frozen as methodology version 1.0.2")
    status = git_output(["status", "--porcelain"])
    if status and not args.allow_dirty:
        raise ValueError("Git worktree must be clean; commit the frozen protocol and tooling first")
    burn_estimate = load_json(args.burn_estimate)
    if int(settings["repeat_count"]) != int(burn_estimate["requested_repeat_count"]):
        raise ValueError("repeat_count does not match the burn estimate")
    if not burn_estimate["requested_repeat_count_affordable"]:
        raise ValueError("repeat_count is not affordable under the burn estimate")
    completed_settings = copy.deepcopy(settings)
    completed_settings["billing"]["estimated_hourly_burn_by_configuration"] = {
        item["configuration"]: item["estimated_hourly_burn"]
        for item in burn_estimate["configurations"]
    }
    completed_settings["billing"]["estimated_total"] = burn_estimate["estimated_total"]
    completed_settings["billing"]["budget_ceiling"] = burn_estimate["budget"]
    payload = {
        "schema_version": 2,
        "protocol": {
            "version": "1.0.2",
            "git_commit": git_output(["rev-parse", "HEAD"]),
            "file": str(protocol_path),
            "sha256": hashlib.sha256(protocol_text.encode("utf-8")).hexdigest(),
            "frozen_timestamp_utc": utc_now_iso(),
            "worktree_clean": not bool(status),
        },
        **completed_settings,
        "burn_estimate": burn_estimate,
    }
    write_json(args.output, payload)
    output_bytes = Path(args.output).read_bytes()
    checksum = hashlib.sha256(output_bytes).hexdigest()
    Path(args.checksum_output).write_text(f"{checksum}  {args.output}\n")


if __name__ == "__main__":
    main()
