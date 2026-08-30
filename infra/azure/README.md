# Azure experiment infrastructure

Methodology version 1.0.8 retains four staged Bicep deployment templates:

1. `shared.bicep` creates ACR, one Event Hubs namespace with two two-partition Event Hubs, and PostgreSQL Flexible Server.
2. `aks-region.bicep` creates one AKS cluster, a system pool, and the declared application user pools.
3. `acr-pull.bicep` grants each deployed cluster's kubelet identity `AcrPull` on the shared registry. This is separate because the AKS-created kubelet identity is queried after cluster creation.
4. `front-door.bicep` creates the frozen Azure Front Door Standard endpoint, origin group, origins, and GraphQL route. Clients use HTTPS; the controlled Front Door-to-AKS origin connection uses HTTP port 80 as frozen in protocol version 1.0.8.

Parameter files under `parameters/` are reusable reviewed defaults. Secrets and deployment-specific origin hostnames are supplied at deployment time and must never be committed.

No further deployment command should be run until `evidence/azure-experiment-freeze-v1.0.8.json` is complete and explicit approval has been given. The original `evidence/azure-experiment-freeze.json` remains the unchanged historical E1 freeze.

The region parameter files pin AKS `1.35.7`, reverified on 2026-08-30 in policy-permitted `italynorth` and `norwayeast`. Re-run `az aks get-versions` in both regions immediately before deployment; if availability has changed, stop and amend the freeze rather than silently selecting another version. This metadata query does not create resources.

All application pools use `Standard_D2as_v4`. Protocol v1.0.3 amended the original DASv5 selection before E1 because the experiment subscription reported zero DASv5-family vCPU quota in both planned regions, while DASv4 had sufficient quota. The node counts and topology were not changed.

Protocol v1.0.4 froze `project`, `phase`, `configuration`, `run`, `owner` and applicable `regionRole` tags in every parameter set. Protocol v1.0.8 preserves completed E1's three measured repeats and uses two measured repeats for each remaining F1/G1/G2 configuration.

Protocol v1.0.5 uses Italy North as Region A and Norway East as Region B because the experiment subscription's enforced allowed-region policy rejected West Europe/North Europe before service-resource creation. Both amended regions support the frozen services, quotas, VM sizes, AKS patch and zones 1/2/3 without subscription-specific restrictions.

Region A reuses `aks-region.bicep` through three explicit parameter sets:

- `region-a-e1.bicepparam`: one non-zonal application node; it does not inherit F1 pools.
- `region-a-e2.bicepparam`: retained as previously validated reusable/historical IaC, but E2-A/E2-B are not future Azure execution targets under v1.0.8.
- `region-a-f1.bicepparam`: two one-node zone-aligned application pools; reused by the later Region A multi-region configurations.

These are mutually exclusive complete application-pool topologies. Transition directly from completed E1 to the F1 parameter set; recreate the experiment cluster from that set, or remove the obsolete non-zonal `app` pool during the approved topology transition, then verify the declared pool list before installing workloads. This prevents F1/G1/G2 Pods from being scheduled onto inherited E1 capacity.

Before compiling parameter files, provide these environment variables. Validation may use non-secret placeholders; deployment must use the real secret/host values without committing them:

```bash
export AZURE_POSTGRES_ADMIN_PASSWORD='validation-placeholder'
export REGION_A_ORIGIN_HOST='region-a.example.invalid'
export REGION_B_ORIGIN_HOST='region-b.example.invalid'
```

Validate locally:

```bash
az bicep build --file infra/azure/shared.bicep
az bicep build --file infra/azure/aks-region.bicep
az bicep build --file infra/azure/acr-pull.bicep
az bicep build --file infra/azure/front-door.bicep
az bicep build-params --file infra/azure/parameters/shared.bicepparam
az bicep build-params --file infra/azure/parameters/region-a-e1.bicepparam
az bicep build-params --file infra/azure/parameters/region-a-e2.bicepparam
az bicep build-params --file infra/azure/parameters/region-a-f1.bicepparam
az bicep build-params --file infra/azure/parameters/region-b.bicepparam
az bicep build-params --file infra/azure/parameters/front-door-g1.bicepparam
az bicep build-params --file infra/azure/parameters/front-door-g2.bicepparam
```
