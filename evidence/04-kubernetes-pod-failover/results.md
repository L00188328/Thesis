# Kubernetes Pod-Level Resilience Results

Complete each deployment or resilience section only after observing its result. This phase covers local Kubernetes Pod-level resilience only.

## D1. Local Kubernetes Environment

- Date/time: 2026-08-25 to 2026-08-26
- Test purpose: Establish a reachable local Kubernetes control plane and Ready node using the least disruptive environment compatible with the existing Docker Compose setup.
- Initial state: The `docker-desktop` context and `kubectl` v1.32.2 client existed, but the control plane at `127.0.0.1:6443` refused connections because Docker Desktop Kubernetes was not running.
- Selected environment: Docker Desktop Kubernetes using a single Kubeadm node. This phase evaluates Pod-level resilience, not node-level resilience.
- Expected result: The Docker Desktop control plane is reachable and the node reports `Ready`.
- Actual result: The `docker-desktop` context connected successfully after the cluster was enabled. The control plane and CoreDNS were reachable. Node `docker-desktop` reported `Ready` with control-plane role, Kubernetes v1.32.2, internal IP `192.168.65.3`, and Docker 28.1.1 runtime. Client and server versions both reported v1.32.2.
- PASS/FAIL: PASS
- Screenshot evidence: Not captured; these were preliminary environment checks.
- Anomalies or discarded attempts: The first `cluster-info` and node checks failed while Kubernetes was disabled. No installation or cluster workload had begun at that point.

## D2. Baseline Preparation and Deployment

- Date/time: 2026-08-26
- Test purpose: Verify Pod-to-Docker dependency reachability, confirm local application images, and make Redpanda's external listener resolvable from Kubernetes without losing existing Kafka data or offsets.
- Expected result: A temporary Pod resolves `host.docker.internal`, reaches PostgreSQL port 5433 and Redpanda port 19092, required images exist, and the Redpanda listener adjustment preserves its data volume and zero-lag offsets.
- Dependency connectivity: PASS — `host.docker.internal` resolved to `192.168.65.254` and IPv6 address `fdc4:f303:9324::254`; TCP connections to ports 5433 and 19092 succeeded. The temporary `k2-connectivity-check` Pod was deleted automatically.
- Local images: PASS — `thesis/aggregator:local` existed as image `sha256:4455cac1de36a3068d650ed8cf1cc0f579f329d3569ce0fbebc25d3725d10285`; `thesis/api:local` existed as image `sha256:a93e7da843cc6e069c7a09504fddca8821e5516047edaf05f0284b218e6eae0f`.
- Redpanda precondition: PASS — the broker used anonymous volume `846719c4ced71787a948a3783c099562eca13a7ede6c17672183e6b3340ff100` for `/var/lib/redpanda/data`; the consumer group was stable with one member and total lag zero at offsets 442 and 629.
- Kubernetes-specific listener adjustment: The external advertised address was changed from `localhost:19092` to `host.docker.internal:19092`; internal Docker clients continue using `redpanda:9092`.
- Listener-adjustment result: PASS — Redpanda was recreated successfully while retaining the same data volume. Existing committed/log-end offsets remained `442/442` and `629/629`, and total lag remained zero.
- Baseline deployment: PASS — Deployments `aggregator` and `api` each rolled out successfully with one desired, updated, available, and Ready replica. Pods `aggregator-8cf7f9955-2b76l` and `api-566df6fbd9-xwbsd` both reported `1/1 Running`, zero restarts, and placement on node `docker-desktop`. ClusterIP Services exposed ports 8081 and 8000 respectively.
- Service health and readiness: PASS — Aggregator `/health` and `/ready` returned HTTP 200 with `status: ok` and instance ID `aggregator-8cf7f9955-2b76l`. API `/health` and `/ready` returned HTTP 200 with `status: ok`, JSON instance ID `api-566df6fbd9-xwbsd`, and matching `X-Instance-ID` response headers.
- Structured logs: PASS — Aggregator emitted `aggregator_started` with instance ID `aggregator-8cf7f9955-2b76l`. API emitted repeated structured `request_complete` entries for `/health` and `/ready` with instance ID `api-566df6fbd9-xwbsd`, HTTP status 200, and measured latency.
- Kafka baseline: PASS — consumer group `shipment-aggregator` was stable with one member and total lag zero. Delivery Base partition 0 remained at committed/log-end `442/442`; Logistic Centre partition 0 remained at `629/629`. Both partitions were assigned to the same Kubernetes Aggregator member `kafka-python-2.2.3-873fee4b-be2a-4de2-bd5c-8b2c06bbc764`.
- Baseline deployment status: In progress — Pod readiness, service health, structured logs, and Kafka membership are verified; controlled event processing, database state, and GraphQL flow remain to be checked.
- Screenshot evidence: `Screenshots/D-02A-baseline-deployments-pods-and-services-ready.png`, `Screenshots/D-02B-aggregator-health-and-readiness-instance-id.png`, `Screenshots/D-02C-api-health-and-readiness-instance-id.png`, `Screenshots/D-02D-baseline-structured-logs-and-instance-ids.png`, and `Screenshots/D-02E-baseline-kafka-consumer-group-and-zero-lag.png`. Preliminary preparation checks were not captured because they were not considered substantive thesis evidence.
- Anomalies or discarded attempts: The installed Redpanda `rpk` version did not provide `rpk redpanda config get`. A subsequent `rpk group describe` was accidentally run on the macOS host and failed because host `rpk` was not installed. The corrected container commands succeeded. `kubectl run` could not attach interactively to the short-lived health-check container and automatically fell back to streaming its logs; all four checks completed successfully and Kubernetes deleted the Pod.
