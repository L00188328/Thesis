# Azure Experiment Preparation — Local Validation

**Date:** 2026-08-30
**Protocol:** 1.0.7
**Azure resources created:** No

| Validation | Observed result | Status |
|---|---|---|
| Automated tests | The original 12 tests, four blocker-specific tests and two v1.0.7 manifest-metadata tests passed in the rebuilt pinned experiment-tools image (18/18) | PASS |
| Controlled workload | 600 events published; exactly 150 events on each of the four topic/partition pairs | PASS |
| Workload freshness | Both controlled shipments sampled every 5 seconds during publication; successful observations progressed from versions 104/105 to 300 | PASS |
| Round-robin assignment | Two Aggregators; four partitions split 2/2; Redpanda reported `BALANCER roundrobin` | PASS |
| Consumer progress vs `rpk` | Collector and `rpk group describe` both reported committed/end offset 300 on every partition and total lag 0 | PASS |
| Database integrity | 600 expected and persisted rows, 600 unique IDs, no missing/duplicate rows, both materialised states at version 300 | PASS |
| Evidence export | All local validation text artifacts exported through the sanitizer; no files were rejected | PASS |
| Kubernetes manifests | E1 and replicated overlays rendered; two Deployments/two Services, with two total E1 replicas and four replicated replicas | PASS |
| Azure Bicep | All four templates and all seven amended parameter files compiled with Azure CLI 2.89.0 and Bicep 0.46.1 | PASS |
| Exact AKS patch | `1.35.7` confirmed non-preview and available under `KubernetesOfficial`/`AKSLongTermSupport` in both planned regions; all four affected regional parameter files recompiled | PASS |
| Pre-E1 VM quota amendment | DASv5-family quota was 0 vCPUs in both regions; protocol v1.0.3 changed every application pool to available two-vCPU `Standard_D2as_v4`, for which each region has a four-vCPU family quota | PASS |
| Pre-E1 cost-tag amendment | Protocol v1.0.4 froze project, phase, configuration-series, run-series, owner and applicable region-role tags in every reusable parameter set before resource creation | PASS |
| Pre-E1 allowed-region amendment | Azure policy rejected West/North Europe before service creation; protocol v1.0.5 selected Italy North/ Norway East after service, AKS patch, quota and zone-restriction checks | PASS |
| Pre-E1 run-identity amendment | Protocol v1.0.6 replaced unknowable future date-bearing IDs with 18 stable measured IDs and six warm-up IDs; execution UTC remains separately recorded | PASS |
| Pre-E1 key-manifest schema amendment | Protocol v1.0.7 records the pinned producer version and partitioner on every broker-verified key object before E1 | PASS |
| Live Azure prices | Public EUR retail meters were reconfirmed on 2026-08-30 for the policy-compatible regions; D2as_v4 is EUR 0.0984/hour in Italy North and EUR 0.1204/hour in Norway East | PASS |
| Preliminary amended freeze | Schema version 2 / protocol 1.0.7 generated and checksummed with stable run identities and complete key-manifest metadata; `worktree_clean: false` pending committed-checkpoint regeneration | PASS |
| Repository secret scan | Current working tree and index contain only placeholders, test fixtures, redaction patterns, or environment-variable references; the local secret manifest is ignored and no longer tracked | PASS |

The historical manual Phase 1 failure scenarios were not rerun. The blocker corrections did not change PostgreSQL transaction boundaries, history/current-state atomicity, post-transaction offset commit, fail-on-error behaviour, `event_id` idempotency, or `event_version` state protection.

The v1.0.7 freeze artifact in this uncommitted amendment checkpoint is deliberately preliminary. Shared dependencies exist, but no key manifest, temporary verification Event Hub, AKS cluster, workload or E1 measurement existed when the evidence-schema omission was corrected. After committing this checkpoint, regenerate the final freeze and checksum before broker verification.
