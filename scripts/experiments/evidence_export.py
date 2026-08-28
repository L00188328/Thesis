import argparse
import hashlib
from pathlib import Path
from typing import Any

from scripts.experiments.common import ensure_parent, sanitize_text, utc_now_iso, write_json


TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".log", ".md", ".txt", ".yaml", ".yml"}


def export_evidence(source: Path, destination: Path) -> dict[str, Any]:
    source = source.resolve()
    destination = destination.resolve()
    if not source.is_dir():
        raise ValueError("evidence source must be a directory")
    if destination == source or source in destination.parents:
        raise ValueError("evidence destination must be outside the source directory")

    exported: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            rejected.append({"path": str(path.relative_to(source)), "reason": "symlink"})
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if path.suffix.lower() not in TEXT_SUFFIXES:
            rejected.append({"path": str(relative), "reason": "binary_or_unsupported"})
            continue
        try:
            sanitized = sanitize_text(path.read_text())
        except UnicodeDecodeError:
            rejected.append({"path": str(relative), "reason": "non_utf8"})
            continue
        target = ensure_parent(destination / relative)
        target.write_text(sanitized)
        exported.append(
            {
                "path": str(relative),
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        )

    manifest = {
        "schema_version": 1,
        "generated_timestamp_utc": utc_now_iso(),
        "source_label": source.name,
        "exported_files": exported,
        "rejected_files": rejected,
        "binary_policy": "Binary and image files are rejected because text redaction cannot prove that they contain no secrets.",
    }
    write_json(destination / "export-manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export redacted text evidence")
    parser.add_argument("--source", required=True)
    parser.add_argument("--destination", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    destination = Path(args.destination)
    if destination.exists():
        if any(destination.iterdir()):
            raise ValueError("evidence destination must be empty")
    else:
        destination.mkdir(parents=True)
    manifest = export_evidence(Path(args.source), destination)
    if manifest["rejected_files"]:
        raise SystemExit(
            "evidence export rejected unsupported files; review export-manifest.json and provide separately sanitised replacements"
        )


if __name__ == "__main__":
    main()
