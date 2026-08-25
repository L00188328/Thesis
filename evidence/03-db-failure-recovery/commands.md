# Database Failure and Recovery Commands

Record the exact commands actually executed for each evidence step. Do not add commands that were not run. Clearly identify temporary test instrumentation and its removal.

## C1. Stable Starting State

docker inspect --format 'Container ID: {{.Id}} | Restart count: {{.RestartCount}} | Status: {{.State.Status}} | Started: {{.State.StartedAt}}' "$(docker compose ps -q aggregator)"

printf '%s\n' '{"event_id":"postcommit-evid-evt-001","shipment_id":"TST-POSTCOMMIT-EVID-001","event_version":1,"domain":"LogisticCenter","event_type":"ParcelReceivedAtHub","occurred_at":"2026-08-25T15:10:00+00:00","location":"Linz Post-Commit Hub","details":{"test":"post-db-commit-crash-evidence","crashExpected":true}}' | docker compose exec -T redpanda rpk topic produce logistic-center-events --compression none --partition 0 --key TST-POSTCOMMIT-EVID-001

docker inspect --format 'Container ID: {{.Id}} | Restart count: {{.RestartCount}} | Status: {{.State.Status}} | Started: {{.State.StartedAt}}' "$(docker compose ps -q aggregator)"

docker compose logs --since 10m --no-color aggregator | grep -E 'postcommit-evid-evt-001|test_crash_after_db_commit|aggregator_started' | tail -n 30

docker compose exec -T postgres psql -U postgres -d shipments -P pager=off -c "SELECT event_id, shipment_id, event_version, domain, event_type, occurred_at, location, details FROM all_shipment_events WHERE event_id = 'postcommit-evid-evt-001'; SELECT COUNT(*) AS historical_row_count, COUNT(DISTINCT event_id) AS unique_event_ids FROM all_shipment_events WHERE event_id = 'postcommit-evid-evt-001'; SELECT shipment_id, latest_event_version, latest_event_type, latest_event_domain, latest_location, latest_event_time FROM current_shipment_state WHERE shipment_id = 'TST-POSTCOMMIT-EVID-001';"

docker compose exec -T redpanda rpk group describe shipment-aggregator

docker compose exec -T redpanda rpk group describe shipment-aggregator

## C2. Forced Database Transaction Failure

docker compose exec -T postgres psql -U postgres -d shipments -c "SELECT COUNT(*) AS history_before FROM all_shipment_events WHERE event_id = 'dbfail-evid-evt-001'; SELECT COUNT(*) AS state_before FROM current_shipment_state WHERE shipment_id = 'TST-DBFAIL-EVID-001'; SELECT COUNT(*) AS trigger_before FROM pg_trigger WHERE tgname = 'trg_fail_db_evidence';"

docker compose exec -T postgres psql -U postgres -d shipments -v ON_ERROR_STOP=1 -c "CREATE FUNCTION fail_db_evidence() RETURNS trigger LANGUAGE plpgsql AS \$\$ BEGIN IF NEW.shipment_id = 'TST-DBFAIL-EVID-001' THEN RAISE EXCEPTION 'forced evidence failure for %', NEW.shipment_id; END IF; RETURN NEW; END; \$\$; CREATE TRIGGER trg_fail_db_evidence BEFORE INSERT OR UPDATE ON current_shipment_state FOR EACH ROW EXECUTE FUNCTION fail_db_evidence();"

docker compose exec -T postgres psql -U postgres -d shipments -c "SELECT tgname, pg_get_triggerdef(oid) AS trigger_definition FROM pg_trigger WHERE tgname = 'trg_fail_db_evidence';"

printf '%s\n' '{"event_id":"dbfail-evid-evt-001","shipment_id":"TST-DBFAIL-EVID-001","event_version":1,"domain":"LogisticCenter","event_type":"ParcelReceivedAtHub","occurred_at":"2026-08-25T12:40:00+00:00","location":"Vienna Failure Hub","details":{"test":"database-failure-evidence","failureExpected":true}}' | docker compose exec -T redpanda rpk topic produce logistic-center-events --compression none --partition 0 --key TST-DBFAIL-EVID-001

docker compose exec -T postgres psql -U postgres -d shipments -c "SELECT COUNT(*) AS history_during_failure FROM all_shipment_events WHERE event_id = 'dbfail-evid-evt-001'; SELECT COUNT(*) AS state_during_failure FROM current_shipment_state WHERE shipment_id = 'TST-DBFAIL-EVID-001';"

docker inspect --format 'Container ID: {{.Id}} | Restart count: {{.RestartCount}} | Status: {{.State.Status}} | Exit code: {{.State.ExitCode}} | Started: {{.State.StartedAt}} | Finished: {{.State.FinishedAt}}' "$(docker compose ps -q aggregator)"

docker compose exec -T redpanda rpk group describe shipment-aggregator

docker compose logs --since 10m --no-color aggregator | grep -E 'aggregation_failed|forced evidence failure|aggregator_started' | tail -n 30

## C3. Automatic Recovery

docker compose exec -T postgres psql -U postgres -d shipments -v ON_ERROR_STOP=1 -c "DROP TRIGGER IF EXISTS trg_fail_db_evidence ON current_shipment_state; DROP FUNCTION IF EXISTS fail_db_evidence(); SELECT COUNT(*) AS trigger_after_removal FROM pg_trigger WHERE tgname = 'trg_fail_db_evidence';"

docker compose exec -T postgres psql -U postgres -d shipments -P pager=off -c "SELECT event_id, shipment_id, event_version, domain, event_type, occurred_at, location, details FROM all_shipment_events WHERE event_id = 'dbfail-evid-evt-001'; SELECT COUNT(*) AS historical_row_count FROM all_shipment_events WHERE event_id = 'dbfail-evid-evt-001'; SELECT shipment_id, latest_event_version, latest_event_type, latest_event_domain, latest_location, latest_event_time FROM current_shipment_state WHERE shipment_id = 'TST-DBFAIL-EVID-001';"

docker compose exec -T redpanda rpk group describe shipment-aggregator

docker inspect --format 'Container ID: {{.Id}} | Restart count: {{.RestartCount}} | Status: {{.State.Status}} | Started: {{.State.StartedAt}}' "$(docker compose ps -q aggregator)"

docker compose logs --since 15m --no-color aggregator | grep -E 'dbfail-evid-evt-001|aggregator_started' | tail -n 20

## C4. DB Commit / Offset Commit Crash Window

docker compose up --build -d aggregator

docker compose exec -T postgres psql -U postgres -d shipments -c "SELECT COUNT(*) AS history_before FROM all_shipment_events WHERE event_id = 'postcommit-evid-evt-001'; SELECT COUNT(*) AS state_before FROM current_shipment_state WHERE shipment_id = 'TST-POSTCOMMIT-EVID-001'; SELECT COUNT(*) AS failure_trigger_count FROM pg_trigger WHERE tgname = 'trg_fail_db_evidence';"

docker compose exec -T redpanda rpk group describe shipment-aggregator

docker inspect --format 'Container ID: {{.Id}} | Restart count: {{.RestartCount}} | Status: {{.State.Status}} | Started: {{.State.StartedAt}}' "$(docker compose ps -q aggregator)"
