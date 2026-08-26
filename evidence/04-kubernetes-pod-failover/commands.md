# Kubernetes Pod-Level Resilience Commands

Record only commands that were actually executed. Preliminary checks do not require screenshots unless explicitly identified later.

## D1. Local Kubernetes Environment

docker context show

kubectl version --client

kubectl config get-contexts

kubectl config current-context

kubectl cluster-info

kubectl get nodes -o wide

After enabling the Docker Desktop single-node Kubeadm cluster:

kubectl config use-context docker-desktop

kubectl cluster-info

kubectl get nodes -o wide

kubectl version

## D2. Baseline Preparation and Deployment

docker compose ps postgres redpanda

kubectl run k2-connectivity-check --image=busybox:1.36.1 --restart=Never --rm -i -- sh -c 'nslookup host.docker.internal && nc -zvw5 host.docker.internal 5433 && nc -zvw5 host.docker.internal 19092'

docker image inspect thesis/aggregator:local thesis/api:local --format 'Image: {{index .RepoTags 0}} | ID: {{.Id}} | Created: {{.Created}}'

docker inspect --format 'Container: {{.Name}} | Mounts: {{json .Mounts}}' "$(docker compose ps -q redpanda)"

docker inspect --format='Redpanda command: {{json .Config.Cmd}}' "$(docker compose ps -q redpanda)"

docker compose exec -T redpanda rpk group describe shipment-aggregator

docker compose up -d redpanda

docker inspect --format='Mounts: {{json .Mounts}} | Command: {{json .Config.Cmd}}' "$(docker compose ps -q redpanda)"

docker compose exec -T redpanda rpk group describe shipment-aggregator

kubectl rollout status deployment/aggregator -n thesis-ha --timeout=120s

kubectl rollout status deployment/api -n thesis-ha --timeout=120s

kubectl get deployments,pods,services -n thesis-ha -o wide

kubectl run d2-health-check -n thesis-ha --image=busybox:1.36.1 --restart=Never --rm -i -- sh -c 'for url in http://aggregator:8081/health http://aggregator:8081/ready http://api:8000/health http://api:8000/ready; do echo; echo "=== $url ==="; wget -S -O - "$url"; echo; done'

kubectl logs deployment/aggregator -n thesis-ha --since=20m | grep -E '"message": "aggregator_started"|"message": "event_projected"'

kubectl logs deployment/api -n thesis-ha --since=20m | grep '"message": "request_complete"' | tail -n 10

docker compose exec -T redpanda rpk group describe shipment-aggregator

docker compose exec -T postgres psql -U postgres -d shipments -c "SELECT COUNT(*) AS history_before FROM all_shipment_events WHERE event_id = 'k8s-baseline-evt-001'; SELECT COUNT(*) AS state_before FROM current_shipment_state WHERE shipment_id = 'TST-K8S-BASELINE-001';"

printf '%s\n' '{"event_id":"k8s-baseline-evt-001","shipment_id":"TST-K8S-BASELINE-001","event_version":1,"domain":"LogisticCenter","event_type":"ParcelReceivedAtHub","occurred_at":"2026-08-26T09:45:00+00:00","location":"Vienna Kubernetes Hub","details":{"test":"kubernetes-baseline"}}' | docker compose exec -T redpanda rpk topic produce logistic-center-events --compression none --partition 0 --key TST-K8S-BASELINE-001

docker compose exec -T postgres psql -U postgres -d shipments -P pager=off -c "SELECT event_id, shipment_id, event_version, domain, event_type, occurred_at, location, details FROM all_shipment_events WHERE event_id = 'k8s-baseline-evt-001'; SELECT COUNT(*) AS historical_row_count FROM all_shipment_events WHERE event_id = 'k8s-baseline-evt-001'; SELECT shipment_id, latest_event_version, latest_event_type, latest_event_domain, latest_location, latest_event_time FROM current_shipment_state WHERE shipment_id = 'TST-K8S-BASELINE-001';"

kubectl logs deployment/aggregator -n thesis-ha --since=10m | grep 'k8s-baseline-evt-001'

docker compose exec -T redpanda rpk group describe shipment-aggregator

kubectl port-forward -n thesis-ha service/api 18000:8000

curl -s -X POST http://localhost:18000/graphql/ -H 'Content-Type: application/json' --data '{"query":"query($shipmentId: String!) { shipment(shipmentId: $shipmentId) { shipmentId latestEventVersion latestEventType latestEventDomain latestLocation latestEventTime timeline { eventId eventVersion domain eventType location occurredAt } } }","variables":{"shipmentId":"TST-K8S-BASELINE-001"}}' | python3 -m json.tool

### Discarded Diagnostic Attempts

The installed `rpk` version did not support this read command:

docker compose exec -T redpanda rpk redpanda config get redpanda.advertised_kafka_api

The following command was accidentally executed on the macOS host, where `rpk` was not installed:

rpk group describe shipment-aggregator

## D3. Replicated Application Pods

kubectl apply -f k8s/aggregator-deployment.yaml -f k8s/api-deployment.yaml

kubectl rollout status deployment/aggregator -n thesis-ha --timeout=120s

kubectl rollout status deployment/api -n thesis-ha --timeout=120s

kubectl get deployments,pods -n thesis-ha -o wide

kubectl get pods -n thesis-ha -l app=aggregator -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,IP:.status.podIP,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount'

kubectl logs -n thesis-ha -l app=aggregator --prefix=true --since=20m | grep '"message": "aggregator_started"'

docker compose exec -T redpanda rpk group describe shipment-aggregator

for pod in $(kubectl get pods -n thesis-ha -l app=aggregator -o name); do echo; echo "=== $pod ==="; kubectl logs -n thesis-ha "$pod" | grep '"message": "aggregator_started"'; done

docker compose exec -T redpanda rpk group describe shipment-aggregator

docker compose exec -T postgres psql -U postgres -d shipments -c "SELECT COUNT(*) AS history_before FROM all_shipment_events WHERE event_id IN ('k8s-replica-evt-v1','k8s-replica-evt-v2'); SELECT COUNT(*) AS state_before FROM current_shipment_state WHERE shipment_id = 'TST-K8S-REPLICA-001';"

printf '%s\n' '{"event_id":"k8s-replica-evt-v1","shipment_id":"TST-K8S-REPLICA-001","event_version":1,"domain":"LogisticCenter","event_type":"ParcelReceivedAtHub","occurred_at":"2026-08-26T11:10:00+00:00","location":"Graz Kubernetes Hub","details":{"test":"kubernetes-replication","sequence":"v1"}}' | docker compose exec -T redpanda rpk topic produce logistic-center-events --compression none --partition 0 --key TST-K8S-REPLICA-001

printf '%s\n' '{"event_id":"k8s-replica-evt-v2","shipment_id":"TST-K8S-REPLICA-001","event_version":2,"domain":"DeliveryBase","event_type":"OutForDelivery","occurred_at":"2026-08-26T11:11:00+00:00","location":"Graz Delivery Base","details":{"test":"kubernetes-replication","sequence":"v2"}}' | docker compose exec -T redpanda rpk topic produce delivery-base-events --compression none --partition 0 --key TST-K8S-REPLICA-001

for pod in $(kubectl get pods -n thesis-ha -l app=aggregator -o name); do echo; echo "=== $pod ==="; kubectl logs -n thesis-ha "$pod" | grep -E 'k8s-replica-evt-v1|k8s-replica-evt-v2' || echo "(no matching events in $pod)"; done

docker compose exec -T postgres psql -U postgres -d shipments -P pager=off -c "SELECT event_id, event_version, domain, event_type, location, occurred_at FROM all_shipment_events WHERE shipment_id = 'TST-K8S-REPLICA-001' ORDER BY event_version; SELECT COUNT(*) AS history_rows, COUNT(DISTINCT event_id) AS unique_event_ids FROM all_shipment_events WHERE shipment_id = 'TST-K8S-REPLICA-001'; SELECT shipment_id, latest_event_version, latest_event_type, latest_event_domain, latest_location, latest_event_time FROM current_shipment_state WHERE shipment_id = 'TST-K8S-REPLICA-001';"

docker compose exec -T redpanda rpk group describe shipment-aggregator

kubectl get pods -n thesis-ha -l app=api -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,IP:.status.podIP,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount'

kubectl run d3-api-routing-check -n thesis-ha --image=busybox:1.36.1 --restart=Never --rm -i -- sh -c 'for request in $(seq 1 20); do echo -n "request $request: "; wget -S -O /dev/null http://api:8000/health 2>&1 | grep -i "x-instance-id"; done'

## D4. Controlled Aggregator Pod Failure

date -u '+T0 baseline: %Y-%m-%dT%H:%M:%SZ'

kubectl get pods -n thesis-ha -l app=aggregator -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,IP:.status.podIP,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount,STARTED:.status.startTime'

for pod in $(kubectl get pods -n thesis-ha -l app=aggregator -o name); do echo -n "$pod INSTANCE_ID="; kubectl exec -n thesis-ha "$pod" -- printenv INSTANCE_ID; done

docker compose ps -a producer-logistic-center producer-delivery-base

docker compose exec -T redpanda rpk group describe shipment-aggregator

docker compose exec -T postgres psql -U postgres -d shipments -c "SELECT COUNT(*) AS history_before FROM all_shipment_events WHERE shipment_id = 'TST-K8S-FAILOVER-001'; SELECT COUNT(*) AS state_before FROM current_shipment_state WHERE shipment_id = 'TST-K8S-FAILOVER-001';"

./scripts/kubernetes/d4-controlled-stream.sh 120 1 | tee /tmp/d4-controlled-stream.log

date -u '+T1 deletion requested: %Y-%m-%dT%H:%M:%SZ'

kubectl delete pod aggregator-8cf7f9955-4q8nl -n thesis-ha --wait=false

date -u '+T1 deletion command returned: %Y-%m-%dT%H:%M:%SZ'

kubectl get pods -n thesis-ha -l app=aggregator -o wide

kubectl rollout status deployment/aggregator -n thesis-ha --timeout=120s

date -u '+T5 replacement Ready: %Y-%m-%dT%H:%SZ'

kubectl get pods -n thesis-ha -l app=aggregator -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,IP:.status.podIP,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount,STARTED:.status.startTime'

kubectl wait --for=delete pod/aggregator-8cf7f9955-4q8nl -n thesis-ha --timeout=60s

date -u '+T2 original Pod fully deleted: %Y-%m-%dT%H:%M:%SZ'

kubectl get pods -n thesis-ha -l app=aggregator -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,IP:.status.podIP,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount,STARTED:.status.startTime'

echo "Published event count:"

grep -c '^STREAM event=' /tmp/d4-controlled-stream.log

echo "First stream entries:"

grep '^STREAM event=' /tmp/d4-controlled-stream.log | head -n 3

echo "Last stream entries:"

grep '^STREAM event=' /tmp/d4-controlled-stream.log | tail -n 3

date -u '+T6 recovery verification: %Y-%m-%dT%H:%M:%SZ'

for pod in $(kubectl get pods -n thesis-ha -l app=aggregator -o name); do echo; echo "=== $pod ==="; echo -n "Matching event count: "; kubectl logs -n thesis-ha "$pod" | grep -c '"shipment_id": "TST-K8S-FAILOVER-001"' || true; echo "First matching events:"; kubectl logs -n thesis-ha "$pod" | grep '"shipment_id": "TST-K8S-FAILOVER-001"' | head -n 3; echo "Last matching events:"; kubectl logs -n thesis-ha "$pod" | grep '"shipment_id": "TST-K8S-FAILOVER-001"' | tail -n 3; done

docker compose exec -T redpanda rpk group describe shipment-aggregator

docker compose exec -T postgres psql -U postgres -d shipments -P pager=off -c "
SELECT
  COUNT(*) AS history_rows,
  COUNT(DISTINCT event_id) AS unique_event_ids,
  COUNT(DISTINCT event_version) AS unique_versions,
  MIN(event_version) AS first_version,
  MAX(event_version) AS highest_version
FROM all_shipment_events
WHERE shipment_id = 'TST-K8S-FAILOVER-001';

SELECT
  shipment_id,
  latest_event_version,
  latest_event_type,
  latest_event_domain,
  latest_location,
  latest_event_time
FROM current_shipment_state
WHERE shipment_id = 'TST-K8S-FAILOVER-001';

SELECT event_version, COUNT(*) AS duplicate_count
FROM all_shipment_events
WHERE shipment_id = 'TST-K8S-FAILOVER-001'
GROUP BY event_version
HAVING COUNT(*) > 1
ORDER BY event_version;
"
