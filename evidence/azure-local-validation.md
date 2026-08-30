# Azure Experiment Preparation — Local Validation

**Date:** 2026-08-30
**Protocol:** 1.0.3
**Azure resources created:** No

| Validation | Observed result | Status |
|---|---|---|
| Automated tests | The original 12 tests and four blocker-specific tests passed in the pinned experiment-tools image (16/16) | PASS |
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
| Live Azure prices | Existing public EUR retail meters were reconfirmed on 2026-08-29; amended D2as_v4 meters were queried on 2026-08-30 at EUR 0.101/hour in West Europe and EUR 0.094/hour in North Europe | PASS |
| Preliminary amended freeze | Schema version 2 / protocol 1.0.3 generated and checksummed with estimated total EUR 16.394321; `worktree_clean: false` pending committed-checkpoint regeneration | PASS |
| Repository secret scan | Current working tree and index contain only placeholders, test fixtures, redaction patterns, or environment-variable references; the local secret manifest is ignored and no longer tracked | PASS |

The historical manual Phase 1 failure scenarios were not rerun. The blocker corrections did not change PostgreSQL transaction boundaries, history/current-state atomicity, post-transaction offset commit, fail-on-error behaviour, `event_id` idempotency, or `event_version` state protection.

The v1.0.3 freeze artifact in this uncommitted amendment checkpoint is deliberately preliminary. No experimental Azure resources existed when the quota incompatibility was discovered or amended. After committing this checkpoint, regenerate the final freeze and checksum so they reference the clean amendment commit before E1 deployment.
