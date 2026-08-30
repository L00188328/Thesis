# Azure High-Availability Experimental Protocol

**Methodology version:** 1.0.9
**Status:** Final experimental amendment — programme closed
**Frozen at:** 2026-08-30T15:25:05Z

Methodological changes after this point are prohibited unless pre-E1 validation discovers a genuine technical incompatibility. Any such change requires a versioned amendment and the reruns defined by this protocol.

**Version 1.0.1 compatibility amendment:** Pre-E1 IaC validation established that the AKS API origin is an HTTP `LoadBalancer` Service with no repository-managed public certificate or TLS ingress. Adding certificate/DNS infrastructure solely for this experiment would materially increase scope and complexity. External clients still use HTTPS to Azure Front Door, but Front Door forwards and probes the controlled AKS origin over HTTP port 80. Validation also found the originally drafted AKS `1.32.2` pin was out of standard support; the IaC now requests supported minor `1.35`, and pre-deployment validation must resolve and record one identical patch available in both regions before either cluster is created. No availability, recovery, workload, integrity, cost, or fault definition changed.

**Version 1.0.2 transport clarification:** E1, E2-A, E2-B, and F1 send the external availability probe directly to the Region A HTTP `LoadBalancer` application endpoint. G1 and G2 send the external probe over HTTPS to Azure Front Door, which forwards and probes the AKS origins over HTTP port 80. No TLS ingress, certificate manager, or experiment-only DNS/certificate infrastructure is introduced. All availability, recovery, workload, integrity, cost, and fault definitions remain unchanged. Because the direct and Front Door paths contain different routing and TLS components, latency comparisons must identify the path and must not attribute path-induced differences solely to the application topology.

**Version 1.0.3 pre-E1 quota amendment:** Subscription quota discovery immediately before deployment found a zero-vCPU quota for the DASv5 family in both planned regions, making the frozen `Standard_D2as_v5` application nodes undeployable. Both regions expose `Standard_D2as_v4` with the required two-vCPU size and a four-vCPU family quota. Before any experimental Azure resource was created or any E1 run began, every application pool was therefore changed to `Standard_D2as_v4`, and the current EUR burn estimate was regenerated. System-pool sizing, application-node counts, zones, scheduling, workloads, metrics, routing, probes, repeat counts, fault mechanisms, transaction/commit behaviour, idempotency and event-version semantics remain unchanged. All configurations use the amended application VM size so comparability is preserved.

**Version 1.0.4 pre-E1 cost-attribution amendment:** Final rendered-IaC review found that the parameter sets did not carry the protocol-required `run` tag, and the shared/Region B sets lacked an unambiguous configuration-series tag. Before any experimental Azure resource was created or E1 began, frozen resource-tag sets were added for shared, E1, E2, F1, Region B, G1 Front Door and G2 Front Door resources. Persistent resources use series labels rather than individual repeat IDs because they span warm-up and three measured runs. This amendment changes cost attribution metadata only; no infrastructure SKU, count, topology, zone, workload, timing, metric, routing, probe, failure or application semantic changed.

**Version 1.0.5 pre-E1 subscription-policy amendment:** The first shared deployment request was rejected before resource creation by the Azure for Students `Allowed resource deployment regions` policy, which permits only Italy North, Switzerland North, Spain Central, Norway East and France Central. Read-only compatibility checks found that Italy North and Norway East both support every required service, non-preview AKS `1.35.7`, the frozen B2s/D2as_v4 sizes, sufficient family/total quota and unrestricted zones 1/2/3. France Central and Spain Central had subscription-specific zone restrictions for frozen sizes; Switzerland North was technically valid but not selected. Region A is therefore amended to Italy North and Region B to Norway East, and their current EUR VM meters are used in a regenerated burn estimate. The direct-versus-Front-Door routing definitions, region roles, node sizes/counts/zones, workloads, timings, metrics, failure mechanisms and application semantics remain unchanged. The rejected West Europe deployment created only empty resource groups and no experimental service resources.

**Version 1.0.6 pre-E1 run-identity clarification:** Multi-day execution made the original date-bearing run-ID format incompatible with the requirement to broker-freeze every future run key before E1, because future execution dates are not yet known. Measured runs now use stable IDs `<configuration>-r<two-digit repeat>` and warm-ups use `<configuration>-warmup`; each run records its actual start/end UTC dates separately in primary evidence. The complete measured and warm-up ID sets are frozen before broker verification. This changes identifiers only and does not change key hashing, partitioning, workloads, counts, rates, timings, metrics or comparisons. Shared Azure services had been provisioned when this pre-E1 contradiction was resolved, but no key manifest, workload, AKS cluster or measured E1 run existed.

**Version 1.0.7 pre-E1 evidence-schema correction:** Final broker-manifest readiness review found that the generator recorded the frozen partitioner globally but omitted the protocol-required producer version from each key object. Before the temporary verification Event Hub was created, the generator was corrected to record `kafka-python-ng 2.2.3` and `kafka-python-ng murmur2` on every key object. This changes evidence completeness only; the pinned producer package, key selection, key bytes, Murmur2 hashing, broker verification, partitions, workloads, metrics and application semantics remain unchanged. Shared Azure services existed, but no key manifest, temporary verification hub, AKS cluster, workload or measured E1 run existed when this was corrected.

**Version 1.0.8 post-E1 scope and repeat-count amendment:** E1 completed under v1.0.7 with its discarded warm-up and all three measured repeats; `E1-r01`, `E1-r02`, and `E1-r03` remain valid, unchanged results. The observed operator duration and resource overhead of executing the frozen protocol was substantially higher than planned. This operational observation—not the numerical E1 outcome—motivates focusing the remaining Azure budget/time on capabilities unavailable in the local single-node Kubernetes environment. E2-A and E2-B are cancelled from future Azure execution because Phase D already experimentally demonstrated the same principal Kubernetes Pod-failure mechanisms: Aggregator deletion/recovery with consumer reassignment and GraphQL API Pod deletion/replacement. The retained Azure chain is F1 simulated zonal failure, G1 active-passive regional resilience, and G2 active-active regional resilience, with one discarded warm-up and two measured repeats for each. Metric definitions, 600-second windows, probe/progress cadences, 600-event workload, Event Hubs partitioning/assignment, integrity criteria, F1/G1/G2 faults, Front Door settings, and application semantics are unchanged. The original pre-E1 key manifest and checksum remain historical evidence; E2 keys and the third-repeat F1/G1/G2 keys are marked planned but not executed in the separate v1.0.8 run plan.

**Version 1.0.9 final experimental amendment:** E1 is completed with one discarded warm-up and three measured runs. F1 is completed with one discarded warm-up and two measured runs. G1 infrastructure preparation reached a running Region B AKS deployment, but the Azure Front Door profile was rejected before the readiness gate or any workload execution with `Free Trial and Student account is forbidden for Azure Frontdoor resources.` G1 is therefore **blocked before workload execution by an Azure subscription constraint**, not an experimental FAIL result. No G1 warm-up, T1, controlled workload, or measured run began, and every G1 reserved ID/key remains unused. G2 was never started and is **not executed** because the same constraint makes the frozen Front Door-based multi-region routing design unavailable. No alternate routing service or subscription is substituted: Azure Front Door is a frozen component of the G1/G2 architecture, and substitution would change the evaluated design. There are no G1/G2 availability, recovery, latency, lag, integrity, or cost-performance measurements, and none may be inferred or estimated. The Azure experimental programme is closed; G1/G2 remain designed strategies for architecture discussion and Limitations/Future Work only. All thesis Azure resources were permanently torn down after sanitized inventory and blocker evidence export. Historical freezes, completed E1/F1 evidence, blocked-G1 raw evidence, and the broker key manifest remain unchanged.

## 1. Scope and Freeze Rule

This protocol governs the comparison:

**Application correctness → local Kubernetes Pod resilience → E1 Azure baseline → F1 simulated zonal resilience**

The comparative scope is application-layer availability and recovery of the Event Aggregation Service and GraphQL API. Azure Event Hubs and PostgreSQL are required supporting dependencies, but their own high-availability behaviour is outside the comparison. Conclusions are conditional on those dependencies remaining available.

The Event Aggregation Service is described as providing **at-least-once processing with an idempotent consumer**. It must never be described as exactly-once processing.

The original pre-E1 freeze and v1.0.8 amended freeze remain unchanged historical artifacts. Version 1.0.9 creates a separate final run-plan overlay, final freeze, checksums, experiment matrix, and Azure closeout evidence. Completed E1/F1 evidence and blocked-G1 evidence are never rewritten. The frozen G1/G2 architecture remains documented, but it is not part of the empirical performance comparison.

This is a descriptive prototype evaluation. Its repeat counts support transparent repeated observations and do not establish production SLA statistics.

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
- E1 and F1 use HTTP to the direct Region A public `LoadBalancer` application endpoint.
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

- E1 retains its completed discarded warm-up and three measured runs. F1 retains its completed discarded warm-up and two measured runs. G1/G2 have no workload windows or measurements.
- The post-E1 reduction applies only to future runs and responds to observed operational duration/resource overhead, not to the numerical outcome of E1.
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

Always label latency results with the routing path. E1/F1 measure the direct external-host-to-Region-A HTTP path, while G1/G2 include external HTTPS termination and routing at Azure Front Door plus the HTTP origin hop. Preserve the same latency calculation, probe cadence, and timeout definitions, but do not interpret differences between these paths as application-topology effects alone.

## 4. Final Experiment Matrix

Supporting Event Hubs and PostgreSQL remain as constant as practical and outside the comparative HA scope.

| Configuration | Status | Runs executed | Empirical evidence | Reason if not executed |
|---|---|---|---|---|
| Local Kubernetes Pod HA | COMPLETED | D4 Aggregator Pod failure; D5 API Pod failure | `evidence/04-kubernetes-pod-failover/` | Not applicable |
| E1 Azure baseline | COMPLETED | 1 discarded warm-up + 3 measured | `evidence/05-azure-baseline/` | Not applicable |
| F1 simulated zonal resilience | COMPLETED | 1 discarded warm-up + 2 measured | `evidence/06-azure-az/` | Not applicable |
| G1 active-passive | BLOCKED BEFORE WORKLOAD EXECUTION — Azure subscription constraint | 0 | Blocker/infrastructure evidence only: `evidence/07-azure-region/g1-blocked-2026-08-30/` | Azure for Students rejected the frozen Front Door resource |
| G2 active-active | NOT EXECUTED | 0 | Design/IaC only; no empirical results | The same Front Door subscription constraint made the frozen routing design unavailable |

E2-A and E2-B were removed from Azure execution under v1.0.8. Their principal Kubernetes mechanisms are represented by the completed Phase D evidence in `evidence/04-kubernetes-pod-failover/`: Aggregator Pod deletion/recovery, replacement, consumer reassignment, zero final lag and database integrity; and GraphQL API Pod deletion/replacement with continued Service routing.

The G1/G2 sections below preserve the frozen designs only. They were not empirically executed and must not be used to claim availability, recovery, latency, lag, integrity, assignment, regional continuity, or cost-performance results.

### 4.1 G1 Standby State — Frozen Design, Not Executed

The proposed G1 freeze is a **running cluster with stopped application-capacity standby** in Region B:

- Cluster B control plane and minimum system node pool remain running.
- A dedicated user node pool for the Aggregator and API is created, labelled/tainted for application workloads, and stopped with `az aks nodepool stop` before T0.
- Aggregator and API Deployments, Services, configuration, secrets, probes, and desired replica counts are already applied. Their Pods remain Pending while the application pool is stopped because they cannot schedule on the system pool.
- The Region B Front Door origin exists, is enabled at lower priority, and is expected to be unhealthy until the API becomes Ready.
- Region A is the priority-1 healthy origin; Region B is priority 2.

After the Region A fault at T2, the single planned manual activation action is `az aks nodepool start` for Region B's application pool. Desired Pods then schedule automatically, and Front Door routes automatically when its probes mark Region B healthy. Record any unplanned additional operator action separately.

Implications:

- **Designed recovery path:** includes node-pool allocation/start, node Ready, image pull, Pod scheduling/readiness, Front Door health detection, and five-probe sustained service recovery. No duration was measured or estimated.
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
- Keep the same topic names, partition count, group ID, key strategy, and assignment strategy across the completed E1 and F1 configurations. The same values remain part of the unexecuted G1/G2 design.
- Preserve shipment ID as the Kafka key so events for one shipment remain on one partition within each Event Hub.
- Preselect two unique controlled shipment IDs/keys for every planned measured run before the first E1 T0. For each run, one key must map to Partition 0 and the other to Partition 1 in both Event Hubs, and both keys must publish events to both Event Hubs.
- Preserve the complete broker-verified pre-E1 key manifest in `evidence/partition-key-map.json` unchanged. `evidence/azure-run-plan-v1.0.9.json` is the final status overlay. G1/G2 keys, cancelled E2 keys, and cancelled third-repeat keys are retained for auditability, remain unused where stated, and are never reused.

The implicit range strategy was changed to an explicit `RoundRobinPartitionAssignor` before E1 and remained unchanged through completed F1. Its proposed G2 distribution remains a design statement only because G2 was not executed. This instrumentation/configuration change did not alter manual offset commits, database transaction ordering, fail-on-processing-error behaviour, idempotency, or stale-state protection.

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
- F1: two Aggregators should receive two partitions each.
- G1 standby: Region A owns assignments while Region B application capacity is stopped; Region B receives assignments only after activation/rebalance.
- G2: four Aggregators join one group and should receive one partition each. Because both workload keys send to both Event Hubs, every assigned partition should carry controlled traffic and both regions should perform useful Aggregator work before the fault.

Round-robin assignment is not region-aware and does not promise equal event counts per region. Every run must record actual assignment and per-instance processing from structured logs and the external collector. Do not claim both regions processed simultaneously unless that evidence confirms it.

### 4.5 G1/G2 Region A Failure Mechanism — Frozen Design, Not Executed

Use one identical Region A application-capacity fault for G1 and G2. Region A's Aggregator and API Pods must have required scheduling rules that permit only the frozen Region A application user node pools and exclude the system pool.

At T2, one version-controlled fault script records the command timestamp and issues `az aks nodepool stop --no-wait` for every Region A application user pool in the fixed order recorded in `evidence/azure-experiment-freeze.json`. Record each operation-accepted timestamp, first Region A application node with `Ready != True`, all affected Pod transitions, and the first time all target pools report stopped.

Do not disable, remove, reprioritise, or reconfigure the Region A Front Door origin during either measured fault. Front Door must detect the unavailable Region A API through its frozen health probes:

- In G1, after the identical Region A stop commands are accepted, record the separate planned manual `az aks nodepool start` activation of Region B's application user pool.
- In G2, Region B application capacity is already running and no standby activation action occurs.

Restore Region A by starting the same application pools only after the measured window, unless safety requires earlier recovery; record any deviation and invalidate the run if it changes the measured fault.

### 4.6 Azure Front Door Parameters — Frozen Design, Not Executed

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

The same workload implementation and rates were used across completed E1 and F1. They remain documented for the unexecuted G1/G2 design but produced no G1/G2 workload evidence.

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

`evidence/azure-burn-estimate-v1.0.8.json` remains a historical planning estimate, not an actual-cost result. Actual Cost Management data for E1, F1, and G1 preparation remained unavailable at final closeout: the final query returned HTTP 429. No missing amount is fabricated. `evidence/08-azure-closeout/pre-teardown/` preserves sanitized resource paths, SKUs, regions, tags, and operation timestamps for later billing attribution; `post-teardown/` preserves the final zero-resource verification. No G1/G2 cost-performance result exists.

## 8. Evidence Layout

Do not store credentials, connection strings, access tokens, or unredacted subscription identifiers in evidence.

The historical pre-E1 artifact `evidence/azure-experiment-freeze.json` and the post-E1 `evidence/azure-experiment-freeze-v1.0.8.json`, with their checksums, remain unchanged. The final amendment creates `evidence/azure-experiment-freeze-v1.0.9.json`, `evidence/azure-run-plan-v1.0.9.json`, and their own checksums. The final freeze records:

- `protocol`: version `1.0.9`, the Git commit containing the final amended protocol, its SHA-256, and UTC amendment-freeze timestamp;
- `amendment`: references to the unchanged historical freeze, checksum, key manifest, and versioned amended run plan;
- `billing`: sanitised subscription reference, billing currency, separate E1/F1/G1-preparation cost references, pending actual-cost status, the last HTTP 429 query result, and retained budget guard;
- `regions`: Region A and Region B, plus the sanitised physical location of the external laptop;
- `resource_tags`: the frozen project, phase, configuration-series, run-series, owner and applicable region-role tags used for cost attribution;
- `run_identity`: completed E1/F1 IDs; G1 IDs blocked before workload execution and unused; G2 IDs not executed and unused; cancelled historical IDs; and references to the unchanged broker manifest and final run plan;
- `skus`: Front Door/Event Hubs/AKS/PostgreSQL tiers and every cluster, node-pool, VM size, mode, zone, and desired/min/max node count;
- `event_hubs`: namespace tier, entity names, two partitions per entity, retention, consumer group, producer/client version, producer partitioner, and `RoundRobinPartitionAssignor`;
- `front_door`: profile tier, endpoint/route, origin names/host headers/ports, priorities, weights, HTTP GET `/ready` to origin, HTTPS client endpoint, 10-second interval, sample size 4, successful samples 3, 1000-millisecond additional latency, disabled session affinity, non-applicable HTTP-origin certificate-name validation, and disabled GraphQL caching;
- `probe_transport`: direct Region A HTTP for E1/F1 and external HTTPS to Front Door with an HTTP AKS origin hop for G1/G2;
- `measured_repeat_counts`: completed E1 count 3, completed F1 count 2, and executed G1/G2 count 0;
- `fault_mechanisms`: F1's single zone-aligned user-pool stop and the ordered Region A application-pool list/script used identically by G1 and G2, plus G1's separate Region B activation action;
- `external_host`: stable laptop ID, sanitised physical location, OS/kernel, tool/container versions, mains-power/sleep state, wired/Wi-Fi connection state, ISP/public-egress arrangement, DNS configuration, time synchronisation, and VPN/proxy state.

Validate and checksum the final JSON. No further Azure deployment is permitted by this final amendment; historical artifacts must not be edited silently.

The canonical, complete pre-E1 key manifest is `evidence/partition-key-map.json`; its original bytes and broker-verification evidence remain unchanged. `evidence/azure-run-plan-v1.0.9.json` is the authoritative final execution-status overlay. Each executed run retains a checksum-addressed reference. G1/G2 reserved keys remain unused.

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
cost/
  E1-cost-window.md
  E1-resource-inventory.csv
  E1-actual-cost.csv
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
raw/F1-simulated-zonal-failure/
  warm-up/
  run-01/
  run-02/
Each run directory contains:
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
run-plan.md
g1-blocked-2026-08-30/
  README.md
  azure/front-door-failure.json
  azure/front-door-resource-inventory.json
  azure/region-b-provisioned-topology.json
  preflight/preflight-summary.json
  post-experiment/resource-state.json
  export-manifest.json
```

No G1/G2 raw run directory exists because no workload window began. The blocked-G1 evidence is infrastructure/blocker evidence only and must not be interpreted as an experimental run.

### `evidence/08-azure-closeout/`

```text
README.md
final-experiment-matrix.md
cost/final-cost-status.md
pre-teardown/
  sanitized inventories, deployment/activity timestamps and cost-query status
post-teardown/
  deletion activity and zero-resource service inventories
```

Each `results.md` must include the common table:

`Test | Purpose | Expected Result | Observed Result | PASS/FAIL | Evidence`

Results are written only after observation.

## 9. Final Cost and Teardown State

All required E1/F1/G1-blocker evidence and checksums were verified before deletion. Sanitized pre-teardown inventories preserve resource paths, names, SKUs, regions, tags, deployment timestamps, and activity timestamps for delayed billing attribution. Region A AKS, Region B AKS, both AKS managed resource groups, PostgreSQL, Event Hubs, ACR, and the empty failed-Front-Door resource group were permanently deleted. Subscription-wide post-teardown inventories report zero thesis resource groups and zero thesis AKS, PostgreSQL, Event Hubs, ACR, Front Door, or other thesis resources. The non-billable EUR 50 budget guard is intentionally retained.

Cost Management was still delayed/rate-limited at final closeout and returned HTTP 429. Actual E1, F1, and G1-preparation costs remain pending. No G1/G2 cost-performance result exists and no missing cost is fabricated. Delayed charges may be retrieved from Azure billing later without recreating resources.

## 10. Final Azure Implementation Record

1. E1 completed with its discarded warm-up and `E1-r01` through `E1-r03`.
2. E2-A/E2-B were removed; completed Phase D local Pod-failure evidence is used instead.
3. F1 completed with its discarded warm-up and `F1-r01`/`F1-r02`.
4. G1 preparation restarted Region A and PostgreSQL, created Region B, applied the frozen workload, and attempted the frozen Front Door deployment.
5. Azure rejected Front Door before the readiness gate or workload execution. G1 stopped as blocked; G2 never started. No substitute was used.
6. Sanitized inventories, blocker records, activity timestamps, tags, SKUs, resource paths, and cost-query status were exported locally and checksummed.
7. All thesis Azure resource groups and billable services were permanently deleted and zero-resource verification was exported.
8. Delayed actual costs may be retrieved later from Azure billing without recreating resources. No further Azure experiment or deployment is permitted by this protocol.

Azure DevOps and self-hosted agents are excluded. The repository remains in GitHub. GitHub Actions is optional later and is not required for this experimental sequence.

## 11. Risks and Dissertation Assumptions

- F1 is a controlled simulated zonal failure, not an actual Availability Zone outage. G1/G2 produced no failure experiment or empirical result.
- Docker Desktop results and Azure results use the same application semantics but different infrastructure and networking paths.
- PostgreSQL and Event Hubs availability are assumed during application HA tests; failures in those services invalidate the run rather than measure the tested topology.
- Shared cross-region dependencies may add latency or become a common dependency; this must be stated when interpreting regional results.
- Event Hubs partition count limits active consumers. Replica count does not prove simultaneous consumption; actual assignment is evidence.
- Front Door health-probe and routing settings remain part of the unexecuted G1/G2 design only; they produced no measured recovery evidence.
- `az aks nodepool stop` is a supported managed operation, but its shutdown sequence may differ from an abrupt physical zone outage; F1 remains a simulated zonal failure.
- Standard-tier Event Hubs partition counts cannot be changed after creation. Incorrect provisioning requires replacement before E1, not an in-series change.
- The proposed four-consumer G2 assignment was never observed; do not infer balanced active-active processing from the design.
- Keyed events preserve order only within their Event Hub partition. The protocol does not assume total ordering across the two Event Hubs; `event_version` protects the materialised state from cross-topic reordering.
- Event Hubs may not expose complete consumer-group member assignments through the Kafka admin API. Structured Aggregator rebalance logs are the assignment authority when collector assignment data is unavailable.
- AKS control-plane and image-pull times may vary between runs; retain raw timestamps and report all completed E1/F1 repeats rather than only the best result.
- Azure quotas, regional SKU availability, and zone support may require parameter changes before E1. Freeze changes before measured comparisons.
- Cost Management data is delayed and may include taxes, credits, or rounding. Report the billing view and currency used.
- Short-lived actual cost must not be presented as a fabricated annual estimate.
- AKS Free tier has no financially backed control-plane SLA claim in this evaluation.
- Measurement-host or network failure can resemble service failure. Use the frozen external laptop/network arrangement, record its own health, and retain raw errors; invalidate runs affected by laptop, power, or local-network failure.
- UTC clock drift can corrupt recovery measurements. Check clocks before every run.
- This is a descriptive/prototype evaluation. E1's three and F1's two completed measured repeats support transparent repeated observations but do not establish production SLA statistics. G1/G2 are excluded from empirical performance conclusions.
- Evidence must be sanitised; no Azure credentials, secrets, or unredacted sensitive identifiers enter Git.

## 12. Programme Closure

The Azure experimental programme is closed. Do not attempt G1 or G2 again, substitute another routing service or subscription, or recreate thesis Azure resources under this protocol. G1/G2 may be discussed only as designed strategies and limitations/future work. Dissertation prose drafting is outside this amendment.

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
