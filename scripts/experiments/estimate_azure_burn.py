import argparse
from typing import Any

from scripts.experiments.common import load_json, utc_now_iso, write_json


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    budget = float(payload["budget"])
    fixed_cost = sum(float(item["estimated_cost"]) for item in payload.get("fixed_costs", []))
    configuration_costs: list[dict[str, Any]] = []
    one_repeat_total = 0.0
    for configuration in payload["configurations"]:
        hourly = sum(
            float(resource["hourly_rate"]) * float(resource.get("quantity", 1))
            for resource in configuration["resources"]
        )
        hours = float(configuration["measured_hours_per_repeat"])
        cost_per_repeat = hourly * hours
        one_repeat_total += cost_per_repeat
        configuration_costs.append(
            {
                "configuration": configuration["configuration"],
                "estimated_hourly_burn": round(hourly, 6),
                "measured_hours_per_repeat": hours,
                "estimated_cost_per_repeat": round(cost_per_repeat, 6),
            }
        )
    remaining = max(0.0, budget - fixed_cost)
    maximum_repeats = int(remaining // one_repeat_total) if one_repeat_total else 0
    requested_repeats = int(payload["requested_repeat_count"])
    return {
        "schema_version": 1,
        "generated_timestamp_utc": utc_now_iso(),
        "currency": payload["currency"],
        "budget": budget,
        "fixed_estimated_cost": round(fixed_cost, 6),
        "one_repeat_all_configurations_cost": round(one_repeat_total, 6),
        "maximum_repeat_count_within_estimate": maximum_repeats,
        "requested_repeat_count": requested_repeats,
        "requested_repeat_count_affordable": requested_repeats <= maximum_repeats,
        "estimated_total": round(fixed_cost + requested_repeats * one_repeat_total, 6),
        "configurations": configuration_costs,
        "assumptions": payload.get("assumptions", []),
        "price_sources": payload.get("price_sources", []),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate frozen Azure experiment burn")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = calculate(load_json(args.input))
    write_json(args.output, result)
    if not result["requested_repeat_count_affordable"]:
        raise SystemExit("requested repeat count exceeds the supplied budget estimate")


if __name__ == "__main__":
    main()
