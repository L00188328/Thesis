import argparse
import csv
from pathlib import Path

from scripts.experiments.common import ensure_parent, utc_now_iso


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append a UTC experiment timeline event")
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--detail", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = ensure_parent(args.output)
    exists = Path(output).exists() and Path(output).stat().st_size > 0
    with output.open("a", newline="") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=("timestamp_utc", "label", "detail"),
        )
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp_utc": utc_now_iso(),
                "label": args.label,
                "detail": args.detail,
            }
        )


if __name__ == "__main__":
    main()
