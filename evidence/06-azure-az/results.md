# F1 Azure Simulated Zonal Failure — Results

F1 completed under frozen protocol v1.0.8. This was a **simulated zonal failure** created with the supported AKS user-node-pool stop action; it was not an Azure Availability Zone outage. Results are descriptive prototype observations and are not production SLA statistics.

## Outcome

| Run | Status | Failed pool | Availability | Failures | Longest failure sequence | p50 / p95 / p99 / max latency (ms) | Maximum lag | Final integrity |
|---|---|---|---:|---:|---:|---|---:|---|
| `F1-warmup` | Discarded, valid rehearsal | `appzone1` | 100.00000% (600/600) | 0 | 0 | 135.23 / 312.93 / 334.78 / 644.27 | 6 | PASS: 600 unique, 0 missing, 0 duplicates, both states v300 |
| `F1-r01` | Measured PASS | `appzone1` | 99.00000% (594/600) | 6 | 2 | 130.38 / 163.56 / 245.25 / 3129.25 | 3 | PASS: 600 unique, 0 missing, 0 duplicates, both states v300 |
| `F1-r02` | Measured PASS | `appzone2` | 99.83333% (599/600) | 1 | 1 | 111.95 / 140.84 / 206.97 / 419.06 | 3 | PASS: 600 unique, 0 missing, 0 duplicates, both states v300 |

Latency uses the unchanged direct external-host-to-Region-A HTTP path. It must not be compared with later G1/G2 latency without accounting for their external HTTPS Front Door and HTTP origin path.

## Recovery and progress

Durations are seconds after the node-pool stop command (T2).

| Run | Azure command accepted | Pool reported stopped | Node removed | Replacement scheduled / containers started | Replacement API Ready and routed | First / sustained event progress | Backlog recovery | T3 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `F1-warmup` | 11.931 | 11.783 | 50.370 | 14.370 / 15.370 | 30.258 | 3.153 / 3.153 | 3.153 | none |
| `F1-r01` | 10.124 | 10.026 | 52.383 | 12.383 / 13.383 | 26.443 | 3.819 / 3.819 | 3.819 | first service timeout at 128.438 s |
| `F1-r02` | 9.938 | 9.822 | 52.648 | 12.648 / 13.648 | 29.937 | 3.358 / 3.358 | 8.360 | first service timeout at 166.931 s |

The first successful probe and first five-success sequence occurred immediately after T2 in both measured runs (r01: 0.442 s; r02: 0.939 s), because service initially remained available through the managed stop transition. Later isolated timeouts remain failures in the full-window numerator and are not removed. Neither measured run had a workload-freshness progress interruption; both finished with three consecutive zero-lag samples and complete database integrity.

## Topology and complexity

The verified topology contained one AKS cluster, three node pools (`system`, `appzone1`, `appzone2`), two desired Aggregator replicas, two desired API replicas, one region, and two explicitly configured application zones. Before every run, each application had one Ready Pod per zone. During each fault, replacement Pods were allowed to co-locate in the surviving zone as frozen.

The raw complexity vector is **[1, 3, 4, 1, 2, 0, 9, 1, 8]** for clusters, node pools, desired application replicas, regions, configured application zones, Front Door/routing objects, applied Kubernetes application/configuration objects, measured manual failover actions, and deployment-to-stable runbook steps. The optional unweighted index is 29; the raw vector is authoritative.

## Instrumentation note

The live macOS node watcher used GNU-style `%3N`, which macOS `date` retained literally, and it exited when Azure first reported the pool `Stopped` before Kubernetes removed the node. Those raw rows are retained unchanged. The required node-unavailable timestamps were recovered from the retained authoritative Kubernetes `RemovingNode` events at one-second precision: 50.370 seconds after T2 for the warm-up, 52.383 seconds for r01, and 52.648 seconds for r02. Azure pool-state, Kubernetes replacement scheduling/container events, probes, assignments, lag, workload and integrity streams were unaffected.

## Evidence and final Azure state

`exported/export-manifest.json` records the sanitised primary export. It contains the warm-up and two measured raw directories, metrics, timelines, broker assignments, progress/freshness, published/expected events, integrity, Kubernetes events/configuration, and Azure inventory. No binary or unsupported file was accepted or silently omitted.

After export and final integrity verification, Region A AKS and PostgreSQL compute were stopped to contain cost. They were not deleted. Event Hubs, ACR, PostgreSQL storage/data, and the reusable F1 topology remain. `post-experiment/` records the stopped states.
