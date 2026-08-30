# Azure experiment infrastructure

Methodology version 1.0.3 uses four staged Bicep deployments:

1. `shared.bicep` creates ACR, one Event Hubs namespace with two two-partition Event Hubs, and PostgreSQL Flexible Server.
2. `aks-region.bicep` creates one AKS cluster, a system pool, and the declared application user pools.
3. `acr-pull.bicep` grants each deployed cluster's kubelet identity `AcrPull` on the shared registry. This is separate because the AKS-created kubelet identity is queried after cluster creation.
4. `front-door.bicep` creates the frozen Azure Front Door Standard endpoint, origin group, origins, and GraphQL route. Clients use HTTPS; the controlled Front Door-to-AKS origin connection uses HTTP port 80 as frozen in protocol version 1.0.3.

Parameter files under `parameters/` are reusable reviewed defaults. Secrets and deployment-specific origin hostnames are supplied at deployment time and must never be committed.

No deployment command should be run until `evidence/azure-experiment-freeze.json` is complete and explicit approval has been given.

The region parameter files pin AKS `1.35.7`, selected on 2026-08-29 as the latest patch offered to the experiment subscription in both `westeurope` and `northeurope`. Re-run `az aks get-versions` in both regions immediately before deployment; if availability has changed, stop and amend the freeze rather than silently selecting another version. This metadata query does not create resources.

All application pools use `Standard_D2as_v4`. Protocol v1.0.3 amended the original DASv5 selection before E1 because the experiment subscription reported zero DASv5-family vCPU quota in both planned regions, while DASv4 had sufficient quota. The node counts and topology were not changed.

Region A reuses `aks-region.bicep` through three explicit parameter sets:

- `region-a-e1.bicepparam`: one non-zonal application node; it does not inherit F1 pools.
- `region-a-e2.bicepparam`: one non-zonal two-node application pool.
- `region-a-f1.bicepparam`: two one-node zone-aligned application pools; reused by the later Region A multi-region configurations.

These are mutually exclusive complete application-pool topologies. Do not apply the F1 set incrementally over E2 while retaining the non-zonal `app` pool: recreate the experiment cluster from the selected parameter set, or remove the obsolete pool during the approved topology transition, then verify the declared pool list before installing workloads. This prevents F1/G1/G2 pods from being scheduled onto an inherited E1/E2 application pool.

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
