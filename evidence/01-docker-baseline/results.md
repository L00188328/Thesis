# Docker Baseline Results

Complete each section only after observing the result.

## A1. Clean Local Environment

- Date/time: 2026-08-25 (terminal time not captured)
- Test purpose: Establish a clean Docker Compose environment with newly created containers, network, Kafka storage, and PostgreSQL storage.
- Controlled test IDs: Not applicable
- Expected result: Existing Compose resources are removed; all application images build; Redpanda, PostgreSQL, Aggregator, GraphQL API, Logistic Centre producer, and Delivery Base producer start without errors.
- Actual result: Existing containers and the `thesis_default` network were removed. All four application images built successfully. The network was recreated and all six required containers reported `Started`.
- PASS/FAIL: PASS
- Relevant Kafka offsets: Not applicable
- Relevant database row counts: Not applicable
- Evidence files: `Screenshots/A-01A-clean-compose-teardown.jpg` and `Screenshots/A-01B-clean-compose-build-and-start.jpg`.
- Anomalies or discarded attempts: Docker Compose printed an informational suggestion about enabling `COMPOSE_BAKE`; no build or startup failure occurred. The terminal also printed an unrelated local mail notification.

## A2. Running Containers

- Date/time: 2026-08-25 (terminal time not captured)
- Test purpose: Demonstrate that every service required by the local event-driven architecture is running under Docker Compose.
- Expected result: Redpanda, PostgreSQL, Aggregator, GraphQL API, Logistic Centre producer, and Delivery Base producer all report `Up`, with the expected host ports published.
- Actual result: All six required containers reported `Up 7 minutes`. Aggregator exposed `8081`, API exposed `8000`, PostgreSQL exposed `5433`, and Redpanda exposed Kafka on `19092`.
- PASS/FAIL: PASS
- Evidence files: `Screenshots/A-02A-docker-desktop-services-running.jpg` and `Screenshots/A-02B-compose-services-running.jpg`.
- Anomalies or discarded attempts: None observed.

## A3. Health and Readiness

- Date/time: 2026-08-25 11:08:44–11:09:53 UTC
- Test purpose: Demonstrate that the Aggregator and GraphQL API processes are alive and ready to serve traffic using their dependencies.
- Expected result: `/health` and `/ready` return HTTP 200 with `status: ok` for both `aggregator` and `api`.
- Actual result: Aggregator `/health` and `/ready` returned HTTP/1.0 200 with `status: ok`, service `aggregator`, and instance `aggregator-local`. API `/health` and `/ready` returned HTTP/1.1 200 with `status: ok`, service `api`, and instance `api-local`.
- PASS/FAIL: PASS
- Evidence files: `Screenshots/A-03A-aggregator-health-ready-and-api-health.jpg` and `Screenshots/A-03B-api-readiness.jpg`.
- Anomalies or discarded attempts: None observed. The API readiness command was captured approximately 69 seconds after the other three checks and still returned HTTP 200.

## A4. PostgreSQL Schema

- Date/time: 2026-08-25 (terminal time not captured)
- Test purpose: Demonstrate that PostgreSQL contains the historical-event and materialised-current-state tables required by the architecture.
- Expected result: `all_shipment_events` and `current_shipment_state` exist in the `public` schema; the simulation-only table may also exist.
- Actual result: PostgreSQL listed three public tables owned by `postgres`: `all_shipment_events`, `current_shipment_state`, and `shipment_simulation_state`.
- PASS/FAIL: PASS
- Relevant database objects: `public.all_shipment_events`, `public.current_shipment_state`, and `public.shipment_simulation_state`.
- Evidence files: `Screenshots/A-04A-postgresql-schema-tables.jpg`.
- Anomalies or discarded attempts: None observed.

## A5. End-to-End Event Flow

- Date/time: 2026-08-25 (capture time not fully recorded)
- Test purpose: Demonstrate the normal Producer → Redpanda → Aggregator → PostgreSQL → GraphQL API → UI event flow.
- Controlled shipment ID: `SHP-0026`
- Controlled event IDs: Producer-generated UUIDs; first `f59dded3-e5d4-4f99-b39d-d6abd3ceaa9a`, latest `ddccb2a9-b070-4e1d-aec6-aac929f47cf9`.
- Expected result: Both producer domains appear in history; Kafka drains to zero lag; PostgreSQL history and current state agree; GraphQL returns the same current state and complete ordered history; UI renders the shipment timeline.
- Actual result: Producers were stopped after generating the evidence dataset. The Aggregator group was stable with one member and zero lag. PostgreSQL contained 34 unique historical events across versions 1–34 and both domains, with current state at version 34 (`ParcelLoadedForTransit`, `LogisticCenter`, `Cork Hub`). GraphQL returned the matching current state and all 34 ordered events. The user confirmed that the UI displayed the expected shipment timeline successfully.
- PASS/FAIL: PASS
- Relevant Kafka offsets: `delivery-base-events` committed/log-end `442/442`, lag 0; `logistic-center-events` committed/log-end `621/621`, lag 0.
- Relevant database row counts: 34 historical rows and 34 distinct event IDs; one current-state row.
- Evidence files: `Screenshots/A-05A-producer-generated-shipment-overview.jpg`, `Screenshots/A-05B-kafka-zero-lag-after-producers-stopped.jpg`, `Screenshots/A-05C-docker-desktop-producers-stopped.jpg`, `Screenshots/A-05D-postgresql-shipment-state-and-history.jpg`, `Screenshots/A-05E-graphql-current-shipment-state.jpg`, `Screenshots/A-05F-graphql-shipment-history.jpg`, `Screenshots/A-05G-ui-shipment-timeline.jpg`, `Screenshots/A-05F1-graphql-history-summary-SHP-0026.json`, and `Screenshots/A-05F2-graphql-history-full-SHP-0026.json`.
- Anomalies or discarded attempts: Terminal output visually duplicated part of the Kafka member columns, but offsets and lag remained readable. `Screenshots/A-05F1-graphql-history-summary-SHP-0026.json` is a compact summary containing the event count and first/latest events, while `Screenshots/A-05F2-graphql-history-full-SHP-0026.json` is the separate complete 34-event raw GraphQL response.
