# Data Integrity Commands

Record the exact commands actually executed for each evidence step. Do not add commands that were not run.

## B1. Duplicate Event

docker compose exec -T postgres psql -U postgres -d shipments -c "SELECT COUNT(*) AS history_before FROM all_shipment_events WHERE event_id = 'dup-evid-evt-001'; SELECT COUNT(*) AS state_before FROM current_shipment_state WHERE shipment_id = 'TST-DUP-EVID-001';"

printf '%s\n' '{"event_id":"dup-evid-evt-001","shipment_id":"TST-DUP-EVID-001","event_version":1,"domain":"LogisticCenter","event_type":"ParcelReceivedAtHub","occurred_at":"2026-08-25T11:40:00+00:00","location":"Dublin Evidence Hub","details":{"test":"duplicate-evidence","destinationCity":"Dublin"}}' | docker compose exec -T redpanda rpk topic produce logistic-center-events --compression none --partition 0 --key TST-DUP-EVID-001

printf '%s\n' '{"event_id":"dup-evid-evt-001","shipment_id":"TST-DUP-EVID-001","event_version":1,"domain":"LogisticCenter","event_type":"ParcelReceivedAtHub","occurred_at":"2026-08-25T11:40:00+00:00","location":"Dublin Evidence Hub","details":{"test":"duplicate-evidence","destinationCity":"Dublin"}}' | docker compose exec -T redpanda rpk topic produce logistic-center-events --compression none --partition 0 --key TST-DUP-EVID-001

docker compose exec -T postgres psql -U postgres -d shipments -P pager=off -c "SELECT event_id, shipment_id, event_version, domain, event_type, occurred_at, location, details FROM all_shipment_events WHERE event_id = 'dup-evid-evt-001'; SELECT COUNT(*) AS historical_row_count FROM all_shipment_events WHERE event_id = 'dup-evid-evt-001'; SELECT shipment_id, latest_event_version, latest_event_type, latest_event_domain, latest_location, latest_event_time FROM current_shipment_state WHERE shipment_id = 'TST-DUP-EVID-001';"

docker compose logs --since 10m --no-color aggregator | grep 'dup-evid-evt-001'

docker compose exec -T redpanda rpk group describe shipment-aggregator
## B2. Out-of-Order Event

docker compose exec -T postgres psql -U postgres -d shipments -c "SELECT COUNT(*) AS history_before FROM all_shipment_events WHERE event_id IN ('ooo-evid-evt-v5', 'ooo-evid-evt-v3'); SELECT COUNT(*) AS state_before FROM current_shipment_state WHERE shipment_id = 'TST-OOO-EVID-001';"

printf '%s\n' '{"event_id":"ooo-evid-evt-v5","shipment_id":"TST-OOO-EVID-001","event_version":5,"domain":"LogisticCenter","event_type":"ParcelLoadedForTransit","occurred_at":"2026-08-25T12:10:00+00:00","location":"Cork Evidence Hub","details":{"test":"out-of-order-evidence","sequence":"newer-first"}}' | docker compose exec -T redpanda rpk topic produce logistic-center-events --compression none --partition 0 --key TST-OOO-EVID-001

printf '%s\n' '{"event_id":"ooo-evid-evt-v3","shipment_id":"TST-OOO-EVID-001","event_version":3,"domain":"LogisticCenter","event_type":"ParcelSorted","occurred_at":"2026-08-25T12:00:00+00:00","location":"Cork Evidence Hub","details":{"test":"out-of-order-evidence","sequence":"older-second"}}' | docker compose exec -T redpanda rpk topic produce logistic-center-events --compression none --partition 0 --key TST-OOO-EVID-001


docker compose exec -T postgres psql -U postgres -d shipments -P pager=off -c "SELECT event_id, event_version, event_type, occurred_at, details FROM all_shipment_events WHERE shipment_id = 'TST-OOO-EVID-001' ORDER BY event_version DESC; SELECT COUNT(*) AS history_rows, COUNT(DISTINCT event_id) AS unique_event_ids FROM all_shipment_events WHERE shipment_id = 'TST-OOO-EVID-001'; SELECT shipment_id, latest_event_version, latest_event_type, latest_event_domain, latest_location, latest_event_time FROM current_shipment_state WHERE shipment_id = 'TST-OOO-EVID-001';"


docker compose logs --since 10m --no-color aggregator | grep 'TST-OOO-EVID-001'

docker compose exec -T redpanda rpk group describe shipment-aggregator

## B3. Replay

_Not yet run._
