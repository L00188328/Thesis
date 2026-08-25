# Docker Baseline Commands

## A1. Clean Local Environment

docker compose down -v --remove-orphans

docker compose up --build -d

## A2. Running Containers

docker compose ps

## A3. Health and Readiness

curl -i -s http://localhost:8081/health; echo
curl -i -s http://localhost:8081/ready; echo
curl -i -s http://localhost:8000/health; echo
curl -i -s http://localhost:8000/ready; echo

## A4. PostgreSQL Schema

docker compose exec -T postgres psql -U postgres -d shipments -c "\dt"
## A5. End-to-End Event Flow

docker compose exec -T postgres psql -U postgres -d shipments -P pager=off -c "SELECT shipment_id, COUNT(*) AS event_count, MAX(event_version) AS highest_version, string_agg(DISTINCT domain, ', ' ORDER BY domain) AS domains, MAX(occurred_at) AS latest_event FROM all_shipment_events GROUP BY shipment_id ORDER BY latest_event DESC LIMIT 5;"



docker compose stop producer-logistic-center producer-delivery-base


docker compose exec -T redpanda rpk group describe shipment-aggregator


docker compose exec -T postgres psql -U postgres -d shipments -P pager=off -c "SELECT shipment_id, latest_event_version, latest_event_type, latest_event_domain, latest_location, latest_event_time FROM current_shipment_state WHERE shipment_id = 'SHP-0026'; SELECT COUNT(*) AS history_rows, COUNT(DISTINCT event_id) AS unique_event_ids, MIN(event_version) AS first_version, MAX(event_version) AS highest_version, string_agg(DISTINCT domain, ', ' ORDER BY domain) AS domains FROM all_shipment_events WHERE shipment_id = 'SHP-0026'; SELECT event_id, event_version, domain, event_type, location, occurred_at FROM all_shipment_events WHERE shipment_id = 'SHP-0026' ORDER BY event_version DESC LIMIT 8;"



curl -s -X POST http://localhost:8000/graphql/ \
  -H 'Content-Type: application/json' \
  --data '{"query":"query($shipmentId: String!) { shipment(shipmentId: $shipmentId) { shipmentId latestEventVersion latestEventType latestEventDomain latestLocation latestEventTime } }","variables":{"shipmentId":"SHP-0026"}}' \
  | python3 -m json.tool


  curl -s -X POST http://localhost:8000/graphql/ \
  -H 'Content-Type: application/json' \
  --data '{"query":"query($shipmentId: String!) { shipment(shipmentId: $shipmentId) { shipmentId timeline { eventId eventVersion domain eventType location occurredAt } } }","variables":{"shipmentId":"SHP-0026"}}' \
  | tee evidence/01-docker-baseline/graphql-history-SHP-0026.json \
  | python3 -c 'import json, sys; payload=json.load(sys.stdin); events=payload["data"]["shipment"]["timeline"]; print(json.dumps({"shipmentId": payload["data"]["shipment"]["shipmentId"], "eventCount": len(events), "firstEvent": events[0], "latestEvent": events[-1]}, indent=2))'