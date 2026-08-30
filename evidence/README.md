# Dissertation Evidence Index

This directory contains evidence collected while evaluating the Event Aggregation Service. Do not store passwords, credentials, connection strings, access tokens, or other secrets here.

## Phase 1: Local Docker Compose

- `01-docker-baseline/`: Docker Compose startup, running services, health/readiness, PostgreSQL schema, and normal end-to-end event flow.
- `02-data-integrity/`: Duplicate-event idempotency, out-of-order version protection, and replay evidence.
- `03-db-failure-recovery/`: PostgreSQL transaction rollback, Kafka offset handling, Docker automatic restart, event redelivery, and the DB-commit/offset-commit crash window.

Each Phase 1 directory contains:

- `commands.md`: Exact commands personally executed during evidence collection.
- `results.md`: Observed results, test IDs, offsets, row counts, anomalies, and PASS/FAIL decisions.

Results must only be recorded after they are observed. Screenshots and relevant plain-text output can be stored beside these files.

## Later Phases and Final Azure Status

- `04-kubernetes-pod-failover/`: Completed local Kubernetes Aggregator and GraphQL API Pod-failure evidence.
- `05-azure-baseline/`: Completed E1 Azure baseline evidence: one discarded warm-up and three measured runs.
- `06-azure-az/`: Completed F1 simulated zonal-resilience evidence: one discarded warm-up and two measured runs.
- `07-azure-region/`: G1 infrastructure/blocker evidence only. G1 was blocked before workload execution by the Azure Front Door subscription constraint; G2 was not executed.
- `08-azure-closeout/`: Final v1.0.9 matrix, cost status, sanitized pre-teardown inventories, deletion activity and zero-resource verification.

The Azure experimental programme is closed. Do not create new thesis Azure resources or infer empirical G1/G2 results from the retained design artifacts.
