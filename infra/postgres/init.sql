CREATE TABLE IF NOT EXISTS all_shipment_events (
    event_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    event_version BIGINT NOT NULL,
    domain TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    location TEXT NOT NULL,
    details JSONB NOT NULL
);

ALTER TABLE all_shipment_events
ADD COLUMN IF NOT EXISTS event_version BIGINT NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_all_shipment_events_shipment_id ON all_shipment_events (shipment_id);
CREATE INDEX IF NOT EXISTS idx_all_shipment_events_occurred_at ON all_shipment_events (occurred_at);

CREATE TABLE IF NOT EXISTS current_shipment_state (
    shipment_id TEXT PRIMARY KEY,
    latest_event_version BIGINT NOT NULL,
    latest_event_type TEXT NOT NULL,
    latest_event_domain TEXT NOT NULL,
    latest_event_time TIMESTAMPTZ NOT NULL,
    latest_location TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE current_shipment_state
ADD COLUMN IF NOT EXISTS latest_event_version BIGINT NOT NULL DEFAULT 0;
