import json
import os
from datetime import datetime
from typing import Any

import psycopg
from ariadne import ObjectType, QueryType, gql, make_executable_schema
from ariadne.asgi import GraphQL
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@postgres:5432/shipments",
)

def fetchall(query: str, params: tuple = ()) -> list[dict]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def stringify_dt(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


type_defs = gql(
    """
    type Event {
      eventId: String!
      shipmentId: String!
      domain: String!
      eventType: String!
      occurredAt: String!
      location: String!
      details: String!
    }

    type ShipmentSummary {
      shipmentId: String!
      latestEventType: String!
      latestEventDomain: String!
      latestEventTime: String!
      latestLocation: String!
    }

    type Shipment {
      shipmentId: String!
      latestEventType: String!
      latestEventDomain: String!
      latestEventTime: String!
      latestLocation: String!
      timeline: [Event!]!
    }

    type Query {
      shipments(limit: Int = 20): [ShipmentSummary!]!
      shipment(shipmentId: String!): Shipment
    }
    """
)

query = QueryType()


def row_to_summary(row: dict[str, Any]) -> dict[str, str]:
    return {
        "shipmentId": row["shipment_id"],
        "latestEventType": row["latest_event_type"],
        "latestEventDomain": row["latest_event_domain"],
        "latestEventTime": stringify_dt(row["latest_event_time"]),
        "latestLocation": row["latest_location"],
    }


def row_to_event(row: dict[str, Any]) -> dict[str, str]:
    return {
        "eventId": row["event_id"],
        "shipmentId": row["shipment_id"],
        "domain": row["domain"],
        "eventType": row["event_type"],
        "occurredAt": stringify_dt(row["occurred_at"]),
        "location": row["location"],
        "details": json.dumps(row["details"]),
    }


@query.field("shipments")
def resolve_shipments(*_: Any, limit: int = 20) -> list[dict[str, str]]:
    rows = fetchall(
        """
        SELECT shipment_id, latest_event_type, latest_event_domain, latest_event_time, latest_location
        FROM shipment_projection
        ORDER BY latest_event_time DESC NULLS LAST
        LIMIT %s
        """,
        (limit,),
    )
    return [row_to_summary(row) for row in rows]


@query.field("shipment")
def resolve_shipment(*_: Any, shipmentId: str) -> dict[str, Any] | None:
    projection = fetchall(
        """
        SELECT shipment_id, latest_event_type, latest_event_domain, latest_event_time, latest_location
        FROM shipment_projection
        WHERE shipment_id = %s
        """,
        (shipmentId,),
    )
    if not projection:
        return None

    events = fetchall(
        """
        SELECT event_id, shipment_id, domain, event_type, occurred_at, location, details
        FROM shipment_events
        WHERE shipment_id = %s
        ORDER BY occurred_at ASC
        """,
        (shipmentId,),
    )

    shipment = row_to_summary(projection[0])
    shipment["timeline"] = [row_to_event(event) for event in events]
    return shipment


schema = make_executable_schema(type_defs, query)
graphql_app = GraphQL(schema, debug=True)

app = FastAPI(title="Shipment Aggregation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/graphql", graphql_app)
app.mount("/", StaticFiles(directory="/app/services/ui", html=True), name="ui")
