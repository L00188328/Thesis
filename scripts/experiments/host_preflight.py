import argparse
import hashlib
import os
import platform
import socket
import subprocess
import sys
from typing import Any

from scripts.experiments.common import utc_now_iso, write_json


def command_output(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        return "unavailable"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture controlled laptop preflight data")
    parser.add_argument("--host-id", required=True)
    parser.add_argument("--physical-location", required=True)
    parser.add_argument("--connection-type", choices=("wired", "wifi"), required=True)
    parser.add_argument("--network-interface", required=True)
    parser.add_argument("--public-egress-label", required=True)
    parser.add_argument("--dns-arrangement", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    hostname_hash = hashlib.sha256(socket.gethostname().encode("utf-8")).hexdigest()[:16]
    payload: dict[str, Any] = {
        "timestamp_utc": utc_now_iso(),
        "host_id": args.host_id,
        "hostname_sha256_prefix": hostname_hash,
        "physical_location": args.physical_location,
        "connection_type": args.connection_type,
        "network_interface": args.network_interface,
        "public_egress_label": args.public_egress_label,
        "dns_arrangement": args.dns_arrangement,
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "machine": platform.machine(),
        "time_utc": command_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]),
        "docker_version": command_output(["docker", "--version"]),
        "kubectl_client_version": command_output(["kubectl", "version", "--client"]),
        "vpn_proxy_environment_present": any(
            os.getenv(name)
            for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy")
        ),
        "power_state": command_output(["pmset", "-g", "batt"]),
        "sleep_settings": command_output(["pmset", "-g", "custom"]),
    }
    write_json(args.output, payload)


if __name__ == "__main__":
    main()
