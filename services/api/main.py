import json
import os
from time import perf_counter
from datetime import datetime
from typing import Any

import psycopg
from ariadne import ObjectType, QueryType, gql, make_executable_schema
from ariadne.asgi import GraphQL
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from services.common.db_wait import database_ready, wait_for_db
from services.common.logging_utils import configure_logging, get_instance_id, utc_now_iso
from services.common.schema_init import ensure_projection_schema

DATABASE_URL = os.environ["DATABASE_URL"]
SERVICE_NAME = "api"
INSTANCE_ID = get_instance_id(SERVICE_NAME)
AZURE_REGION = os.getenv("AZURE_REGION", "local")
logger = configure_logging(SERVICE_NAME)

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
      eventVersion: Int!
      domain: String!
      eventType: String!
      occurredAt: String!
      location: String!
      details: String!
    }

    type ShipmentSummary {
      shipmentId: String!
      latestEventVersion: Int!
      latestEventType: String!
      latestEventDomain: String!
      latestEventTime: String!
      latestLocation: String!
    }

    type Shipment {
      shipmentId: String!
      latestEventVersion: Int!
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
        "latestEventVersion": row["latest_event_version"],
        "latestEventType": row["latest_event_type"],
        "latestEventDomain": row["latest_event_domain"],
        "latestEventTime": stringify_dt(row["latest_event_time"]),
        "latestLocation": row["latest_location"],
    }


def row_to_event(row: dict[str, Any]) -> dict[str, str]:
    return {
        "eventId": row["event_id"],
        "shipmentId": row["shipment_id"],
        "eventVersion": row["event_version"],
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
        SELECT shipment_id, latest_event_version, latest_event_type, latest_event_domain, latest_event_time, latest_location
        FROM current_shipment_state
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
        SELECT shipment_id, latest_event_version, latest_event_type, latest_event_domain, latest_event_time, latest_location
        FROM current_shipment_state
        WHERE shipment_id = %s
        """,
        (shipmentId,),
    )
    if not projection:
        return None

    events = fetchall(
        """
        SELECT event_id, shipment_id, event_version, domain, event_type, occurred_at, location, details
        FROM all_shipment_events
        WHERE shipment_id = %s
        ORDER BY event_version ASC, occurred_at ASC
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


@app.middleware("http")
async def log_requests(request: Request, call_next: Any) -> Any:
    request_timestamp = utc_now_iso()
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        latency_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "request_failed",
            extra={
                "request_timestamp": request_timestamp,
                "response_status": 500,
                "latency_ms": latency_ms,
                "method": request.method,
                "path": request.url.path,
            },
        )
        raise

    latency_ms = round((perf_counter() - started_at) * 1000, 2)
    response.headers["X-Instance-ID"] = INSTANCE_ID
    response.headers["X-Region"] = AZURE_REGION
    logger.info(
        "request_complete",
        extra={
            "request_timestamp": request_timestamp,
            "response_status": response.status_code,
            "latency_ms": latency_ms,
            "method": request.method,
            "path": request.url.path,
            "region": AZURE_REGION,
        },
    )
    return response


@app.on_event("startup")
def startup() -> None:
    wait_for_db(DATABASE_URL)
    ensure_projection_schema(DATABASE_URL)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "instanceId": INSTANCE_ID,
        "timestamp": utc_now_iso(),
    }


@app.get("/ready")
def ready() -> JSONResponse:
    ready_now = database_ready(
        DATABASE_URL,
        "SELECT 1 FROM current_shipment_state LIMIT 1",
    )
    payload = {
        "status": "ok" if ready_now else "not_ready",
        "service": SERVICE_NAME,
        "instanceId": INSTANCE_ID,
        "timestamp": utc_now_iso(),
    }
    return JSONResponse(
        content=payload,
        status_code=200 if ready_now else 503,
    )

app.mount("/graphql", graphql_app)
app.mount("/", StaticFiles(directory="/app/services/ui", html=True), name="ui")
