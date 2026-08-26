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

### Discarded Diagnostic Attempts

The installed `rpk` version did not support this read command:

docker compose exec -T redpanda rpk redpanda config get redpanda.advertised_kafka_api

The following command was accidentally executed on the macOS host, where `rpk` was not installed:

rpk group describe shipment-aggregator
