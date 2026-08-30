# Azure High-Availability Experimental Protocol

**Methodology version:** 1.0.6
**Status:** Frozen
**Frozen at:** 2026-08-30T09:52:12Z

Methodological changes after this point are prohibited unless pre-E1 validation discovers a genuine technical incompatibility. Any such change requires a versioned amendment and the reruns defined by this protocol.

**Version 1.0.1 compatibility amendment:** Pre-E1 IaC validation established that the AKS API origin is an HTTP `LoadBalancer` Service with no repository-managed public certificate or TLS ingress. Adding certificate/DNS infrastructure solely for this experiment would materially increase scope and complexity. External clients still use HTTPS to Azure Front Door, but Front Door forwards and probes the controlled AKS origin over HTTP port 80. Validation also found the originally drafted AKS `1.32.2` pin was out of standard support; the IaC now requests supported minor `1.35`, and pre-deployment validation must resolve and record one identical patch available in both regions before either cluster is created. No availability, recovery, workload, integrity, cost, or fault definition changed.

**Version 1.0.2 transport clarification:** E1, E2-A, E2-B, and F1 send the external availability probe directly to the Region A HTTP `LoadBalancer` application endpoint. G1 and G2 send the external probe over HTTPS to Azure Front Door, which forwards and probes the AKS origins over HTTP port 80. No TLS ingress, certificate manager, or experiment-only DNS/certificate infrastructure is introduced. All availability, recovery, workload, integrity, cost, and fault definitions remain unchanged. Because the direct and Front Door paths contain different routing and TLS components, latency comparisons must identify the path and must not attribute path-induced differences solely to the application topology.

**Version 1.0.3 pre-E1 quota amendment:** Subscription quota discovery immediately before deployment found a zero-vCPU quota for the DASv5 family in both planned regions, making the frozen `Standard_D2as_v5` application nodes undeployable. Both regions expose `Standard_D2as_v4` with the required two-vCPU size and a four-vCPU family quota. Before any experimental Azure resource was created or any E1 run began, every application pool was therefore changed to `Standard_D2as_v4`, and the current EUR burn estimate was regenerated. System-pool sizing, application-node counts, zones, scheduling, workloads, metrics, routing, probes, repeat counts, fault mechanisms, transaction/commit behaviour, idempotency and event-version semantics remain unchanged. All configurations use the amended application VM size so comparability is preserved.

**Version 1.0.4 pre-E1 cost-attribution amendment:** Final rendered-IaC review found that the parameter sets did not carry the protocol-required `run` tag, and the shared/Region B sets lacked an unambiguous configuration-series tag. Before any experimental Azure resource was created or E1 began, frozen resource-tag sets were added for shared, E1, E2, F1, Region B, G1 Front Door and G2 Front Door resources. Persistent resources use series labels rather than individual repeat IDs because they span warm-up and three measured runs. This amendment changes cost attribution metadata only; no infrastructure SKU, count, topology, zone, workload, timing, metric, routing, probe, failure or application semantic changed.

**Version 1.0.5 pre-E1 subscription-policy amendment:** The first shared deployment request was rejected before resource creation by the Azure for Students `Allowed resource deployment regions` policy, which permits only Italy North, Switzerland North, Spain Central, Norway East and France Central. Read-only compatibility checks found that Italy North and Norway East both support every required service, non-preview AKS `1.35.7`, the frozen B2s/D2as_v4 sizes, sufficient family/total quota and unrestricted zones 1/2/3. France Central and Spain Central had subscription-specific zone restrictions for frozen sizes; Switzerland North was technically valid but not selected. Region A is therefore amended to Italy North and Region B to Norway East, and their current EUR VM meters are used in a regenerated burn estimate. The direct-versus-Front-Door routing definitions, region roles, node sizes/counts/zones, workloads, timings, metrics, failure mechanisms and application semantics remain unchanged. The rejected West Europe deployment created only empty resource groups and no experimental service resources.

**Version 1.0.6 pre-E1 run-identity clarification:** Multi-day execution made the original date-bearing run-ID format incompatible with the requirement to broker-freeze every future run key before E1, because future execution dates are not yet known. Measured runs now use stable IDs `<configuration>-r<two-digit repeat>` and warm-ups use `<configuration>-warmup`; each run records its actual start/end UTC dates separately in primary evidence. The complete measured and warm-up ID sets are frozen before broker verification. This changes identifiers only and does not change key hashing, partitioning, workloads, counts, rates, timings, metrics or comparisons. Shared Azure services had been provisioned when this pre-E1 contradiction was resolved, but no key manifest, workload, AKS cluster or measured E1 run existed.

## 1. Scope and Freeze Rule

This protocol governs the comparison:

**Azure baseline → Pod replication → simulated Availability Zone failure → multi-region active-passive → multi-region active-active**

The comparative scope is application-layer availability and recovery of the Event Aggregation Service and GraphQL API. Azure Event Hubs and PostgreSQL are required supporting dependencies, but their own high-availability behaviour is outside the comparison. Conclusions are conditional on those dependencies remaining available.

The Event Aggregation Service is described as providing **at-least-once processing with an idempotent consumer**. It must never be described as exactly-once processing.

Before E1 begins, create `evidence/azure-experiment-freeze.json` containing the protocol version and Git commit, UTC freeze timestamp, Azure subscription/billing currency, selected regions, service SKUs, node-pool sizes/counts, Event Hubs settings, Front Door settings, fixed repeat count, external measurement-host configuration, and fault mechanisms. Metric definitions must not change between configurations. Any necessary amendment must be versioned and affected configurations rerun.

No Azure resources are created by this document.

## 2. Common Timeline

Use these labels where applicable:

| Timestamp | Meaning |
|---|---|
| T0 | Deployment stable: desired replicas Ready, dependencies reachable, consumer assignment recorded, and lag at baseline. |
| T1 | Probe logger and controlled event stream both running; fixed measurement window begins. |
| T2 | Fault-injection command/action initiated. |
| T3 | First observed user-facing service failure or first event-progress interruption. Record `none` if no impact is observed. |
| T4 | First successful user-facing probe after T2. |
| T5 | Sustained user-facing recovery confirmed. |
| T6 | Replacement capacity, readiness, routing, and consumer assignment stable. |
| T7 | Event backlog returned to zero or the defined steady-state threshold. |
| T8 | Final expected-event and materialised-state integrity checks completed. |

All clocks and outputs use UTC with millisecond precision where available. Timestamps come from the probe/workload host and are checked against Azure/Kubernetes timestamps before each run.

## 3. Metric Definitions

### 3.1 User-Facing Availability

**Availability for a measurement window:**

`successful service probes / total service probes`

Also report the percentage, total successes, total failures, longest consecutive failure sequence, and failure timestamps. Do not exclude failures during fault injection or recovery.

**Probe target**

- Send a `POST` to the user-facing `/graphql/` endpoint using the frozen transport for the configuration.
- E1, E2-A, E2-B, and F1 use HTTP to the direct Region A public `LoadBalancer` application endpoint.
- G1 and G2 use HTTPS from the external client to the Azure Front Door endpoint; Front Door forwards to the AKS origin over HTTP.
- Use a fixed canary shipment created and fully materialised before T0.
- Query:

```graphql
query AvailabilityProbe($shipmentId: String!) {
  shipment(shipmentId: $shipmentId) {
    shipmentId
    latestEventVersion
  }
}
```

The canary shipment is separate from the two changing workload shipments. This prevents processing lag from being misclassified as API unavailability.

**Probe interval and timeout**

- One probe every 1 second, scheduled from the intended start time rather than one second after the previous response.
- Connection timeout: 2 seconds.
- Total request timeout: 5 seconds.
- Record start time, finish time, latency in milliseconds, HTTP status, returned instance/region header, validation result, and error category in CSV.

**Successful probe**

A probe succeeds only when all conditions hold:

- DNS, TLS, connection, and response complete within 5 seconds;
- HTTP status is 200;
- response is valid JSON with no GraphQL `errors`;
- `shipment` is non-null;
- returned shipment ID and fixed canary version match the expected values.

**Failed probe**

Timeouts, DNS/TLS/connection errors, non-200 responses, malformed JSON, GraphQL errors, null shipment data, or incorrect canary values are failures. Record the reason; do not silently retry or replace the sample.

**Measurement window**

- Use one discarded warm-up run per configuration followed by the fixed number of measured runs recorded in `evidence/azure-experiment-freeze.json`.
- Select that repeat count before deployment only after estimating the hourly Azure burn rate and total experimental cost. Use the same repeat count for every comparable E1, E2-A, E2-B, F1, G1, and G2 configuration.
- If the budget later requires a different repeat count, stop measured execution and issue a documented, versioned protocol amendment. Do not change counts ad hoc; identify and rerun any configurations required to restore a comparable dataset.
- Each measured window is fixed at 10 minutes for comparability.
- T1 occurs after at least 60 consecutive successful baseline probes, stable consumer assignment, and baseline lag confirmation.
- For fault tests, inject the fault at `T1 + 60 seconds`.
- End the availability window at `T1 + 600 seconds`, regardless of recovery time.
- If service has not recovered by window end, report recovery as right-censored (`>540 seconds after T2`) and continue diagnostic/data-integrity observation for up to 15 additional minutes.
- E1 has no fault injection; its full 10-minute window measures normal cloud availability.

**External probe/workload host**

- Run the GraphQL availability probe, controlled Kafka publisher, workload-freshness queries, and timeline logger from one fixed external laptop outside Azure and outside both AKS clusters.
- Reuse the same physical laptop, operating system, power arrangement, wired network connection where available, internet connection/public-egress arrangement, DNS configuration, and tool/container versions for every warm-up and measured run. Connect mains power, disable sleep, VPN/proxy changes, Wi-Fi roaming where a wired connection is used, and unrelated workloads during each window.
- Before every run, record UTC/NTP synchronisation, host identity, OS/kernel, tool versions, power state, network interface/link state, public egress identity in sanitised form, DNS resolver, and basic reachability to Front Door and Event Hubs.
- Treat this host and public-internet path as a controlled experimental parameter, not part of the system under test. A laptop, physical location, ISP, connection type, or network-arrangement change requires a protocol amendment before further comparable measurements.

### 3.2 Recovery Times

**Sustained user-facing service recovery** means five consecutive successful 1-second GraphQL probes after T2. A single successful response does not establish recovery.

Record separately:

| Metric | Definition |
|---|---|
| First service success | `T4 - T2`, where T4 is the first successful probe after T2. |
| Sustained service recovery | Timestamp of the first probe in the first five-success sequence minus T2. T5 is the fifth probe that confirms the sequence. |
| Pod/capacity replacement time | Fault injection to the required replacement Pod/node capacity becoming Kubernetes Ready. Record scheduling, container start, and Ready timestamps separately where available. |
| Routing recovery time | Fault injection to Front Door or regional Service consistently routing valid probes to healthy capacity. Use the same five-success rule. |
| First event-processing recovery | T2 to the first post-fault controlled event committed to PostgreSQL with observable consumer progress. |
| Sustained event-processing recovery | T2 to the first of three consecutive 5-second progress samples showing committed offset advancement or backlog reduction without a processing error. |

These metrics are not interchangeable. Report all applicable values even when user-facing service remains available throughout and T3 is `none`.

### 3.3 Consumer Progress and Backlog

Sample every 5 seconds for every Event Hub/topic partition:

- UTC sample timestamp;
- topic/Event Hub and partition;
- committed consumer-group offset;
- log-end/equivalent Event Hubs progress;
- partition lag and total lag;
- consumer member/client identity and actual partition assignment where available.

Definitions:

- **Lag before failure:** last complete total-lag sample before T2.
- **Maximum lag:** maximum observed total lag from T2 until T7.
- **Backlog recovery:** first of three consecutive 5-second samples at total lag zero.
- If baseline cannot remain at zero under the fixed workload, freeze a steady-state threshold before measured runs as `baseline p95 lag + 1 event`; T7 is the first of three samples at or below that threshold.
- **Backlog recovery time:** `T7 - T2`.
- **Eventually processed:** all expected event IDs persist and final consumer lag is zero/steady state within the 15-minute post-window observation limit.

For G2, record actual partition assignments before, during, and after failure. Do not claim every Aggregator Pod or region actively processes events unless assignment evidence proves it.

#### Consumer-progress collector implementation

Do not use `rpk` as the Azure measurement dependency. Before E1, implement one reusable read-only Python script at `scripts/experiments/kafka_consumer_progress.py` using the same pinned `kafka-python-ng` version as the application.

The collector must:

- accept bootstrap servers, group ID, topics, sample interval, output paths, and Kafka security settings through arguments/environment variables;
- use `PLAINTEXT` for local Redpanda and Event Hubs bootstrap `<namespace>.servicebus.windows.net:9093` with `SASL_SSL`/`PLAIN`, username `$ConnectionString`, and the namespace connection string supplied as the password only through an environment variable or mounted secret and never written to output;
- discover every `TopicPartition` for the configured topics;
- call Kafka offset APIs to read the group's committed offset and each partition's end offset without subscribing, polling application records, joining as an active consumer, or committing offsets;
- calculate `lag = max(0, end_offset - committed_offset)` only when both offsets are available; record null plus a reason when no committed offset exists;
- write one long-form CSV row per topic/partition/sample and a total-lag row every 5 seconds;
- attempt Kafka consumer-group description for member/client/host assignment data and write assignment snapshots to JSONL;
- mark assignment as unavailable, rather than failing the offset sample, if Event Hubs does not expose sufficient group-description detail.

Required CSV fields are:

`sample_timestamp_utc, group_id, topic, partition, committed_offset, end_offset, lag, total_lag, assignment_source, collector_error`

Required assignment JSONL fields are:

`sample_timestamp_utc, group_id, member_id, client_id, host, instance_id, region, assignments, source`

Before E1:

1. Test the collector against local Redpanda with a known produced/consumed event count.
2. Compare its committed offsets, end offsets, and lag with local `rpk group describe` output as validation only.
3. Test the same collector against an Event Hubs smoke workload and confirm offset arithmetic using known accepted event counts.
4. Determine whether Event Hubs returns usable group-member assignments through the Kafka admin API.

Because assignment detail may be incomplete, add fixed pre-E1 observability to the Aggregator using a Kafka consumer rebalance listener. It must emit structured `partitions_assigned` and `partitions_revoked` logs containing Pod/instance ID, Azure region, topic, and partition. This is measurement instrumentation only; it must not change transaction, commit, failure, idempotency, or retry semantics. Those logs are the assignment authority when the external collector cannot retrieve member assignments.

### 3.4 Data Integrity and Materialised State

For every measured run calculate:

| Metric | Calculation / expected value |
|---|---|
| Expected events | Number successfully accepted by the controlled publisher across both run shipments; normally 600 total and 300 per shipment. |
| Persisted unique event IDs | `COUNT(DISTINCT event_id)` across the two run shipment IDs. |
| Missing events | Expected event-ID set minus persisted event-ID set. |
| Duplicate historical rows | `COUNT(*) - COUNT(DISTINCT event_id)` and an explicit grouped duplicate query. Expected 0. |
| Highest expected version | Highest successfully published version per shipment; normally 300 for each shipment. |
| Materialised version | Each run shipment's `current_shipment_state.latest_event_version`. Expected to equal that shipment's highest expected version. |
| Stale state | Either materialised version is lower than its shipment's highest expected version after T7/T8. |
| Incorrect state | Either shipment's version or state fields do not match its highest-version controlled event. |

Final PASS requires no missing controlled events, no duplicate historical rows, correct materialised state, and eventual zero/steady-state lag. Redelivery is permitted by the at-least-once model; database idempotency must absorb it.

### 3.5 Latency (Secondary Metric)

From successful availability probes report p50, p95, p99, and maximum response latency for the fixed window. Failed probes remain availability failures and are not assigned artificial latency values. Latency is secondary to availability and recovery.

Always label latency results with the routing path. E1/E2-A/E2-B/F1 measure the direct external-host-to-Region-A HTTP path, while G1/G2 include external HTTPS termination and routing at Azure Front Door plus the HTTP origin hop. Preserve the same latency calculation, probe cadence, and timeout definitions, but do not interpret differences between these paths as application-topology effects alone.

## 4. Azure Test Matrix

Supporting Event Hubs and PostgreSQL remain as constant as practical and outside the comparative HA scope.

| ID | Configuration | Application topology | Controlled change/fault | Goal |
|---|---|---|---|---|
| E1 | Azure baseline | One Region; one AKS cluster; one Aggregator Pod; one API Pod; no deliberate AZ distribution; Event Hubs Kafka interface; PostgreSQL dependency. | No failure during the measured baseline window. | Prove cloud end-to-end operation before HA features. |
| E2-A | Aggregator Pod replication/failure | Same Region and cluster; two Aggregator replicas; two API replicas; same dependencies. | Delete the active Aggregator Pod while probes and the controlled event stream run. | Verify Azure Pod replacement, consumer reassignment, backlog recovery, and final integrity without repeating all local correctness tests. |
| E2-B | GraphQL API Pod replication/failure | Same E2 topology. | Delete one API Pod while the GraphQL probe stream runs. | Verify uninterrupted/recovered user-facing service and routing to the replacement. |
| F1 | Availability Zone resilience | Region A; two zone-aligned application user node pools; two Aggregator and two API replicas distributed across zones. | Stop one zone-aligned application user node pool with `az aks nodepool stop`. | Measure a **simulated zonal failure**. Do not claim an Azure Availability Zone failed. |
| G1 | Multi-region active-passive | Region A/Cluster A active with two Aggregator and two API replicas; Region B/Cluster B running with stopped application capacity; Front Door priority routing. | Stop all Region A application user-node-pool capacity, then start Region B's application user node pool. | Measure a **simulated regional/application failure**, including the explicit manual activation action and routing recovery. |
| G2 | Multi-region active-active | Both regions operational with two Aggregator and two API replicas per cluster; GraphQL origins healthy in Front Door; all Aggregators use the same Event Hubs consumer group. | Stop the same Region A application user-node-pool capacity while Region B remains active. | Compare active-active continuity and consumer reassignment with G1. Record actual assignments. |

G1/G2 stop Region A application capacity so its still-enabled Front Door origin becomes unhealthy; they do not disable the origin and do not represent an actual Azure regional outage.

### 4.1 G1 Standby State — Proposed Freeze Decision

The proposed G1 freeze is a **running cluster with stopped application-capacity standby** in Region B:

- Cluster B control plane and minimum system node pool remain running.
- A dedicated user node pool for the Aggregator and API is created, labelled/tainted for application workloads, and stopped with `az aks nodepool stop` before T0.
- Aggregator and API Deployments, Services, configuration, secrets, probes, and desired replica counts are already applied. Their Pods remain Pending while the application pool is stopped because they cannot schedule on the system pool.
- The Region B Front Door origin exists, is enabled at lower priority, and is expected to be unhealthy until the API becomes Ready.
- Region A is the priority-1 healthy origin; Region B is priority 2.

After the Region A fault at T2, the single planned manual activation action is `az aks nodepool start` for Region B's application pool. Desired Pods then schedule automatically, and Front Door routes automatically when its probes mark Region B healthy. Record any unplanned additional operator action separately.

Implications:

- **Recovery:** includes node-pool allocation/start, node Ready, image pull, Pod scheduling/readiness, Front Door health detection, and five-probe sustained service recovery. It is expected to be slower than G2.
- **Cost:** saves Region B application-node compute while retaining system-pool, control-plane tier, disks, load-balancer/public-IP, monitoring, and Front Door-origin costs. Record stopped-pool storage/network charges and running system-pool cost.
- **Manual complexity:** one planned activation action plus observation. Front Door routing is automatic after the origin becomes healthy; manual routing is not part of the nominal G1 path.

This is a concrete cold-compute standby, not an ambiguous warm application deployment.

### 4.2 F1 Fault Injection — Proposed Freeze Decision

Create two dedicated zone-aligned AKS **user** node pools, one pinned to Zone 1 and one to Zone 2. Keep system workloads on a separate system pool and prevent thesis application Pods from scheduling there. AKS node-pool stop cannot be used for a system pool or with Node Autoprovisioning, so F1 must use user pools and must not enable Node Autoprovisioning.

Primary F1 fault action:

```bash
az aks nodepool stop \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --cluster-name "$AKS_CLUSTER_NAME" \
  --nodepool-name "$FAILED_ZONE_POOL" \
  --no-wait
```

Do not cordon/drain as the measured primary fault and do not manually deallocate the underlying VM scale set. `az aks nodepool stop` is the supported AKS control-plane operation. Cordon/drain may be retained only as an unmeasured recovery/safety procedure if the stop operation cannot be used.

Record separate timestamps:

- **F1-T2-command:** immediately before invoking `az aks nodepool stop`.
- **F1-T2-accepted:** Azure CLI command return/operation-accepted timestamp.
- **F1-T2-node-unavailable:** first 1-second poll where any node in the target pool disappears or has `Ready != True`.
- **F1-T2-pool-stopped:** first poll where the AKS node-pool power state reports stopped.
- Common T3 remains the first user-facing service failure or event-progress interruption; it must not be replaced by the node timestamp.

Poll both AKS power state and Kubernetes node conditions from before F1-T2-command until the pool is stopped. Start the pool after the measured window and record equivalent start, node Ready, Pod redistribution, and T6 timestamps.

This is a **simulated zonal failure** produced by stopping all thesis application capacity in one zone. It is not evidence that an Azure Availability Zone failed, and the managed stop sequence may differ from an abrupt physical outage.

### 4.3 F1 Topology Behaviour — Proposed Freeze Decision

Replacement Pods are **allowed to schedule in the surviving zone**. This best matches the thesis objective of evaluating service continuity when one zone's application capacity is unavailable. Keeping replacements Pending would test strict placement preservation rather than availability.

Apply the following constraint independently to the Aggregator and API Deployments, with the appropriate `app` label selector:

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app: aggregator # use app: api for the API Deployment
```

Also use node affinity/selectors that allow both zone-aligned application pools but exclude the system pool, and preferred (not required) hostname anti-affinity. A PodDisruptionBudget with `minAvailable: 1` is recommended for each application.

Trade-off:

- At T0, `maxSkew: 1` makes an even one-Pod-per-zone layout the scheduler preference and this distribution must be verified before every run.
- During F1, `ScheduleAnyway` permits replacement capacity to co-locate in the surviving zone, restoring replica count and service capacity.
- Zone redundancy is temporarily lost until the stopped pool returns.
- `DoNotSchedule` is rejected for this experiment because it could intentionally leave replacement Pods Pending and conflate placement strictness with application recovery.

### 4.4 Event Hubs Partitions and Assignment — Proposed Freeze Decision

- Create exactly one Event Hubs namespace containing two Event Hub entities, one for each existing domain/topic. Do not create one namespace per domain.
- Create each Event Hub with exactly **two partitions**, giving four partitions across the subscribed topics.
- Use Event Hubs Standard and set the partition count when the Event Hubs are created; Standard partition count is immutable.
- Keep the same topic names, partition count, group ID, key strategy, and assignment strategy across E1, E2-A, E2-B, F1, G1, and G2.
- Preserve shipment ID as the Kafka key so events for one shipment remain on one partition within each Event Hub.
- Preselect two unique controlled shipment IDs/keys for every planned measured run before the first E1 T0. For each run, one key must map to Partition 0 and the other to Partition 1 in both Event Hubs, and both keys must publish events to both Event Hubs.
- Freeze the complete broker-verified key manifest in `evidence/partition-key-map.json` before E1. The key set is immutable after E1 begins; the partition count, Kafka producer partitioner, key-selection method, and consumer assignment strategy remain unchanged across every measured E1, E2-A, E2-B, F1, G1, and G2 run.

Change the current implicit range strategy to an explicit `RoundRobinPartitionAssignor` **before E1**, then keep it unchanged through G2. This pre-experiment configuration change is recommended because all Aggregators subscribe to the same two topics: with four total partitions and four G2 consumers, round-robin assignment with identical subscriptions should allocate one partition to each consumer. The existing range strategy operates per topic and could leave two of the four G2 consumers idle even when all four partitions carry traffic. This changes assignment distribution only; it must not alter manual offset commits, database transaction ordering, fail-on-processing-error behaviour, idempotency, or stale-state protection.

The fixed `kafka-python-ng` configuration is:

```python
from kafka.coordinator.assignors.roundrobin import RoundRobinPartitionAssignor

KafkaConsumer(
    ...,
    partition_assignment_strategy=[RoundRobinPartitionAssignor],
)
```

Expected assignment characteristics:

- E1: the single Aggregator can own all four partitions.
- E2-A/F1: two Aggregators should receive two partitions each.
- E2-B: Aggregator membership and assignment should remain unchanged while the API Pod fails.
- G1 standby: Region A owns assignments while Region B application capacity is stopped; Region B receives assignments only after activation/rebalance.
- G2: four Aggregators join one group and should receive one partition each. Because both workload keys send to both Event Hubs, every assigned partition should carry controlled traffic and both regions should perform useful Aggregator work before the fault.

Round-robin assignment is not region-aware and does not promise equal event counts per region. Every run must record actual assignment and per-instance processing from structured logs and the external collector. Do not claim both regions processed simultaneously unless that evidence confirms it.

### 4.5 G1/G2 Region A Failure Mechanism — Proposed Freeze Decision

Use one identical Region A application-capacity fault for G1 and G2. Region A's Aggregator and API Pods must have required scheduling rules that permit only the frozen Region A application user node pools and exclude the system pool.

At T2, one version-controlled fault script records the command timestamp and issues `az aks nodepool stop --no-wait` for every Region A application user pool in the fixed order recorded in `evidence/azure-experiment-freeze.json`. Record each operation-accepted timestamp, first Region A application node with `Ready != True`, all affected Pod transitions, and the first time all target pools report stopped.

Do not disable, remove, reprioritise, or reconfigure the Region A Front Door origin during either measured fault. Front Door must detect the unavailable Region A API through its frozen health probes:

- In G1, after the identical Region A stop commands are accepted, record the separate planned manual `az aks nodepool start` activation of Region B's application user pool.
- In G2, Region B application capacity is already running and no standby activation action occurs.

Restore Region A by starting the same application pools only after the measured window, unless safety requires earlier recovery; record any deviation and invalidate the run if it changes the measured fault.

### 4.6 Azure Front Door Parameters — Frozen Decision

Use Azure Front Door Standard with one origin group and freeze these settings for G1 and G2:

| Parameter | Frozen value |
|---|---|
| Health probe | Enabled |
| Probe protocol | HTTP |
| Probe request method | GET |
| Probe path | `/ready` |
| Probe interval | 10 seconds |
| Health sample size | 4 |
| Successful samples required | 3 |
| Additional latency sensitivity | 1000 milliseconds |
| Session affinity | Disabled |
| Origin HTTP port | 80 |
| Route forwarding protocol | HTTP only from Front Door to origin |
| Client protocol | HTTPS to Azure Front Door |
| Origin certificate-name validation | Not applicable to the HTTP origin connection |
| Origin weight | 1000 for each origin |
| GraphQL route caching | Disabled |

Source inspection and route introspection of the built API image show `/ready` registers only `GET`, not HEAD, so Front Door must use GET. A probe is healthy only on HTTP 200; the API returns 503 when its database readiness check fails. With a four-sample window requiring three successes, an origin becomes unhealthy when fewer than three of its last four samples succeed. Front Door probing is distributed, so the 10-second interval does not imply one globally exact failover time; retain observed Front Door health and external-probe timestamps.

Origin routing differs only where the compared topology requires it:

- G1: Region A priority 1 and Region B priority 2.
- G2: Region A and Region B both priority 1 with equal weight 1000. The 1000-millisecond additional-latency setting is intended to keep both healthy origins eligible for the controlled client location; actual returned region/instance headers remain the evidence.

Keep both origins enabled throughout G1 and G2. Freeze the Front Door profile tier, endpoint, route, origin host headers/ports, priorities, weights, health-probe settings, load-balancing settings, session-affinity state, and caching state in `evidence/azure-experiment-freeze.json` and export the effective configuration before each run.

## 5. Common Controlled Workload

Use the same workload implementation and rates across E1, E2-A, E2-B, F1, G1, and G2 unless a documented technical constraint requires a protocol amendment.

### 5.1 IDs and Event Design

- Measured run ID: `<configuration>-r<two-digit repeat>`, for example `F1-r02`. Warm-up ID: `<configuration>-warmup`. Record the actual execution UTC date and timestamps separately in the run timeline rather than embedding an unknowable future date in the pre-frozen key identity.
- Workload shipment IDs/Kafka keys: two unique values for each measured run, for example `AZ-<configuration>-R<repeat>-A-<candidate>` and `AZ-<configuration>-R<repeat>-B-<candidate>`.
- Event IDs: `az-<configuration>-r<repeat>-evt-0001` through `...-0600`.
- Event versions: independent integers 1 through 300 for each run-unique workload shipment, with no intentional gaps.
- Use a deterministic four-event cycle that sends each shipment to both Event Hubs, for example A/Logistic Centre, B/Logistic Centre, A/Delivery Base, B/Delivery Base, while incrementing each shipment's version on every event for that shipment.
- Use `shipment_id` as the Kafka key for every event.
- During protocol preparation, enumerate every planned configuration/repeat and use the pinned Kafka producer's actual partitioner with partition metadata `[0, 1]` to choose unique candidate shipment IDs that map A and B to different partitions. Do not choose explicit partition IDs in the measured producer.
- Broker-verify the full candidate set before E1 using a temporary two-partition verification Event Hub and the same Kafka producer version/configuration. The verification Event Hub is not part of a measured configuration and must be deleted before E1. Because Kafka producer partition selection is client-side for the fixed key and partition metadata, the mapping applies to both final two-partition Event Hubs.
- Save one row/object per key in `evidence/partition-key-map.json` with `run_id`, `shipment_id`, `key_role`, `expected_partition`, `observed_partition`, verification Event Hub, acknowledged offset/timestamp, producer version, partitioner, and verification result. Do not store credentials.
- Before every measured T0, verify that both final Event Hubs still expose exactly partitions `[0, 1]`, the pinned local partitioner calculation matches the frozen manifest, and the run's two keys are unused in PostgreSQL. The first measured acknowledgements must confirm the expected partitions in both Event Hubs; otherwise invalidate the run.
- If any candidate mapping fails, correct and reverify the complete manifest before E1. Any key-manifest, partitioning, or assignment-strategy change after E1 requires a protocol amendment and rerunning all affected configurations.
- Use deterministic event types, locations, and details containing configuration/run/sequence.
- Save the exact expected event set before publishing.

### 5.2 Rate and Duration

- Publish 600 events at 1 event per second during the 10-minute measurement window.
- Start publishing at T1; inject faults at T1 + 60 seconds.
- Use the pre-frozen pair of unique keys assigned to that run, plus the same event cycle, `shipment_id` key strategy, producer partitioner, configured partition count, and consumer assignment strategy in every configuration and repeat.
- Record publisher acknowledgement, topic/partition, offset where available, and timestamp for every event.
- Continue 1-second canary GraphQL availability probes concurrently.
- Query both changing workload shipments every 5 seconds as a separate freshness/progress series; do not use them as the availability numerator.

The expected measured distribution is 150 controlled events per Event Hub partition, 300 events per shipment, and 600 events total per run. This workload preserves per-shipment order within each Event Hub, exercises every partition, is long enough to expose interruption/backlog, and has negligible Event Hubs volume relative to infrastructure cost. Cross-Event-Hub arrival order is not assumed; `event_version` remains the authority for materialised-state progression.

## 6. Complexity Rubric

Report the following objective counts for each configuration:

1. AKS clusters.
2. AKS node pools.
3. Desired application replicas (Aggregator + API).
4. Azure regions.
5. Availability Zones explicitly configured for application capacity.
6. Front Door/routing rules and origin configurations.
7. Kubernetes application/configuration objects applied.
8. Manual failover actions required during the measured run.
9. Numbered operator-runbook steps from deployment start to verified stable state.

A runbook step is one operator decision/action; commands executed inside one automated script count as one step. Validation-only observations are recorded but do not count as manual failover actions.

Report the nine-value vector. A coarse **complexity index** may also be reported as the unweighted sum of these counts. The raw vector remains authoritative because the unweighted index deliberately does not claim that all factors have equal operational impact.

## 7. Cost Measurement

### 7.1 Cost Window and Evidence

For each configuration record:

- resource creation/start timestamp;
- measurement-window timestamps;
- resource deletion/deallocation timestamp;
- Azure resource IDs, region, SKU, quantity, tags, and resource group;
- actual Azure Cost Management cost in the subscription billing currency once available;
- credits/discounts separately from gross consumption where the billing view permits.

Tag resources with at least `project=masters-thesis`, `phase`, `configuration`, `run`, and `owner`.

### 7.2 Cost Categories

Record contributions from:

- AKS node VMs/VM scale sets, managed disks, load balancers, and public IPs;
- Azure Container Registry storage/build activity;
- Azure Event Hubs namespace/capacity/throughput;
- PostgreSQL compute/storage/backup;
- Azure Front Door, requests, rules, and data transfer;
- Azure Monitor/Log Analytics ingestion and retention;
- network egress and any other metered supporting resource.

Separate:

- **application HA cost**, which changes across E1–G2; and
- **shared supporting-dependency cost**, which is reported but excluded from claims about the relative HA topology where it remains constant.

Prefer actual expenditure. If configurations run for different durations, report actual cost and an observed cost-per-resource-hour or cost-per-test-hour derived from the same billed period. Do not fabricate monthly or annual values from short-lived experiments. Note Cost Management reporting delay and preserve resource inventory/timestamps before teardown so delayed charges can still be attributed.

AKS Free tier may be used to avoid control-plane charges where appropriate, but no financially backed AKS SLA may be claimed for the Free tier.

## 8. Evidence Layout

Do not store credentials, connection strings, access tokens, or unredacted subscription identifiers in evidence.

Before E1, create `evidence/azure-experiment-freeze.json` from the reviewed protocol and deployment parameters. It must contain:

- `protocol`: version `1.0.6`, the Git commit containing the frozen protocol, and UTC freeze timestamp;
- `billing`: sanitised subscription reference, billing currency, estimated hourly burn by configuration, total planned burn, and budget ceiling;
- `regions`: Region A and Region B, plus the sanitised physical location of the external laptop;
- `resource_tags`: the frozen project, phase, configuration-series, run-series, owner and applicable region-role tags used for cost attribution;
- `run_identity`: the stable format and complete measured/warm-up run-ID sets whose keys are broker-verified before E1, with execution UTC recorded separately;
- `skus`: Front Door/Event Hubs/AKS/PostgreSQL tiers and every cluster, node-pool, VM size, mode, zone, and desired/min/max node count;
- `event_hubs`: namespace tier, entity names, two partitions per entity, retention, consumer group, producer/client version, producer partitioner, and `RoundRobinPartitionAssignor`;
- `front_door`: profile tier, endpoint/route, origin names/host headers/ports, priorities, weights, HTTP GET `/ready` to origin, HTTPS client endpoint, 10-second interval, sample size 4, successful samples 3, 1000-millisecond additional latency, disabled session affinity, non-applicable HTTP-origin certificate-name validation, and disabled GraphQL caching;
- `probe_transport`: direct Region A HTTP for E1/E2-A/E2-B/F1 and external HTTPS to Front Door with an HTTP AKS origin hop for G1/G2;
- `repeat_count`: the fixed measured-run count selected from the recorded burn estimate and used for every comparable configuration;
- `fault_mechanisms`: F1's single zone-aligned user-pool stop and the ordered Region A application-pool list/script used identically by G1 and G2, plus G1's separate Region B activation action;
- `external_host`: stable laptop ID, sanitised physical location, OS/kernel, tool/container versions, mains-power/sleep state, wired/Wi-Fi connection state, ISP/public-egress arrangement, DNS configuration, time synchronisation, and VPN/proxy state.

Validate the JSON against the rendered IaC parameters and save its SHA-256 checksum before deployment. Any post-freeze value change requires a versioned protocol amendment; do not edit the file silently.

The canonical, complete pre-E1 key manifest is `evidence/partition-key-map.json`. Each run also retains an identical copy or checksum-addressed reference so its two assigned keys and observed partitions are directly auditable.

### `evidence/05-azure-baseline/`

```text
commands.md
results.md
config/
  resource-inventory-sanitised.json
  effective-kubernetes-objects.yaml
  front-door-or-endpoint-config-sanitised.json
raw/
  E1-single-replica/run-01/
    timeline.csv
    probes.csv
    workload-progress.csv
    consumer-progress.csv
    consumer-assignments.jsonl
    partition-key-map.json
    expected-events.jsonl
    published-events.csv
    database-integrity.csv
    application-logs.jsonl
  E2-A-aggregator-pod-failure/run-01/
    (same files)
    kubernetes-events.txt
  E2-B-graphql-api-pod-failure/run-01/
    (same files)
    kubernetes-events.txt
cost/
  E1-cost-window.md
  E1-resource-inventory.csv
  E1-actual-cost.csv
  E2-A-cost-window.md
  E2-A-resource-inventory.csv
  E2-A-actual-cost.csv
  E2-B-cost-window.md
  E2-B-resource-inventory.csv
  E2-B-actual-cost.csv
Screenshots/
```

### `evidence/06-azure-az/`

```text
commands.md
results.md
config/
  resource-inventory-sanitised.json
  node-pool-zone-layout.json
  scheduling-and-topology.yaml
raw/F1-simulated-zonal-failure/run-01/
  timeline.csv
  probes.csv
  workload-progress.csv
  consumer-progress.csv
  consumer-assignments.jsonl
  partition-key-map.json
  expected-events.jsonl
  published-events.csv
  database-integrity.csv
  nodepool-power-state.csv
  node-availability.csv
  pod-placement.csv
  kubernetes-events.txt
  application-logs.jsonl
cost/
  F1-cost-window.md
  F1-resource-inventory.csv
  F1-actual-cost.csv
Screenshots/
```

### `evidence/07-azure-region/`

```text
commands.md
results.md
config/
  region-a-inventory-sanitised.json
  region-b-inventory-sanitised.json
  front-door-config-sanitised.json
raw/G1-active-passive/run-01/
  timeline.csv
  probes.csv
  workload-progress.csv
  consumer-progress.csv
  consumer-assignments.jsonl
  partition-key-map.json
  expected-events.jsonl
  published-events.csv
  database-integrity.csv
  front-door-health.csv
  region-a-nodepool-power-state.csv
  region-a-node-availability.csv
  pod-placement.csv
  standby-activation.csv
  kubernetes-events.txt
  application-logs.jsonl
raw/G2-active-active/run-01/
  timeline.csv
  probes.csv
  workload-progress.csv
  consumer-progress.csv
  consumer-assignments.jsonl
  partition-key-map.json
  expected-events.jsonl
  published-events.csv
  database-integrity.csv
  front-door-health.csv
  region-a-nodepool-power-state.csv
  region-a-node-availability.csv
  pod-placement.csv
  kubernetes-events.txt
  application-logs.jsonl
cost/
  G1-cost-window.md
  G1-resource-inventory.csv
  G1-actual-cost.csv
  G2-cost-window.md
  G2-resource-inventory.csv
  G2-actual-cost.csv
Screenshots/
```

Create `run-01` through `run-N`, where `N` is the fixed `repeat_count` in `evidence/azure-experiment-freeze.json`. Keep raw CSV/JSONL as primary evidence and capture only selected screenshots showing topology, fault timing, replacement/routing, peak lag, final integrity, and actual cost. Do not screenshot every command.

Each `results.md` must include the common table:

`Test | Purpose | Expected Result | Observed Result | PASS/FAIL | Evidence`

Results are written only after observation.

## 9. Cost-Controlled Deployment and Teardown

1. Rehearse scripts, manifest rendering, workload generation, parsing, and evidence paths locally.
2. Use one reusable IaC approach and parameter sets; do not create resources manually unless the action is itself measured.
3. Create only the configuration currently under test. Use small suitable node sizes and avoid Premium tiers unless a measured requirement proves they are necessary.
4. Prefer Event Hubs Standard, Azure Front Door Standard, economical PostgreSQL compute, and AKS Free management tier if they satisfy the prototype requirements.
5. Reuse Region A, ACR, Event Hubs, PostgreSQL, and monitoring across E1/E2-A/E2-B/F1 where technically valid. Add/remove only the node pools and scheduling configuration needed for F1.
6. Add Region B only after F1 evidence is complete. Reuse the two-region deployment when moving from G1 to G2.
7. Set an Azure Budget and alerts before deployment. Estimate the hourly and total burn for every configuration, select the fixed repeat count, and record both in `evidence/azure-experiment-freeze.json` before creating clusters.
8. Keep Log Analytics retention and diagnostic categories minimal but sufficient for the defined metrics.
9. After each configuration, export raw evidence, sanitised configuration, resource inventory, timestamps, and preliminary cost data to the local repository before mutation/teardown.
10. Delete/deallocate expensive resources immediately after evidence is safely local. Do not wait for delayed Cost Management data; preserve resource IDs/tags so costs can be attributed later.
11. Delete Region B first after G2, then Region A application resources, then shared dependencies and ACR after confirming no further runs are required.
12. Verify resource groups are empty/deleted and record teardown completion. Cost evidence remains available through Azure billing after resource deletion.

AKS, Front Door, Event Hubs, PostgreSQL, and registry creation/deletion times must be recorded. Evidence must never exist only inside a resource group scheduled for deletion.

## 10. Proposed Azure Implementation Sequence

The proposed order is:

1. Estimate Azure burn, select the fixed repeat count, freeze protocol v1.0.6 and all required parameters, and create/checksum `evidence/azure-experiment-freeze.json` before deployment.
2. Prepare reusable IaC and parameter files for E1, E2-A, E2-B, F1, G1, and G2; validate locally without deployment.
3. Prepare and locally verify probe, workload, consumer-progress, integrity, timeline, sanitisation, and evidence-export scripts. Validate the consumer-progress collector against local Redpanda and then an Event Hubs smoke workload; preselect and broker-verify every measured run's unique key pair, save the complete `evidence/partition-key-map.json`, and remove the temporary verification Event Hub before any measured E1 run.
4. Configure only `RoundRobinPartitionAssignor`, add the fixed assignment/revocation structured logs, and verify locally that assignment changes do not alter event-processing semantics. Freeze this configuration before E1.
5. Build application images locally, scan/smoke-test them, create ACR, push immutable commit-tagged images, and record digests.
6. Deploy shared supporting dependencies and Region A E1 application resources.
7. Verify E1 end-to-end, run the warm-up, then measured baseline runs.
8. Scale/reconfigure the same cluster for E2; verify actual consumer assignment, run E2-A Aggregator Pod failure, then run E2-B GraphQL API Pod failure as a separate reported test.
9. Add zone-aligned application user pools and the proposed topology rules for F1; verify one application replica per zone before each simulated zonal-failure run.
10. Run F1 with `az aks nodepool stop`, recording command, operation-accepted, first node-unavailable, and pool-stopped timestamps separately.
11. Save E1/E2-A/E2-B/F1 evidence and cost inventories; remove unnecessary zone capacity.
12. Add Region B and Front Door; apply and verify the defined G1 stopped-application-capacity standby and frozen Front Door settings.
13. Run G1 with the frozen Region A application-pool stop script and record Region B's node-pool start as the separate planned manual activation action.
14. Reconfigure the same two regions for G2 active-active; retain the same Front Door health/load-balancing parameters and Region A fault script, verify both APIs and actual Event Hubs partition assignments without assuming both regions consume simultaneously.
15. Run G2 measurements.
16. Export/sanitise all evidence, actual available costs, resource inventories, and final configuration.
17. Tear down in the defined order and record deletion completion.
18. Retrieve delayed actual Cost Management data later without recreating resources.

Azure DevOps and self-hosted agents are excluded. The repository remains in GitHub. GitHub Actions is optional later and is not required for this experimental sequence.

## 11. Risks and Dissertation Assumptions

- Failures are controlled simulations. F1 is not an actual Availability Zone outage; G1/G2 are not actual Azure regional outages.
- Docker Desktop results and Azure results use the same application semantics but different infrastructure and networking paths.
- PostgreSQL and Event Hubs availability are assumed during application HA tests; failures in those services invalidate the run rather than measure the tested topology.
- Shared cross-region dependencies may add latency or become a common dependency; this must be stated when interpreting regional results.
- Event Hubs partition count limits active consumers. Replica count does not prove simultaneous consumption; actual assignment is evidence.
- Front Door health-probe timing, sample window, origin settings, latency sensitivity, connection behaviour, and client location influence measured recovery. Use only the frozen settings and retain effective configuration evidence.
- `az aks nodepool stop` is a supported managed operation, but its shutdown sequence may differ from an abrupt physical zone outage; F1 remains a simulated zonal failure.
- Standard-tier Event Hubs partition counts cannot be changed after creation. Incorrect provisioning requires replacement before E1, not an in-series change.
- Round-robin assignment should give each of four G2 consumers one partition only while all consumers have identical subscriptions and all four partitions exist. Treat a different assignment as a pre-E1 compatibility defect or an invalid measured run, not as evidence of balanced active-active processing.
- Keyed events preserve order only within their Event Hub partition. The protocol does not assume total ordering across the two Event Hubs; `event_version` protects the materialised state from cross-topic reordering.
- Event Hubs may not expose complete consumer-group member assignments through the Kafka admin API. Structured Aggregator rebalance logs are the assignment authority when collector assignment data is unavailable.
- AKS control-plane and image-pull times may vary between runs; retain raw timestamps and report all measured repeats rather than only the best result.
- Azure quotas, regional SKU availability, and zone support may require parameter changes before E1. Freeze changes before measured comparisons.
- Cost Management data is delayed and may include taxes, credits, or rounding. Report the billing view and currency used.
- Short-lived actual cost must not be presented as a fabricated annual estimate.
- AKS Free tier has no financially backed control-plane SLA claim in this evaluation.
- Measurement-host or network failure can resemble service failure. Use the frozen external laptop/network arrangement, record its own health, and retain raw errors; invalidate runs affected by laptop, power, or local-network failure.
- UTC clock drift can corrupt recovery measurements. Check clocks before every run.
- The preselected fixed repeat count improves comparability but does not establish production SLA statistics.
- Evidence must be sanitised; no Azure credentials, secrets, or unredacted sensitive identifiers enter Git.

## 12. Review Gate

Implementation begins only after this protocol is reviewed and frozen. The next stage may prepare reusable IaC and measurement scripts, but Azure resources must not be created until an explicit approval step.

## 13. Authoritative Azure References

- [Azure Event Hubs for Apache Kafka](https://learn.microsoft.com/en-ie/azure/event-hubs/azure-event-hubs-apache-kafka-overview) — Kafka protocol support is available in Standard, Premium, and Dedicated tiers, not Basic.
- [Configure Event Hub properties](https://learn.microsoft.com/en-us/azure/event-hubs/configure-event-hub-properties) — Standard-tier partition count is selected at creation and cannot be updated later.
- [Event Hubs frequently asked questions](https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-faq) — partitions bound consumer-group parallelism; excess Kafka consumer members can remain idle and membership changes trigger rebalancing.
- [Event Hubs features and terminology](https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-features) — partition keys are statically hashed, preserve related-event ordering within a partition, and must be structured to benefit from multiple partitions.
- [Event Hubs availability and consistency](https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-availability-and-consistency) — keyed events are stored together and ordered within their partition, with an explicit availability/consistency trade-off.
- [Apache Kafka `RoundRobinAssignor`](https://kafka.apache.org/21/javadoc/org/apache/kafka/clients/consumer/RoundRobinAssignor.html) — identical topic subscriptions produce a uniform partition distribution across consumers.
- [Configure AKS availability zones](https://learn.microsoft.com/en-us/azure/aks/reliability-availability-zones-configure) — zone-aligned user node pools are created by assigning one zone to each pool, and pool zone configuration cannot be changed after creation.
- [Stop and start AKS node pools](https://learn.microsoft.com/en-us/azure/aks/start-stop-nodepools) — supported user-pool stop/start operations, prerequisites, interruption warning, and restrictions for system pools and Node Autoprovisioning.
- [`az aks nodepool` CLI reference](https://learn.microsoft.com/en-us/cli/azure/aks/nodepool?view=azure-cli-latest) — syntax for `az aks nodepool stop`, `start`, and zone configuration.
- [AKS support policies](https://learn.microsoft.com/en-us/azure/aks/support-policies) — use supported AKS operations rather than directly modifying managed infrastructure.
- [Kubernetes Pod topology spread constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/) — `ScheduleAnyway` permits scheduling while treating skew as a preference; `DoNotSchedule` can leave a Pod unscheduled.
- [AKS Free, Standard, and Premium tiers](https://learn.microsoft.com/en-us/azure/aks/free-standard-pricing-tiers) — AKS Free provides best-effort uptime without a financially backed SLA.
- [Azure Front Door architecture best practices](https://learn.microsoft.com/en-us/azure/well-architected/service-guides/azure-front-door) — origin health probes and multi-origin routing considerations.
- [Azure Front Door origins and origin groups](https://learn.microsoft.com/en-us/azure/frontdoor/origin) — health-probe configuration and origin enable/disable behaviour.
- [Azure Front Door health probes](https://learn.microsoft.com/en-us/azure/frontdoor/health-probes) — HTTP 200 health evaluation, GET/HEAD behaviour, distributed probing, sample windows, and latency measurement.
- [Azure Front Door routing methods](https://learn.microsoft.com/en-us/azure/frontdoor/routing-methods) — priority, latency sensitivity, weights, origin health, and active-passive/active-active routing behaviour.
- [`az afd origin-group` CLI reference](https://learn.microsoft.com/en-us/cli/azure/afd/origin-group?view=azure-cli-latest) — configurable probe method/path/protocol/interval and load-balancing sample parameters.
- [Azure Cost Management exports](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-improved-exports) — actual-cost exports, schemas, and delayed cost-data considerations.
