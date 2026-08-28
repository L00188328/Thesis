#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?AZURE_RESOURCE_GROUP is required}"
: "${AKS_CLUSTER_NAME:?AKS_CLUSTER_NAME is required}"
: "${REGION_A_APP_POOLS:?REGION_A_APP_POOLS is required}"
: "${TIMELINE_OUTPUT:?TIMELINE_OUTPUT is required}"

mkdir -p "$(dirname "$TIMELINE_OUTPUT")"
if [[ ! -s "$TIMELINE_OUTPUT" ]]; then
  printf 'timestamp_utc,label,detail\n' >"$TIMELINE_OUTPUT"
fi

timestamp() {
  date -u '+%Y-%m-%dT%H:%M:%S.%3NZ'
}

csv_record() {
  printf '%s,%s,%s\n' "$(timestamp)" "$1" "$2" | tee -a "$TIMELINE_OUTPUT"
}

csv_record "T2-region-a-stop-command" "pools=${REGION_A_APP_POOLS}"
for node_pool in ${REGION_A_APP_POOLS}; do
  az aks nodepool stop \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --cluster-name "$AKS_CLUSTER_NAME" \
    --nodepool-name "$node_pool" \
    --no-wait \
    --only-show-errors
  csv_record "region-a-stop-accepted" "pool=${node_pool}"
done
