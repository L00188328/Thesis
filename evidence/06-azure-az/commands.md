# F1 Azure Simulated Zonal Failure — Operator Runbook

Protocol v1.0.8. Credentials were supplied only through the ignored runtime environment or the mounted Kubernetes Secret. Region B and Azure Front Door were not deployed.

1. Verify the amended freeze/checksums, Azure login, budget, quota, Italy North AKS 1.35.7 availability, shared dependencies, and completed E1 inventory.
2. Delete the completed non-zonal E1 AKS cluster only after preserving E1 evidence; wait until it is absent.
3. Deploy Region A from `region-a-f1.bicepparam`, then verify exactly `system`, `appzone1`, and `appzone2`, with the two application pools pinned to zones 1 and 2.
4. Grant the replacement kubelet identity `AcrPull`; apply the mounted Secret, ConfigMap, replicated overlay, PDBs, Services, and immutable E1 application image digests.
5. Verify one Aggregator and one API Pod per zone, two Event Hubs members with two partitions each, zero baseline lag, direct HTTP canary routing, and at least 60 consecutive successful preflight probes.
6. Execute and discard `F1-warmup` with all frozen collectors and stop `appzone1` at T1+60 seconds; restore and verify the two-zone topology afterward.
7. Execute measured `F1-r01` identically with `appzone1` selected and recorded before T0; validate integrity/final lag and restore the topology.
8. Execute measured `F1-r02` identically with `appzone2` selected and recorded before T0; validate integrity/final lag and restore the topology.
9. Capture final Kubernetes/Azure configuration, events, logs, resource inventory, cost status, derived metrics, and post-recovery integrity.
10. Export only sanitised text evidence and verify its manifest before mutation.
11. Stop, but do not delete, Region A AKS and PostgreSQL compute; retain Event Hubs, ACR, database storage, and the reusable F1 topology for the regional experiments.

For each 600-second window, the external host concurrently ran the one-second canary probe, five-second workload-freshness collector, five-second Event Hubs progress/assignment collector, and the 600-event publisher. The fault remained in place through the end of the window.
