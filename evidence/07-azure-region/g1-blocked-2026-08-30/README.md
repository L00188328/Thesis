# G1 blocked execution attempt — 2026-08-30

Status: **BLOCKED before workload execution**.

The G1 environment setup began under protocol v1.0.8. Region A AKS and the shared PostgreSQL server were restarted successfully. Region B AKS was created successfully from `infra/azure/parameters/region-b.bicepparam` with Kubernetes 1.35.7, one `Standard_B2s` system pool in zone 1, and one `Standard_D2as_v4` application pool in each of zones 1 and 2. The Region B kubelet identity was granted `AcrPull` on the existing registry, and the frozen replicated Kubernetes workload was applied.

Azure then rejected creation of the protocol-required Front Door profile with `BadRequest`: `Free Trial and Student account is forbidden for Azure Frontdoor resources.` The failed resource-group inventory was empty, confirming that no Front Door resource was created.

Because G1 requires an external HTTPS client path through Azure Front Door, no alternative router was substituted. The readiness gate was not reached, and `G1-warmup`, `G1-r01`, and `G1-r02` were not started. Their reserved shipment IDs and partition keys remain unused/planned.

Cost Management actual-cost retrieval was unavailable/delayed during preflight and was treated as non-blocking as planned. Before deployment, the subscription budget was confirmed at EUR 50 monthly, AKS 1.35.7 was confirmed in Italy North and Norway East, and Norway East quota was confirmed at 6 total regional vCPUs and 4 DASv4-family vCPUs—the exact frozen Region B requirement.

After the blocker, Region A AKS, Region B AKS, and PostgreSQL were stopped. Event Hubs, ACR, database storage, and the stopped Region B topology remain retained. Azure PostgreSQL flexible server may auto-start after seven days unless stopped again or intentionally resumed.

