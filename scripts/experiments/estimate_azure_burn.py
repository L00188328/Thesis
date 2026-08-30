import argparse
from typing import Any

from scripts.experiments.common import load_json, utc_now_iso, write_json


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    budget = float(payload["budget"])
    fixed_cost = sum(float(item["estimated_cost"]) for item in payload.get("fixed_costs", []))
    configuration_costs: list[dict[str, Any]] = []
    one_repeat_total = 0.0
    planned_measured_cost = 0.0
    uniform_repeat_count = payload.get("requested_repeat_count")
    requested_repeat_counts = payload.get("requested_repeat_counts")
    if requested_repeat_counts is None:
        requested_repeat_counts = {
            configuration["configuration"]: int(uniform_repeat_count)
            for configuration in payload["configurations"]
        }
    for configuration in payload["configurations"]:
        configuration_name = configuration["configuration"]
        repeats = int(requested_repeat_counts[configuration_name])
        hourly = sum(
            float(resource["hourly_rate"]) * float(resource.get("quantity", 1))
            for resource in configuration["resources"]
        )
        hours = float(configuration["measured_hours_per_repeat"])
        cost_per_repeat = hourly * hours
        one_repeat_total += cost_per_repeat
        planned_configuration_cost = cost_per_repeat * repeats
        planned_measured_cost += planned_configuration_cost
        configuration_costs.append(
            {
                "configuration": configuration_name,
                "estimated_hourly_burn": round(hourly, 6),
                "measured_hours_per_repeat": hours,
                "estimated_cost_per_repeat": round(cost_per_repeat, 6),
                "requested_measured_repeats": repeats,
                "estimated_measured_cost": round(planned_configuration_cost, 6),
            }
        )
    remaining = max(0.0, budget - fixed_cost)
    maximum_repeats = int(remaining // one_repeat_total) if one_repeat_total else 0
    estimated_total = fixed_cost + planned_measured_cost
    plan_affordable = estimated_total <= budget
    return {
        "schema_version": 1,
        "generated_timestamp_utc": utc_now_iso(),
        "scope": payload.get("scope", "Azure experiment estimate"),
        "currency": payload["currency"],
        "budget": budget,
        "fixed_estimated_cost": round(fixed_cost, 6),
        "one_repeat_all_configurations_cost": round(one_repeat_total, 6),
        "maximum_repeat_count_within_estimate": maximum_repeats,
        "requested_repeat_counts": requested_repeat_counts,
        "requested_plan_affordable": plan_affordable,
        "requested_repeat_count_affordable": plan_affordable,
        "planned_measured_cost": round(planned_measured_cost, 6),
        "estimated_total": round(estimated_total, 6),
        "estimated_remaining_total": round(estimated_total, 6),
        "completed_e1_cost": payload.get("completed_e1_cost"),
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
    if not result["requested_plan_affordable"]:
        raise SystemExit("requested repeat count exceeds the supplied budget estimate")


if __name__ == "__main__":
    main()
