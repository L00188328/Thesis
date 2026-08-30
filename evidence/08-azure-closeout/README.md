# Final Azure Experimental Closeout

Protocol v1.0.9 formally closes the Azure experimental programme.

The final empirical chain is:

`Application correctness → local Kubernetes Pod resilience → E1 Azure baseline → F1 simulated zonal resilience`

E1 completed with one discarded warm-up and three measured runs. F1 completed with one discarded warm-up and two measured runs. E2-A/E2-B were removed from Azure execution because the corresponding Aggregator and API Pod-failure mechanisms had already been experimentally evaluated in the local Kubernetes phase.

G1 infrastructure preparation reached a successful Region B deployment at `2026-08-30T14:43:52.128098Z`. The frozen Front Door deployment operation began at `2026-08-30T14:53:05.093622Z` and the deployment recorded failure at `2026-08-30T14:54:16.1721727Z` with the sanitized Azure rejection `Free Trial and Student account is forbidden for Azure Frontdoor resources.` The Front Door resource inventory was empty. No G1 warm-up, T1, controlled workload, or measured run began; all G1 reserved IDs/keys remain unused.

G2 was never started. It is not executed because the same subscription constraint made the frozen Front Door routing architecture unavailable. No alternative routing service or subscription was used because substitution would change the evaluated architecture. G1/G2 remain designed strategies only and have no availability, recovery, latency, lag, integrity, assignment, or cost-performance results.

Before teardown, 209/209 historical freeze/evidence checksums passed. Sanitized pre-teardown evidence preserves resource paths, names, SKUs, regions, tags, deployment timestamps, activity timestamps, and the pending cost-query status. Permanent deletion then removed Region A and Region B AKS and their managed resources, PostgreSQL, Event Hubs, ACR, and all thesis resource groups. Subscription-wide final inventories contain zero thesis resources in every targeted service category. The EUR 50 monthly budget guard is intentionally retained and is non-billable.

Actual Cost Management data remained unavailable at closeout; the final query returned HTTP 429. No missing actual cost or G1/G2 cost-performance value is fabricated. Delayed billing data may be retrieved later without recreating resources.

