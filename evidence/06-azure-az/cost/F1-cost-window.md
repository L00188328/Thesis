# F1 Cost Window

- Currency: EUR
- Gross study ceiling: EUR 50
- Frozen estimated F1 hourly burn while both application pools run: EUR 0.373374
- Frozen estimated two measured-run allocation: EUR 0.186687 (measured windows only; transition, warm-up, recovery and ancillary meters are in the conservative fixed remaining allocation)
- E1 non-zonal cluster deletion command/completion UTC: 2026-08-30T11:57:40.564954Z / 2026-08-30T12:03:53.441472Z
- F1 AKS deployment command/completion UTC: 2026-08-30T12:03:53.510209Z / 2026-08-30T12:10:30.762198Z
- F1 application readiness gate UTC: 2026-08-30T12:15:51.697645Z
- F1 discarded warm-up T1/window completion UTC: 2026-08-30T12:22:02.864807Z / 2026-08-30T12:32:05.174911Z
- F1-r01 T1/window completion UTC: 2026-08-30T12:39:45.800005Z / 2026-08-30T12:49:48.365570Z
- F1-r02 T1/window completion UTC: 2026-08-30T12:54:25.661426Z / 2026-08-30T13:04:28.100245Z
- Cost-containment command/completion UTC: 2026-08-30T13:21:45.266003Z / 2026-08-30T13:25:24.047783Z
- Final state: Region A AKS `Stopped`; PostgreSQL `Stopped`; Event Hubs and ACR retained
- Actual Cost Management status: pending reporting delay; the successful REST query returned the expected columns but no rows for the same-day F1 window

Actual accrued E1 cost remains separate in `evidence/05-azure-baseline/cost/E1-cost-window.md`. Delayed F1 actual cost must be retrieved later using the retained resource groups, tags, inventory and timestamps; no value is fabricated from the empty same-day response.
