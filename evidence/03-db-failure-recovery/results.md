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

- Date/time: 2026-08-25 14:43:17.562938 UTC (successful projection observed)
- Test purpose: Demonstrate automatic Docker restart, Kafka redelivery of the uncommitted event, successful projection after removing only the artificial database failure, and offset advancement only after success.
- Controlled shipment ID: `TST-DBFAIL-EVID-001`
- Controlled event ID: `dbfail-evid-evt-001`
- Failure-condition removal: PASS — PostgreSQL reported `DROP TRIGGER`, `DROP FUNCTION`, and trigger count 0. No Aggregator lifecycle command was used.
- Expected result: Docker automatically runs the Aggregator again; Kafka redelivers offset 627; exactly one historical row and the correct current state are written; committed offset advances to 628; lag returns to zero.
- Actual result: PostgreSQL contained exactly one historical row and one current-state row at version 1 with the expected event data. The logistic committed offset advanced from 627 to 628 only after successful projection and matched log end 628, returning lag to zero. The same Aggregator container ID was running with restart count 28. Structured logs showed automatic `aggregator_started` entries followed by `event_projected` for the controlled event at 14:43:17.562938 UTC.
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

- Date/time: 2026-08-25 15:01:30 UTC (baseline container start)
- Test purpose: Demonstrate safe recovery when PostgreSQL commits an event projection but the Aggregator exits before committing the corresponding Kafka consumer offset.
- Controlled shipment ID: `TST-POSTCOMMIT-EVID-001`
- Controlled event ID: `postcommit-evid-evt-001`
- Temporary instrumentation used: A test-only, event-ID-gated one-shot exit in `services/aggregator/main.py` terminates the process with exit code 86 after the PostgreSQL transaction commits and before `consumer.commit()`. The Compose environment enables it only for `postcommit-evid-evt-001`; a marker in `/tmp` prevents a second intentional exit after Docker restarts the same container.
- Precondition: PASS — historical row count 0, current-state row count 0, and prior database failure-trigger count 0.
- Baseline container: `af7a9b346572ffcdd54f6a05b097cfee88725256ce84cf38707d206fe3b67df9`, running with restart count 0.
- Event publication: The controlled event was produced successfully to `logistic-center-events`, partition 0, at offset 628.
- Expected result: The first delivery commits one historical row and the current state, then exits before offset commit. Docker restarts the Aggregator, Kafka redelivers the event, idempotency retains one historical row, the state remains correct, and the offset advances only after replay succeeds.
- Actual result: After the database transaction, structured logs recorded `test_crash_after_db_commit` at 15:56:57.888438 UTC. Docker automatically restarted the same container once, logged `aggregator_started` at 15:56:58.962658 UTC, and Kafka redelivery produced `event_projected` for the same event at 15:57:06.611596 UTC. PostgreSQL subsequently contained exactly one historical row and the correct version-1 materialised state. The logistic committed offset reached 629, matching log end with zero lag.
- PASS/FAIL: PASS, subject to removal and verification of the temporary instrumentation.
- Kafka offsets before crash: Delivery Base committed/log-end 442/442; Logistic Centre committed/log-end 628/628; total lag 0.
- Kafka offsets after crash: Not directly sampled during the approximately one-second automatic restart window. The event was published at offset 628 while the baseline committed offset was 628; the gated hook exited before `consumer.commit()`, and the subsequent `event_projected` entry for the same event after restart demonstrates redelivery.
- Kafka offsets after recovery: Delivery Base committed/log-end 442/442; Logistic Centre committed/log-end 629/629; total lag 0.
- Historical row count after DB commit: Not separately sampled before automatic replay because Docker restarted immediately.
- Historical row count after replay: 1, with 1 distinct event ID.
- Current-state row count: 1 at event version 1 with the expected domain, type, location, and event time.
- Instrumentation removal verified:
- Aggregator restart count: Increased automatically from 0 to 1; container ID remained `af7a9b346572ffcdd54f6a05b097cfee88725256ce84cf38707d206fe3b67df9`.
- Evidence files: `Screenshots/C-04A-post-commit-test-database-preconditions.jpg`, `Screenshots/C-04B-post-commit-test-offset-and-container-baseline.jpg`, `Screenshots/C-04C-publish-controlled-event.jpg`, `Screenshots/C-04D-post-commit-crash-and-automatic-restart.jpg`, and `Screenshots/C-04E-post-commit-replay-database-and-offset-recovery.jpg`.
- Anomalies or discarded attempts: The unrelated local mail notification has no bearing on the test.
