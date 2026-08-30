# E1 Azure Baseline — Results

Complete observations only after the corresponding command has succeeded.

| Test | Purpose | Expected Result | Observed Result | PASS/FAIL | Evidence |
|---|---|---|---|---|---|
| Preflight | Prove frozen configuration is deployable and cost guarded | Freeze/checksum valid; budget alerts active; providers registered; AKS patch, quota and names available | Azure policy rejected West/North Europe before service creation; v1.0.5 selected policy-permitted Italy North/Norway East after service, patch, quota, SKU and zone checks | PASS | `config/preflight/` and `raw/azure/timeline.csv` |
| Shared dependencies | Provide the common registry, Event Hubs and PostgreSQL services | Deployment succeeds and effective resources match v1.0.7 | Pending | Pending | `config/shared-deployment-sanitised.json` |
| Partition-key verification | Freeze broker-observed keys for every planned run | Each run has one key on each partition; temporary Event Hub deleted | All 24 frozen run IDs have two unique keys; all 48 broker observations matched partitions 0/1 with complete producer/partitioner metadata; temporary Event Hub absence confirmed | PASS | `partition-key-map.json` and `raw/azure/timeline.csv` |
| E1 topology | Establish the single-region, single-application-node baseline | One non-zonal application pool; one Aggregator and one API Pod Ready | Pending | Pending | `config/effective-kubernetes-objects.yaml` |
| Warm-up | Discard one complete rehearsal using identical instrumentation | 600 events, final version 300 per shipment, zero lag and full integrity | Pending | Pending | `raw/E1-single-replica/warm-up/` |
| E1 run 01 | Measure normal-cloud baseline availability and progress | Ten-minute window completes without injected fault; integrity and lag pass | Pending | Pending | `raw/E1-single-replica/run-01/` |
| E1 run 02 | Repeat the frozen baseline | Ten-minute window completes without injected fault; integrity and lag pass | Pending | Pending | `raw/E1-single-replica/run-02/` |
| E1 run 03 | Repeat the frozen baseline | Ten-minute window completes without injected fault; integrity and lag pass | Pending | Pending | `raw/E1-single-replica/run-03/` |
| Evidence export | Prevent credentials or raw identifiers entering the repository | Text evidence sanitised, checksummed and no unsupported files silently accepted | Pending | Pending | `export-manifest.json` |
