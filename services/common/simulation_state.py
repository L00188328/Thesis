import psycopg
from psycopg.errors import UniqueViolation


def init_state_table(conn: psycopg.Connection) -> None:
    # Concurrent CREATE TABLE IF NOT EXISTS can still race on PostgreSQL system catalogs.
    # Serialize startup DDL across producers with a transaction-level advisory lock.
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (9042101,))
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS shipment_simulation_state (
                    shipment_id TEXT PRIMARY KEY,
                    stage SMALLINT NOT NULL DEFAULT 0,
                    destination_city TEXT,
                    hub TEXT,
                    attempts SMALLINT NOT NULL DEFAULT 0,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        except UniqueViolation:
            # If another transaction created it in a tight race window, keep startup alive.
            conn.rollback()
            return
    conn.commit()


def seed_shipments(conn: psycopg.Connection, shipment_ids: list[str]) -> None:
    with conn.cursor() as cur:
        for shipment_id in shipment_ids:
            cur.execute(
                """
                INSERT INTO shipment_simulation_state (shipment_id)
                VALUES (%s)
                ON CONFLICT (shipment_id) DO NOTHING
                """,
                (shipment_id,),
            )
    conn.commit()


def recycle_delivered(conn: psycopg.Connection, recycle_after_seconds: int = 45) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE shipment_simulation_state
            SET
                stage = 0,
                destination_city = NULL,
                hub = NULL,
                attempts = 0,
                updated_at = NOW()
            WHERE stage = 5
              AND updated_at < NOW() - (%s::INT * INTERVAL '1 second')
            """,
            (recycle_after_seconds,),
        )
    conn.commit()


def claim_next_for_logistics(conn: psycopg.Connection) -> dict | None:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT shipment_id, stage, destination_city, hub, attempts
            FROM shipment_simulation_state
            WHERE stage IN (0, 1, 2)
            ORDER BY stage DESC, updated_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return None

        return dict(row)


def claim_next_for_delivery(conn: psycopg.Connection) -> dict | None:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT shipment_id, stage, destination_city, hub, attempts
            FROM shipment_simulation_state
            WHERE stage IN (3, 4)
            ORDER BY stage DESC, updated_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return None

        return dict(row)


def update_state(
    conn: psycopg.Connection,
    shipment_id: str,
    stage: int,
    destination_city: str | None,
    hub: str | None,
    attempts: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE shipment_simulation_state
            SET
                stage = %s,
                destination_city = %s,
                hub = %s,
                attempts = %s,
                updated_at = NOW()
            WHERE shipment_id = %s
            """,
            (stage, destination_city, hub, attempts, shipment_id),
        )
    conn.commit()
