# E1 Azure Baseline — Operator Runbook

Protocol v1.0.5. Commands that consume credentials use ignored environment files or mounted Kubernetes Secrets; credentials and raw subscription identifiers are never written here.

1. Verify the final freeze checksum, Git checkpoint, host power/network controls, Azure login, budget alerts, provider registration, regional quota, exact AKS patch and frozen global-name availability.
2. Create the tagged shared and Region A resource groups and record accepted/completed UTC timestamps.
3. Deploy `shared.bicep` with `shared.bicepparam`; retain the unredacted deployment response outside the repository and export only sanitised evidence.
4. Initialise the PostgreSQL schema through a TLS connection, verify both tables, and retain no database credential in command arguments or evidence.
5. Create a temporary two-partition Event Hub, broker-verify every warm-up/measured-run key with the pinned producer, save the sanitised manifest, and delete the temporary Event Hub before E1.
6. Build the API and Aggregator images from the frozen checkpoint, push immutable commit-tagged images to ACR, and record repository digests.
7. Deploy Region A from `region-a-e1.bicepparam`, grant its kubelet identity `AcrPull`, retrieve credentials, and verify the exact non-zonal system/application-pool topology.
8. Create the Kubernetes ConfigMap and Secret from runtime values without writing credentials to the repository; render/apply the E1 overlay with immutable image references.
9. Verify Pods, Services, readiness, direct Region A HTTP GraphQL routing, Event Hubs partition assignment, zero baseline lag, PostgreSQL connectivity and the fully materialised fixed canary.
10. Capture the discarded warm-up using the same 10-minute workload and collectors as a measured run, then validate integrity and zero final lag.
11. Run E1 measured `run-01`, `run-02` and `run-03`; for each, start the 1-second canary probe, 5-second freshness collector, 5-second consumer-progress collector and 600-event/one-second publisher at T1, then verify integrity and final lag.
12. Export and sanitise raw evidence, effective configuration, application logs, resource inventory and cost-window timestamps; record PASS/FAIL observations before any topology mutation or teardown.
