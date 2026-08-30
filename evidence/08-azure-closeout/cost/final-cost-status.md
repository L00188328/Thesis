# Final Azure Cost Status

- Billing currency: EUR.
- Gross experiment ceiling: EUR 50.
- Intentionally retained Azure item: subscription-level `thesis-experiments` EUR 50 monthly budget guard; non-billable.
- E1 actual cost: pending Cost Management reporting; retain `evidence/05-azure-baseline/cost/E1-cost-window.md` separately.
- F1 actual cost: pending Cost Management reporting; retain `evidence/06-azure-az/cost/F1-cost-window.md` separately.
- G1 preparation actual cost: pending Cost Management reporting; includes Region A/PostgreSQL restart and temporary Region B infrastructure preparation only. No G1 workload or performance result exists.
- G2 actual cost: no experimental execution; no G2 infrastructure/workload was started.
- Final actual-cost query status: HTTP 429 (`Too Many Requests`) on 2026-08-30; no amount returned.
- Historical planning estimate: `evidence/azure-burn-estimate-v1.0.8.json`; it is not actual expenditure and must not be presented as such.
- Billing-attribution evidence: `evidence/08-azure-closeout/pre-teardown/` preserves sanitized resource paths, SKUs, regions, tags, deployment timestamps and activity timestamps.
- Final billable-resource verification: `evidence/08-azure-closeout/post-teardown/` contains empty thesis inventories for AKS, PostgreSQL, Event Hubs, ACR, Front Door, all thesis resources and all thesis resource groups.

No missing cost is fabricated. Delayed actual charges may be retrieved from Azure billing later without recreating any resource.
