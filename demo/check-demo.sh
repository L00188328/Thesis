#!/usr/bin/env bash
set -euo pipefail
demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -ne 0 ]]; then echo 'Usage: ./demo/check-demo.sh' >&2; exit 2; fi
exec python3 "$demo_dir/demo_failover.py" appzone1 --check
