# Azure Experiment Preparation — Local Validation

**Date:** 2026-08-28  
**Protocol:** 1.0.2  
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
| Azure Bicep | All four templates and all seven parameter files compiled with Azure CLI 2.89.0 and Bicep 0.46.1 | PASS |
| Preliminary freeze | Schema version 2 / protocol 1.0.2 generated and checksummed with all non-live fields; `worktree_clean: false` | PASS |
| Repository secret scan | Current working tree and index contain only placeholders, test fixtures, redaction patterns, or environment-variable references; the local secret manifest is ignored and no longer tracked | PASS |

The historical manual Phase 1 failure scenarios were not rerun. The blocker corrections did not change PostgreSQL transaction boundaries, history/current-state atomicity, post-transaction offset commit, fail-on-error behaviour, `event_id` idempotency, or `event_version` state protection.

The freeze artifact in this uncommitted checkpoint is deliberately preliminary. After Azure authentication, select one exact AKS 1.35 patch available in both planned regions and confirm current live prices. After committing the checkpoint, regenerate the final freeze and checksum so they reference that clean commit.
