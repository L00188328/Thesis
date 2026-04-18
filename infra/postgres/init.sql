CREATE TABLE IF NOT EXISTS shipment_events (
    event_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    location TEXT NOT NULL,
    details JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_shipment_events_shipment_id ON shipment_events (shipment_id);
CREATE INDEX IF NOT EXISTS idx_shipment_events_occurred_at ON shipment_events (occurred_at);

CREATE TABLE IF NOT EXISTS shipment_projection (
    shipment_id TEXT PRIMARY KEY,
    latest_event_type TEXT NOT NULL,
    latest_event_domain TEXT NOT NULL,
    latest_event_time TIMESTAMPTZ NOT NULL,
    latest_location TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
