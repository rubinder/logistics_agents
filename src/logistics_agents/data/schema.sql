CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id          TEXT PRIMARY KEY,
    supplier       TEXT NOT NULL,
    expected_items JSONB NOT NULL,
    expected_date  TIMESTAMPTZ NOT NULL,
    destination_dc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    sku      TEXT NOT NULL,
    dc_id    TEXT NOT NULL,
    on_hand  INTEGER NOT NULL,
    reserved INTEGER NOT NULL,
    capacity INTEGER NOT NULL,
    PRIMARY KEY (sku, dc_id)
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id     TEXT PRIMARY KEY,
    po_id           TEXT,
    carrier         TEXT NOT NULL,
    tracking_number TEXT NOT NULL,
    reported_items  JSONB NOT NULL,
    reported_date   TIMESTAMPTZ NOT NULL,
    docs_present    BOOLEAN NOT NULL,
    damaged         BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS carrier_events (
    tracking_number TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    status          TEXT NOT NULL,
    eta             TIMESTAMPTZ,
    delayed         BOOLEAN NOT NULL,
    event_time      TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    run_id             TEXT PRIMARY KEY,
    shipment_id        TEXT NOT NULL,
    label              TEXT NOT NULL,
    exceptions         JSONB NOT NULL,
    recommended_actions JSONB NOT NULL,
    confidence         DOUBLE PRECISION NOT NULL,
    reasoning          TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT NOT NULL,
    node        TEXT NOT NULL,
    input_json  TEXT NOT NULL,
    output_json TEXT NOT NULL,
    latency_ms  INTEGER NOT NULL,
    tokens      INTEGER NOT NULL,
    cost_usd    DOUBLE PRECISION NOT NULL,
    model       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (run_id, node)
);

CREATE TABLE IF NOT EXISTS budget_ledger (
    id         BIGSERIAL PRIMARY KEY,
    run_id     TEXT NOT NULL,
    cost_usd   DOUBLE PRECISION NOT NULL,
    source     TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
