# Thesis Prototype - Phase 1 MVP


## Summary
This protoype is part of a thesis to evaluate fail over methods and busines continuity for domain driven, event driven architecures in the postal sector. 


Local event-driven prototype for parcel shipment aggregation.

## Components

- `producer-logistic-center`: simulates logistics-center domain events
- `producer-delivery-tour`: simulates delivery-tour domain events
- `redpanda`: Kafka-compatible event streaming broker
- `aggregator`: consumes events and builds a shipment projection in PostgreSQL
- `api`: GraphQL API + simple web UI
- `postgres`: persistence for raw events + projection

## Run

```bash
docker compose up --build
```

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
- Next phases can add HA variants (replicas, multi-node, blue/green, geo strategies) and metrics automation.
