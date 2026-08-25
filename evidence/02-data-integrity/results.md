# Data Integrity Results

Complete each section only after observing the result.

## B1. Duplicate Event

- Date/time: 2026-08-25 12:00:03–12:00:11 UTC
- Test purpose: Demonstrate idempotent handling when Kafka delivers the exact same event more than once.
- Controlled shipment ID: `TST-DUP-EVID-001`
- Controlled event IDs: `dup-evid-evt-001`, published twice unchanged.
- Expected result: Both Kafka deliveries are processed, but `event_id` idempotency retains one historical row and the materialised state remains correct.
- Actual result: The identical event was produced to logistic topic partition 0 at offsets 621 and 622. Structured logs contained two `event_projected` entries. PostgreSQL retained one historical row and one current-state row at version 1 with the expected event type, domain, time, and location. The consumer group returned to zero lag.
- PASS/FAIL: PASS
- Relevant Kafka offsets: Produced at 621 and 622; final logistic committed/log-end offset `623/623`, lag 0. Delivery Base remained `442/442`, lag 0.
- Relevant database row counts: Historical row count 1; current-state row count 1.
- Anomalies or discarded attempts: Kafka member columns were visually concatenated by terminal rendering, but topic offsets and lag remained readable.

## B2. Out-of-Order Event

- Date/time: 2026-08-25 12:07:48–12:08:03 UTC
- Test purpose: Demonstrate that an older event delivered after a newer event is preserved in history without regressing the materialised shipment state.
- Controlled shipment ID: `TST-OOO-EVID-001`
- Controlled event IDs: `ooo-evid-evt-v5` (version 5) and `ooo-evid-evt-v3` (version 3).
- Expected result: Both unique events remain in history, while `current_shipment_state` retains version 5 after version 3 is processed later.
- Actual result: Version 5 was produced first at offset 623 and version 3 second at offset 624. Structured logs showed both events were processed. PostgreSQL contained both unique historical events, while current state remained version 5 (`ParcelLoadedForTransit`) at the newer timestamp. Kafka returned to zero lag.
- PASS/FAIL: PASS
- Relevant Kafka offsets: Produced at 623 and 624; final logistic committed/log-end offset `625/625`, lag 0. Delivery Base remained `442/442`, lag 0.
- Relevant database row counts: Two historical rows, two distinct event IDs, and one current-state row at version 5.
- Anomalies or discarded attempts: None observed.

## B3. Replay

- Date/time:
- Test purpose:
- Controlled shipment ID:
- Controlled event IDs:
- Expected result:
- Actual result:
- PASS/FAIL:
- Relevant Kafka offsets:
- Relevant database row counts:
- Anomalies or discarded attempts:
