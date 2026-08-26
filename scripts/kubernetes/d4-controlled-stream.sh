#!/usr/bin/env bash
set -euo pipefail

shipment_id="TST-K8S-FAILOVER-001"
event_count="${1:-60}"
interval_seconds="${2:-1}"

for ((event_version = 1; event_version <= event_count; event_version++)); do
  event_id=$(printf "k8s-failover-evt-%03d" "$event_version")
  occurred_at=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
  payload=$(printf '{"event_id":"%s","shipment_id":"%s","event_version":%d,"domain":"LogisticCenter","event_type":"FailoverSequenceEvent","occurred_at":"%s","location":"Vienna Pod Failover Lab","details":{"test":"kubernetes-pod-failover","sequence":%d}}' "$event_id" "$shipment_id" "$event_version" "$occurred_at" "$event_version")

  printf 'STREAM event=%s version=%d published_at=%s\n' "$event_id" "$event_version" "$occurred_at"
  printf '%s\n' "$payload" | docker compose exec -T redpanda rpk topic produce logistic-center-events --compression none --partition 0 --key "$shipment_id"
  sleep "$interval_seconds"
done
