# K3s Phase F demonstration baseline

This environment adapts the thesis application-worker failure experiment to three x64 Azure VMs. It does not reproduce an actual Azure Availability Zone outage or the managed AKS experiment.

The server is in Italy North Zone 3 (B2s, 2 vCPUs/4 GiB). Each application worker is D2as_v4 (2 vCPUs/8 GiB), in Zones 1 and 2. Total VM quota consumption is six regional vCPUs: two B-series and four DASv4.

The server runs K3s v1.35.9+k3s1, SQLite and system components. Workers run the unchanged thesis images. Flannel VXLAN and a server NodePort replace AKS networking and its Azure Load Balancer. API access is http://SERVER_IP:30080/graphql/. Traefik and ServiceLB are disabled. The server remains a shared dependency outside the worker-failure scope.

## Presentation-only eviction settings

`k8s/kustomization.yaml` adds explicit 30-second NoExecute tolerations for `node.kubernetes.io/not-ready` and `node.kubernetes.io/unreachable` to BOTH application Deployments. This deliberately shortens eviction after node failure detection to make the live demonstration practical. **It was not part of the original measured Phase F experiment.** Node detection, consumer rebalance, scheduling and readiness still take additional time; report actual timestamps.

The historical manifests, thesis results and evidence are unchanged. Preferred anti-affinity, ScheduleAnyway zone spreading, application-only affinity, two replicas per service and disruption budgets remain in use.

## Provisioning and credentials

`provision.py` has explicit network/shared/images/vms stages; `baseline.py` has install/deploy stages. These target only the named demo groups. They contain no VM stop, delete or failure-injection stage. Execution requires Docker Desktop, the persistent authenticated Azure CLI config volume and operator permissions. Do not run stages blindly against another subscription or existing untagged groups.

Private state, database and registry credentials, SSH keys, Docker login cache and kubeconfig live in ignored `.private/`; never commit or share it. The ACR pull token expires after 30 days and must be rotated before later reuse. The operator IP in the server NSG must match the recording host. Workers accept no public inbound connections; SSH reaches them through the server. Each VM has an explicit static public IP for egress. Cluster overlay and kubelet traffic stay inside the VNet.

PostgreSQL16/B1ms/32GiB, database shipments and HA disabled match the existing shared template. Event Hubs Standard exposes two two-partition topics with the original SASL_SSL/PLAIN configuration. Schema initialization uses the original initializer. The four baseline seed events use fresh shipment IDs and are separate from any later demo workload.

## Baseline verification

`verify_in_cluster.py` runs in the cached thesis tools image on the surviving worker. It initializes/verifies PostgreSQL, publishes four acknowledged partition-checked seed events through the original generator, verifies exact persisted IDs and version2 states, checks four partitions, zero measured lag, two consumers with two assignments each, and GraphQL retrieval. A separate external check must verify the public NodePort and initial per-worker Pod placement.

A healthy baseline does not authorize failure injection. Stop here until the user explicitly approves the worker-failure run.

Fresh deployments initialize the original SQL schema once before launching all four application replicas, avoiding the original initializer’s concurrent table-creation race. The first baseline deployment encountered that race once; the affected Aggregator restarted and became Ready.

## Live orchestration

The completed live run `results/20261022T145721Z-45f6e90a-auto/` retains its original evidence and strict assessment. The measurement/summary changes below apply to future runs only. A new live fault requires separate operator approval. These commands are available from the repository root:

```bash
./demo/demo-failover.sh appzone1 --dry-run
./demo/check-demo.sh
# After approval, choose one live mode:
./demo/demo-failover.sh appzone1 --presentation-mode
./demo/demo-failover.sh appzone1 --auto
# After a live run, explicitly restore the baseline:
./demo/reset-demo.sh
```

The runner requires Python 3.10+, SSH, Docker Desktop running, an authenticated persistent Azure CLI config volume, and the existing SSH key/known-hosts files. No Kafka or PostgreSQL packages need to be installed on the operator laptop. A local lock prevents concurrent check/run/reset commands. `appzone1` is the only accepted target; there is no free-form VM selector. The full resource ID, subscription, dedicated resource group, ownership tag, Italy North location, Zone 1 and exact name `vm-demo-appzone1` are checked again immediately before the sole stop/start action. The control-plane VM cannot be selected. No quota changes, resource deletion or supporting-dependency stop operation exists in this runner.

### Azure CLI survives terminal restarts

All demo Azure calls use `azure_cli.py`, which creates a fresh `docker run --rm` helper for each command, using pinned image `mcr.microsoft.com/azure-cli:2.89.0`. Each helper mounts the existing `thesis-azure-cli-config` volume at `/root/.azure` and this repository at `/work`. No container ID or long-running helper is required, and closing Terminal or VS Code does not remove the login volume. Existing unrelated Docker containers are not started, stopped or deleted. The obsolete `container` field in older state files is ignored; provisioning removes it on the next state save.

The previous failure came from saving the ID of an interactive `docker run --rm -it` helper and later calling `docker exec` against it. Closing that helper's shell removed its container; recreating a helper gave it a different ID even with the same login volume. The command-per-helper design removes this dependency from provisioning, baseline checks, failover and reset.

The wrapper also supports read-only manual inspection or renewed authentication without managing IDs:

```bash
./demo/azure-cli.sh account show
./demo/azure-cli.sh login --use-device-code
./demo/reset-demo.sh
```

Docker Desktop must be running. If the original config volume is missing, the scripts stop with an explanation rather than silently creating an empty replacement. Revoked/expired Azure credentials require a fresh login; they are separate from container lifetime. Programmatic calls never automatically log out, log in or retry a possibly submitted resource mutation. Optional overrides are `DEMO_AZURE_CLI_CONFIG_VOLUME` / `DEMO_AZURE_CLI_IMAGE`, or `azure_cli_config_volume` / `azure_cli_image` in ignored state. The same explicit subscription binding and VM identity guards remain in force.

Dry-run/check read Azure VM/NIC inventory, Kubernetes node/Pod/Deployment/event state, an existing baseline shipment through external GraphQL, PostgreSQL using server-enforced read-only transactions, and Event Hubs metadata, assignments and committed/end offsets. They do not publish events, initialize schema, create Pods, change Kubernetes objects, join the consumer group, commit offsets or stop/start VMs. Baseline shipment IDs are read from the ignored `results/baseline.json` produced during baseline deployment. Dry-run prints the live sequence as text only. Local evidence files and the lock file are written.

Live mode executes the original thesis generator and Kafka helpers, supplied in memory, in the existing Zone-2 Aggregator container. It shares that container's resources and depends on that Pod remaining alive. There is no producer deployment, no application-image rebuild and no change to historical manifests. The operator laptop and Zone-3 SSH/API path remain observation dependencies. These choices keep the presentation small; this is a demonstration, not another original Phase F measurement.

Each run uses two fresh shipment IDs selected by the original Kafka key mapping for partitions 0 and 1. Production is one event/second, using the original four-event cycle and `acks=all`. Every exact expected payload is recorded before its send; every acknowledgement includes topic/partition/offset. An ambiguous or failed send fails the run. Production finishes a complete cycle when stopped and has a 40-minute hard lifetime bound. Before enabling scored progress probes, the runner requires at least eight acknowledgements across both topics and both partitions, an acknowledgement for each exact new shipment ID, both shipments visible in PostgreSQL and external GraphQL, SQL versions of at least two, and a successful availability probe. This avoids scoring a null shipment before its first event has been emitted/projected.

Presentation mode then displays `>>> READY TO INJECT FAILURE: ZONE 1 APPLICATION WORKER <<<` and waits for ENTER, with production and probes continuing. Ctrl-C/EOF cancels. The wait is bounded to 20 minutes. `--auto` uses the same workload gate without the ENTER pause. After the pause, the runner checks workload health, consumer membership, three-node readiness, replica spread and exact Azure target identity again. It issues **`az vm stop`**, retaining allocation and static networking; it does not deallocate or stop any other VM. No automatic reset hides the failure.

After the stop request, production/probes continue for at least 120 seconds and until the Zone-1 node is unavailable, shipment state advances before replacement readiness, the original Zone-2 replicas remain Ready, new Aggregator/API Pod UIDs are Ready on Zone 2, and two consumers have zero measured lag. This observation stage times out after 600 seconds. Kubernetes detection precedes the demo-only 30-second NoExecute tolerations; 30 seconds is not a promise of total replacement time. Raw node taint times, Pod deletion/creation/condition times and Kubernetes events are retained. A stopped worker's old Pods may remain Terminating because its kubelet is unreachable; no force deletion is used. Replacement readiness means **replica redundancy restored**; service continuity is measured separately using actual GraphQL requests and advancing projection state.

The constant version-2 baseline shipment measures availability from the start of the workload. Background GraphQL progress probes wait until the readiness gate confirms both new shipments have been emitted and are observable; the gate opens once and stays open. Readiness requests made while waiting are kept unchanged in `graphql-progress.jsonl`, with `purpose=readiness`, `phase=startup` and `scored=false`. Their success/failure counts remain visible in the summary and console. The gate opening time is saved as `progress_scoring_started_utc` and in the timeline. Scored progress requests are marked `phase=workload` or `phase=post-failure`, with `scored=true`. Every post-injection progress request is scored, including null shipments, HTTP errors, timeouts and connection failures; the gate is never closed again because of a failure.

Every actual request/response or error remains in the raw evidence. Summary totals combine all availability probes and scored progress probes, including final validation requests. Explicit startup readiness checks are reported separately, and preflight requests remain in their separate file. `raw_progress_probe_count` equals `progress_probe_count` plus `startup_progress_probe_count`. Historical records without phase/scoring metadata retain their original scoring; old run artifacts are never rewritten. Failed requests are never retried into successes. Observed success percentage is the fraction of scored recorded requests that succeeded, not a claim about every moment between probes.

After completing the producer cycle, the runner allows up to 120 seconds to drain. Final integrity checks compare expected, acknowledged and persisted unique IDs; include all rows for the run shipment IDs or `details.runId`; detect missing/unexpected events, duplicate IDs, duplicate shipment/version rows and payload differences; and compare each shipment's expected maximum version with PostgreSQL and final GraphQL fields. Unknown/partial offsets never count as zero lag. Event Hubs exposes member IDs and assignments but reports host `0.0.0.0` here, so the evidence does not claim member-to-Pod identity from the admin response.

The presentation summary reports separate outcomes:

- **Event integrity: PASS/FAIL** uses the unchanged event/payload/version checks.
- **Failover observed: PASS/FAIL** requires the selected Azure VM confirmed stopped, the Zone-1 node observed unavailable, and shipment state advancing after failure, including progress before replacement readiness.
- **Replica capacity restored: PASS/FAIL** requires both replacement replicas Ready on Zone 2 alongside the surviving replicas.
- **GraphQL successful probes: X/Y (percentage)** and the failed count retain every scored failure.
- **Missing events**, **Duplicate events** and **Final consumer lag** report measured values; unavailable lag is `UNKNOWN`.

Duplicate events count excess persisted rows repeating an event ID or shipment/version, counting each extra row once. Detailed duplicate-ID and duplicate-version evidence stays in `integrity.json`.

Live `summary.json` uses `summary_schema_version=2` and an `outcomes` mapping instead of a blanket `pass` verdict. `strict_graphql_availability_pass` still records whether every scored request succeeded, and `strict_pass` retains the former strict combined assessment for audit. These fields do not override the component outcomes. `execution_completed` records whether orchestration finished without collection/producer errors or a timeout. The process exits zero only when execution, all three component checks, final GraphQL state validation and two-consumer/zero-lag checks succeed with nonempty GraphQL measurements; a transient failed probe alone does not make the process exit nonzero. Interruptions, missing evidence, collection failures, failed final state validation, nonzero/unknown lag and failed component checks still produce a nonzero exit. Dry-run/check/reset keep their existing baseline PASS/FAIL behavior. No live run or reset was executed to verify this code change; regression checks use offline fakes.

## Evidence and reset

Each command writes `results/<UTC-time>-<random-id>-<mode>/`, ignored by Git. A dry-run saves `summary.json`, `preflight.json`, Azure VM identities, the raw Kubernetes baseline, dependency offsets/assignments, the external GraphQL response and `planned-actions.json`. Live runs additionally save:

- `expected-events.jsonl`, `acknowledged-events.jsonl`, `producer-stream.jsonl`, `producer-stderr.log` and `shipments.json`;
- `graphql-probes.csv`, `graphql-progress.jsonl`, `graphql-final.json` and `timeline.jsonl`;
- `cluster-observations.jsonl`, `dependency-observations.jsonl`, `dependencies-final.json`, `azure-failure-final.json`, `integrity.json` and `summary.json`.

Reset starts only `vm-demo-appzone1` if needed and waits for its Kubernetes node to be Ready. If both replicas are on Zone 2, reset temporarily cordons only `demo-appzone2` and uses the Kubernetes eviction API, respecting disruption budgets and Pod UID preconditions, to move at most one replica of each service back to Zone 1. It waits for each replacement and uncordons in a `finally` block. An already cordoned surviving node is treated as external maintenance and is not altered. This deliberate redistribution happens outside measurement and does not change Deployment specifications. Reset does not delete shipment history, rerun schema initialization or restart supporting dependencies. Full baseline checks, including two consumers and zero measured lag, must pass before it prints exactly `DEMO ENVIRONMENT READY`.

Offline guard, integrity and CLI lifecycle tests: `python3 -m unittest demo.test_demo_failover demo.test_azure_cli -v`.
