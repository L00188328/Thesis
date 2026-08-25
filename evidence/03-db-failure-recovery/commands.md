# Database Failure and Recovery Commands

Record the exact commands actually executed for each evidence step. Do not add commands that were not run. Clearly identify temporary test instrumentation and its removal.

## C1. Stable Starting State

docker inspect --format 'Container ID: {{.Id}} | Restart count: {{.RestartCount}} | Status: {{.State.Status}} | Started: {{.State.StartedAt}}' "$(docker compose ps -q aggregator)"

docker compose exec -T redpanda rpk group describe shipment-aggregator

## C2. Forced Database Transaction Failure

_Not yet run._

## C3. Automatic Recovery

_Not yet run._

## C4. DB Commit / Offset Commit Crash Window

_Not yet run._
