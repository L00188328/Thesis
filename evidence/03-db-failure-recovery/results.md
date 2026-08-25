# Database Failure and Recovery Results

Complete each section only after observing the result.

## C1. Stable Starting State

- Date/time: 2026-08-25 (terminal capture time not recorded)
- Test purpose: Establish a stable zero-lag baseline and record the Aggregator container identity and restart count before injecting a PostgreSQL failure.
- Controlled test IDs: Not applicable
- Expected result: Aggregator is running with restart count 0; the consumer group is stable with one member; committed offsets equal log-end offsets and total lag is zero.
- Actual result: Aggregator container `d3a0e832602c74f90ba697d1b3f48c43ddd5c50b923eacf9e9653c4cda27d2ac` was running with restart count 0. The consumer group was stable with one member and total lag 0.
- PASS/FAIL: PASS
- Kafka committed offset: Delivery Base 442; Logistic Centre 627.
- Kafka log-end offset: Delivery Base 442; Logistic Centre 627.
- Kafka lag: Delivery Base 0; Logistic Centre 0; total lag 0.
- Aggregator restart count: 0.
- Evidence files: `Screenshots/C-01A-stable-baseline-offsets-and-restart-count.jpg`.
- Anomalies or discarded attempts: Terminal spacing compressed the offset columns slightly, but all values remained unambiguous.

## C2. Forced Database Transaction Failure

- Date/time: 2026-08-25 14:22:17–14:24:56 UTC
- Test purpose: Demonstrate atomic PostgreSQL rollback, non-commit of the failed Kafka offset, process termination, and Docker-managed automatic restart after a projection transaction failure.
- Controlled shipment ID: `TST-DBFAIL-EVID-001`
- Controlled event ID: `dbfail-evid-evt-001`
- Precondition: PASS — historical row count 0, current-state row count 0, and trigger count 0 before instrumentation.
- Temporary instrumentation: `fail_db_evidence()` and `trg_fail_db_evidence` were created successfully. PostgreSQL confirmed a `BEFORE INSERT OR UPDATE` trigger on `public.current_shipment_state` executing `fail_db_evidence()`.
- Event publication: The controlled event was produced successfully to `logistic-center-events`, partition 0, at offset 627.
- Expected result: The trigger aborts the transaction; neither table receives a partial row; committed offset remains unchanged; lag becomes 1; the Aggregator exits and Docker automatically restarts it.
- Actual result: Both test-row counts remained zero. The logistic committed offset stayed at 627 while log end advanced to 628, producing lag 1. Structured logs repeatedly showed `aggregation_failed`, the forced PostgreSQL exception, process termination, and a subsequent `aggregator_started`. The same container ID remained in use and Docker increased its restart count from 0 to 10 without manual intervention.
- PASS/FAIL: PASS
- Kafka committed offset: Delivery Base 442; Logistic Centre 627.
- Kafka log-end offset: Delivery Base 442; Logistic Centre 628.
- Kafka lag: Delivery Base 0; Logistic Centre 1; total lag 1.
- Aggregator restart count: 10 at evidence capture, increased automatically from baseline 0.
- Historical row count: 0.
- Current-state row count: 0.
- Evidence files: `Screenshots/C-02A-db-failure-test-precondition.jpg`, `Screenshots/C-02B-temporary-db-failure-trigger.jpg`, `Screenshots/C-02C-failing-event-published.jpg`, `Screenshots/C-02D-docker-automatic-restart.jpg`, `Screenshots/C-02E-db-rollback-and-restart-count.jpg`, and `Screenshots/C-02F-uncommitted-offset-and-failure-logs.jpg`.
- Anomalies or discarded attempts: Docker inspection captured the replacement process while it was running, so its current exit code was 0; the prior `FinishedAt` timestamp, increased restart count, repeated traceback logs, and subsequent start timestamps prove the failed processes exited and were automatically restarted. The unrelated local mail notification has no bearing on the test.

## C3. Automatic Recovery

- Date/time: 2026-08-25 14:43:17 UTC (successful projection observed)
- Test purpose: Demonstrate automatic Docker restart, Kafka redelivery of the uncommitted event, successful projection after removing only the artificial database failure, and offset advancement only after success.
- Controlled shipment ID: `TST-DBFAIL-EVID-001`
- Controlled event ID: `dbfail-evid-evt-001`
- Failure-condition removal: PASS — PostgreSQL reported `DROP TRIGGER`, `DROP FUNCTION`, and trigger count 0. No Aggregator lifecycle command was used.
- Expected result: Docker automatically runs the Aggregator again; Kafka redelivers offset 627; exactly one historical row and the correct current state are written; committed offset advances to 628; lag returns to zero.
- Actual result: PostgreSQL contained exactly one historical row and one current-state row at version 1 with the expected event data. The logistic committed offset advanced from 627 to 628 only after successful projection and matched log end 628, returning lag to zero. The same Aggregator container ID was running with restart count 28. Structured logs showed automatic `aggregator_started` entries followed by `event_projected` for the controlled event.
- PASS/FAIL: PASS
- Kafka committed offset: Delivery Base 442; Logistic Centre 628.
- Kafka log-end offset: Delivery Base 442; Logistic Centre 628.
- Kafka lag: Delivery Base 0; Logistic Centre 0; total lag 0.
- Aggregator restart count: 28 at successful recovery capture; container ID remained `d3a0e832602c74f90ba697d1b3f48c43ddd5c50b923eacf9e9653c4cda27d2ac`.
- Historical row count: 1.
- Current-state row count: 1 at event version 1.
- Evidence files: `Screenshots/C-03A-temporary-failure-trigger-removed.jpg`, `Screenshots/C-03B-recovery-database-state.jpg`, `Screenshots/C-03C-recovery-kafka-zero-lag-and-container.jpg`, and `Screenshots/C-03D-automatic-event-redelivery-log.jpg`.
- Anomalies or discarded attempts: The trigger remained active long enough for Docker's restart count to rise from 10 at failure capture to 28 before removal and recovery. This does not affect correctness; no manual Aggregator lifecycle command was used.

## C4. DB Commit / Offset Commit Crash Window

- Date/time:
- Test purpose:
- Controlled shipment ID:
- Controlled event ID:
- Temporary instrumentation used:
- Expected result:
- Actual result:
- PASS/FAIL:
- Kafka offsets before crash:
- Kafka offsets after crash:
- Kafka offsets after recovery:
- Historical row count after DB commit:
- Historical row count after replay:
- Current-state row count:
- Instrumentation removal verified:
- Anomalies or discarded attempts:
