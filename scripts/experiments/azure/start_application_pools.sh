#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?AZURE_RESOURCE_GROUP is required}"
: "${AKS_CLUSTER_NAME:?AKS_CLUSTER_NAME is required}"
: "${APPLICATION_POOLS:?APPLICATION_POOLS is required}"

for node_pool in ${APPLICATION_POOLS}; do
  az aks nodepool start \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --cluster-name "$AKS_CLUSTER_NAME" \
    --nodepool-name "$node_pool" \
    --no-wait \
    --only-show-errors
  printf '%s application-pool-start-accepted pool=%s\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%S.%3NZ')" "$node_pool"
done
