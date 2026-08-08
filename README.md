# Thesis Prototype - Phase 1 MVP


## Summary
This protoype is part of a thesis to evaluate fail over methods and busines continuity for domain driven, event driven architecures in the postal sector. 


Local event-driven prototype for parcel shipment aggregation.

## Components

- `producer-logistic-center`: simulates logistics-center domain events
- `producer-delivery-base`: simulates Delivery Base domain events
- `redpanda`: Kafka-compatible event streaming broker
- `aggregator`: consumes events and builds a shipment projection in PostgreSQL
- `api`: GraphQL API + simple web UI
- `postgres`: persistence for raw events + projection

## Run

```bash
docker compose up --build
```

## Kubernetes Baseline

- Helm-free manifests for local `kind` or `k3d` testing live in `k8s/`.
- The manifests assume PostgreSQL and Redpanda remain external shared dependencies; update the placeholder ConfigMap and Secret values before applying them.

## Open

- UI: http://localhost:8000/
- GraphQL endpoint: http://localhost:8000/graphql

## Example GraphQL Queries

```graphql
query {
  shipments(limit: 10) {
    shipmentId
    latestEventType
    latestEventDomain
    latestLocation
    latestEventTime
  }
}
```

```graphql
query {
  shipment(shipmentId: "SHP-0001") {
    shipmentId
    latestEventType
    latestEventDomain
    latestLocation
    latestEventTime
    timeline {
      occurredAt
      domain
      eventType
      location
      details
    }
  }
}
```

## Notes

- This is the baseline architecture for your dissertation experiments.
- The comparative HA scope is the application-layer `aggregator` and `api` services, while PostgreSQL and the event-streaming platform remain shared supporting dependencies.
- The simulator's shared shipment state is test infrastructure only and not part of the logical enterprise architecture.
- The `aggregator` and `api` services expose `/health` and `/ready` endpoints for later Kubernetes liveness and readiness probes.
- Shipment projections now use monotonic `event_version` values so an older event cannot overwrite a newer materialized state.
- Next phases can add HA variants (replicas, multi-node, active-passive, active-active) and metrics automation.
