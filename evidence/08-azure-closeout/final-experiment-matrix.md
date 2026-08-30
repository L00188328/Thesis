# Final Experiment Matrix

| Configuration | Status | Runs executed | Empirical evidence | Reason if not executed |
|---|---|---|---|---|
| Local Kubernetes Pod HA | COMPLETED | D4 Aggregator Pod failure; D5 API Pod failure | `evidence/04-kubernetes-pod-failover/` | Not applicable |
| E1 Azure baseline | COMPLETED | 1 discarded warm-up + 3 measured | `evidence/05-azure-baseline/` | Not applicable |
| F1 simulated zonal resilience | COMPLETED | 1 discarded warm-up + 2 measured | `evidence/06-azure-az/` | Not applicable |
| G1 active-passive | BLOCKED BEFORE WORKLOAD EXECUTION — Azure subscription constraint | 0 | `evidence/07-azure-region/g1-blocked-2026-08-30/` contains blocker/infrastructure evidence only | Azure for Students rejected the frozen Azure Front Door resource |
| G2 active-active | NOT EXECUTED | 0 | Design/IaC only; no empirical results | The same Front Door subscription constraint made the frozen routing design unavailable |

G1/G2 are not experimental FAIL results. No warm-up or measured workload began for either configuration, and no empirical metric may be inferred from their designs or the G1 preparation attempt.

