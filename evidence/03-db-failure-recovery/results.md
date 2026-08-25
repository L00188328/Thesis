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
- Anomalies or discarded attempts: Terminal spacing compressed the offset columns slightly, but all values remained unambiguous. No screenshot was present in the evidence directory at the time this result was recorded.

## C2. Forced Database Transaction Failure

- Date/time:
- Test purpose:
- Controlled shipment ID:
- Controlled event ID:
- Expected result:
- Actual result:
- PASS/FAIL:
- Kafka committed offset:
- Kafka log-end offset:
- Kafka lag:
- Aggregator restart count:
- Historical row count:
- Current-state row count:
- Anomalies or discarded attempts:

## C3. Automatic Recovery

- Date/time:
- Test purpose:
- Controlled shipment ID:
- Controlled event ID:
- Expected result:
- Actual result:
- PASS/FAIL:
- Kafka committed offset:
- Kafka log-end offset:
- Kafka lag:
- Aggregator restart count:
- Historical row count:
- Current-state row count:
- Anomalies or discarded attempts:

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
