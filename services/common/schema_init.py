import psycopg


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS shipment_events (
        event_id TEXT PRIMARY KEY,
        shipment_id TEXT NOT NULL,
        event_version BIGINT NOT NULL,
        domain TEXT NOT NULL,
        event_type TEXT NOT NULL,
        occurred_at TIMESTAMPTZ NOT NULL,
        location TEXT NOT NULL,
        details JSONB NOT NULL
    )
    """,
    """
    ALTER TABLE shipment_events
    ADD COLUMN IF NOT EXISTS event_version BIGINT NOT NULL DEFAULT 0
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_shipment_events_shipment_id
    ON shipment_events (shipment_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_shipment_events_occurred_at
    ON shipment_events (occurred_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS shipment_projection (
        shipment_id TEXT PRIMARY KEY,
        latest_event_version BIGINT NOT NULL,
        latest_event_type TEXT NOT NULL,
        latest_event_domain TEXT NOT NULL,
        latest_event_time TIMESTAMPTZ NOT NULL,
        latest_location TEXT NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    ALTER TABLE shipment_projection
    ADD COLUMN IF NOT EXISTS latest_event_version BIGINT NOT NULL DEFAULT 0
    """,
)


def ensure_projection_schema(database_url: str) -> None:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for statement in SCHEMA_STATEMENTS:
                cur.execute(statement)
        conn.commit()
