#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?AZURE_RESOURCE_GROUP is required}"
: "${AKS_CLUSTER_NAME:?AKS_CLUSTER_NAME is required}"
: "${FAILED_ZONE_POOL:?FAILED_ZONE_POOL is required}"
: "${TIMELINE_OUTPUT:?TIMELINE_OUTPUT is required}"

mkdir -p "$(dirname "$TIMELINE_OUTPUT")"
if [[ ! -s "$TIMELINE_OUTPUT" ]]; then
  printf 'timestamp_utc,label,detail\n' >"$TIMELINE_OUTPUT"
fi

timestamp() {
  date -u '+%Y-%m-%dT%H:%M:%S.%3NZ'
}

printf '%s,%s,%s\n' "$(timestamp)" "F1-T2-command" "pool=${FAILED_ZONE_POOL}" \
  | tee -a "$TIMELINE_OUTPUT"

az aks nodepool stop \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --cluster-name "$AKS_CLUSTER_NAME" \
  --nodepool-name "$FAILED_ZONE_POOL" \
  --no-wait \
  --only-show-errors

printf '%s,%s,%s\n' "$(timestamp)" "F1-T2-accepted" "pool=${FAILED_ZONE_POOL}" \
  | tee -a "$TIMELINE_OUTPUT"
