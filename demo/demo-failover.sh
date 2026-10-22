#!/usr/bin/env bash
set -euo pipefail
demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case " ${*} " in
  *" --reset "*|*" --check "*) echo 'Use reset-demo.sh or check-demo.sh for maintenance.' >&2; exit 2 ;;
esac
exec python3 "$demo_dir/demo_failover.py" "$@"
