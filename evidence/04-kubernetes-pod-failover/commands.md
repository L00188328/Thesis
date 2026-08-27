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

## D5. Controlled GraphQL API Pod Failure

date -u '+T0 API baseline: %Y-%m-%dT%H:%M:%SZ'

kubectl get pods -n thesis-ha -l app=api -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,IP:.status.podIP,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount,STARTED:.status.startTime'

for pod in $(kubectl get pods -n thesis-ha -l app=api -o name); do echo -n "$pod INSTANCE_ID="; kubectl exec -n thesis-ha "$pod" -- printenv INSTANCE_ID; done

kubectl get endpointslice -n thesis-ha -l kubernetes.io/service-name=api -o wide

## D6. Final Evidence and Runtime Audit

date -u '+%Y-%m-%dT%H:%M:%SZ'

kubectl config current-context

kubectl get nodes -o wide

kubectl get deployments,pods,services -n thesis-ha -o wide

kubectl get pods -n thesis-ha -o custom-columns='NAME:.metadata.name,STATUS:.status.phase,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount'

kubectl get endpointslice -n thesis-ha -o wide

for pod in $(kubectl get pods -n thesis-ha -l app=aggregator -o name); do echo "=== $pod ==="; kubectl exec -n thesis-ha "$pod" -- python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8081/health", timeout=5).read().decode()); print(urllib.request.urlopen("http://127.0.0.1:8081/ready", timeout=5).read().decode())'; done

for pod in $(kubectl get pods -n thesis-ha -l app=api -o name); do echo "=== $pod ==="; kubectl exec -n thesis-ha "$pod" -- python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5).read().decode()); print(urllib.request.urlopen("http://127.0.0.1:8000/ready", timeout=5).read().decode())'; done

docker compose ps -a postgres redpanda producer-logistic-center producer-delivery-base

docker compose exec -T redpanda rpk group describe shipment-aggregator

docker compose exec -T postgres psql -U postgres -d shipments -P pager=off -c "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND (tgname ILIKE '%fail%' OR tgname ILIKE '%test%'); SELECT proname FROM pg_proc JOIN pg_namespace n ON n.oid = pg_proc.pronamespace WHERE n.nspname = 'public' AND (proname ILIKE '%fail%' OR proname ILIKE '%test%');"

docker compose exec -T postgres psql -U postgres -d shipments -P pager=off -c "SELECT COUNT(*) AS history_rows, COUNT(DISTINCT event_id) AS unique_event_ids, COUNT(DISTINCT event_version) AS unique_versions, MIN(event_version) AS first_version, MAX(event_version) AS highest_version FROM all_shipment_events WHERE shipment_id = 'TST-K8S-FAILOVER-001'; SELECT shipment_id, latest_event_version FROM current_shipment_state WHERE shipment_id = 'TST-K8S-FAILOVER-001';"

git status --short

git diff --stat

git diff --check

git ls-files k8s scripts/kubernetes evidence/04-kubernetes-pod-failover | sort

git check-ignore -v k8s/secret.local.yaml

rg -n --hidden --glob '!evidence/**' --glob '!.git/**' 'TEST_CRASH|test_crash_after_db_commit|TEST_CRASH_MARKER|trg_fail_db_evidence|fail_db_evidence|d5-graphql|d2-health-check|d3-api-routing-check|k2-connectivity-check' .

kubectl apply --dry-run=client -f k8s/namespace.yaml -f k8s/configmap.yaml -f k8s/secret.local.yaml -f k8s/services.yaml -f k8s/aggregator-deployment.yaml -f k8s/api-deployment.yaml -o name

kubectl diff -f k8s/namespace.yaml -f k8s/configmap.yaml -f k8s/secret.local.yaml -f k8s/services.yaml -f k8s/aggregator-deployment.yaml -f k8s/api-deployment.yaml

kubectl get configmap,secret -n thesis-ha

kubectl get pods,jobs,cronjobs -n thesis-ha -o name

rg -o 'Screenshots/[^` ]+' evidence/04-kubernetes-pod-failover/results.md | sort -u

find evidence/04-kubernetes-pod-failover/Screenshots -maxdepth 1 -type f

kubectl run d5-graphql-baseline -n thesis-ha --image=curlimages/curl:8.10.1 --restart=Never --rm -i -- sh -c 'payload="{\"query\":\"query { shipment(shipmentId: \\\"TST-K8S-FAILOVER-001\\\") { shipmentId latestEventVersion } }\"}"; for request in $(seq 1 20); do status=$(curl -sS -D /tmp/headers -o /tmp/body -w "%{http_code}" -X POST http://api:8000/graphql/ -H "Content-Type: application/json" --data "$payload"); instance=$(grep -i "^x-instance-id:" /tmp/headers | tail -n 1 | tr -d "\r" | cut -d " " -f 2); if [ "$status" = "200" ] && grep -q "\"latestEventVersion\":120" /tmp/body; then echo "request=$request status=200 valid=true instance=$instance"; else echo "request=$request status=$status valid=false instance=$instance body=$(cat /tmp/body)"; fi; done'

kubectl run d5-graphql-baseline-capture -n thesis-ha --image=curlimages/curl:8.10.1 --restart=Never -- sh -c 'payload="{\"query\":\"query { shipment(shipmentId: \\\"TST-K8S-FAILOVER-001\\\") { shipmentId latestEventVersion } }\"}"; for request in $(seq 1 20); do status=$(curl -sS -D /tmp/headers -o /tmp/body -w "%{http_code}" -X POST http://api:8000/graphql/ -H "Content-Type: application/json" --data "$payload"); instance=$(grep -i "^x-instance-id:" /tmp/headers | tail -n 1 | tr -d "\r" | cut -d " " -f 2); if [ "$status" = "200" ] && grep -q "\"latestEventVersion\":120" /tmp/body; then echo "request=$request status=200 valid=true instance=$instance"; else echo "request=$request status=$status valid=false instance=$instance"; fi; sleep 0.2; done; sleep 5'

kubectl wait --for=condition=Ready pod/d5-graphql-baseline-capture -n thesis-ha --timeout=60s

kubectl logs -f pod/d5-graphql-baseline-capture -n thesis-ha | tee /tmp/d5-graphql-baseline.log

echo "Successful valid requests:"

grep -c 'status=200 valid=true' /tmp/d5-graphql-baseline.log

echo "Invalid or failed requests:"

grep -c 'valid=false' /tmp/d5-graphql-baseline.log || true

echo "Requests per API instance:"

grep -o 'instance=[^ ]*' /tmp/d5-graphql-baseline.log | sort | uniq -c

kubectl delete pod d5-graphql-baseline-capture -n thesis-ha

kubectl run d5-graphql-failover-stream -n thesis-ha --image=curlimages/curl:8.10.1 --restart=Never -- sh -c 'payload="{\"query\":\"query { shipment(shipmentId: \\\"TST-K8S-FAILOVER-001\\\") { shipmentId latestEventVersion } }\"}"; for request in $(seq 1 90); do timestamp=$(date -u "+%Y-%m-%dT%H:%M:%SZ"); status=$(curl -sS --connect-timeout 2 --max-time 5 -D /tmp/headers -o /tmp/body -w "%{http_code}" -X POST http://api:8000/graphql/ -H "Content-Type: application/json" --data "$payload" || echo "CURL_FAILED"); instance=$(grep -i "^x-instance-id:" /tmp/headers 2>/dev/null | tail -n 1 | tr -d "\r" | cut -d " " -f 2); if [ "$status" = "200" ] && grep -q "\"latestEventVersion\":120" /tmp/body; then echo "REQUEST number=$request timestamp=$timestamp status=200 valid=true instance=$instance"; else echo "REQUEST number=$request timestamp=$timestamp status=$status valid=false instance=${instance:-none}"; fi; sleep 1; done; echo "STREAM_COMPLETE timestamp=$(date -u "+%Y-%m-%dT%H:%M:%SZ")"'

kubectl wait --for=condition=Ready pod/d5-graphql-failover-stream -n thesis-ha --timeout=60s

kubectl logs -f pod/d5-graphql-failover-stream -n thesis-ha | tee /tmp/d5-graphql-failover.log

date -u '+T1 API deletion requested: %Y-%m-%dT%H:%M:%SZ'

kubectl delete pod api-566df6fbd9-mhzjc -n thesis-ha --wait=false

date -u '+T1 API deletion command returned: %Y-%m-%dT%H:%M:%SZ'

kubectl get pods -n thesis-ha -l app=api -o wide

kubectl rollout status deployment/api -n thesis-ha --timeout=120s

date -u '+T5 API replacement Ready: %Y-%m-%dT%H:%M:%SZ'

kubectl get pods -n thesis-ha -l app=api -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,IP:.status.podIP,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount,STARTED:.status.startTime'

echo "Total requests:"

grep -c '^REQUEST ' /tmp/d5-graphql-failover.log

echo "Successful valid requests:"

grep -c 'status=200 valid=true' /tmp/d5-graphql-failover.log

echo "Invalid or failed requests:"

grep -c 'valid=false' /tmp/d5-graphql-failover.log || true

echo "Requests per API instance:"

grep -o 'instance=[^ ]*' /tmp/d5-graphql-failover.log | sort | uniq -c

echo "First requests:"

grep '^REQUEST ' /tmp/d5-graphql-failover.log | head -n 3

echo "Last requests:"

grep '^REQUEST ' /tmp/d5-graphql-failover.log | tail -n 3

kubectl delete pod d5-graphql-failover-stream -n thesis-ha --ignore-not-found

date -u '+D5 final state: %Y-%m-%dT%H:%M:%SZ'

kubectl get deployment/api -n thesis-ha

kubectl get pods -n thesis-ha -l app=api -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,IP:.status.podIP,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount'

kubectl get endpointslice -n thesis-ha -l kubernetes.io/service-name=api -o wide
