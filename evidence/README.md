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

## Later Phases

- `04-kubernetes-pod-failover/`: Placeholder for future local Kubernetes pod-failover evidence.
- `05-azure-baseline/`: Placeholder for future Azure baseline evidence.
- `06-azure-az/`: Placeholder for future Azure availability-zone evidence.
- `07-azure-region/`: Placeholder for future Azure regional-failure evidence.

Kubernetes and Azure evidence collection is outside Phase 1 and must not begin until explicitly requested.
