"""Executed in an existing survivor Aggregator container; never initializes schema.

snapshot is read-only: SELECTs and Kafka metadata/offset requests, no subscription,
poll, commit, production, schema writes, or Kubernetes/Azure object changes.
produce is called only by the explicitly selected live mode.
Original experiment helpers are supplied in-memory by the local runner.
"""
import argparse
import json
import os
import select
import sys
import time

import psycopg
from kafka import KafkaAdminClient, KafkaConsumer, KafkaProducer
from scripts.experiments.common import kafka_client_config, sanitize_text, utc_now_iso
from scripts.experiments.controlled_workload import event_for_sequence
from scripts.experiments.kafka_consumer_progress import (
    describe_assignments, discover_partitions, sample_offsets,
)
from scripts.experiments.partition_key_manifest import key_partition, select_pair


def config():
    return kafka_client_config(argparse.Namespace(
        bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
        security_protocol='SASL_SSL', sasl_mechanism='PLAIN'))


def snapshot(request):
    result = {'timestamp_utc': utc_now_iso()}
    # Server-enforced read-only transactions, including the connection's first SQL.
    with psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10,
                         options='-c default_transaction_read_only=on -c statement_timeout=15000') as db:
        result['postgresql'] = db.execute('SELECT 1').fetchone()[0] == 1
        ids = request.get('shipments', [])
        run_id = request.get('run_id', '')
        result['states'] = [dict(zip(
            ['shipment_id', 'event_version', 'event_type', 'domain', 'event_time', 'location'], row))
            for row in db.execute(
                'SELECT shipment_id,latest_event_version,latest_event_type,latest_event_domain,'
                'latest_event_time,latest_location FROM current_shipment_state '
                'WHERE shipment_id=ANY(%s)', (ids,)).fetchall()]
        result['history'] = [dict(zip(
            ['event_id', 'shipment_id', 'event_version', 'domain', 'event_type',
             'occurred_at', 'location', 'details'], row))
            for row in db.execute(
                'SELECT event_id,shipment_id,event_version,domain,event_type,occurred_at,location,details '
                "FROM all_shipment_events WHERE shipment_id=ANY(%s) OR details->>'runId'=%s "
                'ORDER BY shipment_id,event_version', (ids, run_id)).fetchall()]
        result['duplicate_rows'] = [list(row) for row in db.execute(
            'SELECT event_id,count(*) FROM all_shipment_events WHERE shipment_id=ANY(%s) '
            "OR details->>'runId'=%s GROUP BY event_id HAVING count(*)>1", (ids, run_id)).fetchall()]
    consumer = KafkaConsumer(**config(), group_id=os.environ['KAFKA_GROUP_ID'],
                             enable_auto_commit=False, request_timeout_ms=15000,
                             api_version_auto_timeout_ms=10000)
    admin = None
    try:
        topics = os.environ['KAFKA_TOPICS'].split(',')
        partitions = discover_partitions(consumer, topics)
        result['partitions'] = [{'topic': p.topic, 'partition': p.partition} for p in partitions]
        result['offsets'] = sample_offsets(consumer, partitions, os.environ['KAFKA_GROUP_ID'], 'kafka_admin')
        admin = KafkaAdminClient(**config(), request_timeout_ms=15000,
                                api_version_auto_timeout_ms=10000)
        result['assignments'] = describe_assignments(admin, os.environ['KAFKA_GROUP_ID'])
        result['event_hubs'] = True
    finally:
        if admin is not None:
            admin.close()
        consumer.close(autocommit=False)
    return result


def emit(kind, **data):
    print(json.dumps({'kind': kind, 'timestamp_utc': utc_now_iso(), **data}, default=str), flush=True)


def produce(request):
    """One acknowledged event/second; finish a four-event cycle on STOP or EOF.

    Write each exact expected payload before attempting the send. Ambiguous sends
    are failures, never silently retried as another application-level event.
    Hard lifetime bounds orphaned producers if the operator terminal disappears.
    """
    run_id = request['run_id']
    a, b = select_pair(run_id, 2)
    emit('shipments', shipments=[a, b])
    topics = os.environ['KAFKA_TOPICS'].split(',')
    producer = KafkaProducer(**config(), acks='all',
                             key_serializer=lambda v: v.encode(),
                             value_serializer=lambda v: json.dumps(v).encode(),
                             max_block_ms=15000, request_timeout_ms=15000)
    started = time.monotonic()
    stopping = False
    sequence = 0
    try:
        while True:
            if select.select([sys.stdin], [], [], 0)[0]:
                command = sys.stdin.readline()
                if not command or command.strip() == 'STOP':
                    stopping = True
            if time.monotonic() - started >= request['max_seconds']:
                emit('error', error='producer maximum lifetime reached')
                stopping = True
            if stopping and sequence % 4 == 0:
                break
            sequence += 1
            topic, event = event_for_sequence(run_id, sequence, a, b, *topics, utc_now_iso())
            emit('expected', sequence=sequence, topic=topic, event=event)
            md = producer.send(topic, key=event['shipment_id'], value=event).get(timeout=30)
            emit('acknowledged', sequence=sequence, event_id=event['event_id'],
                 shipment_id=event['shipment_id'], event_version=event['event_version'],
                 topic=topic, partition=md.partition, offset=md.offset,
                 expected_partition=key_partition(event['shipment_id'], 2))
            if md.partition != key_partition(event['shipment_id'], 2):
                raise RuntimeError('acknowledged partition differs from original key mapping')
            time.sleep(max(0, started + sequence - time.monotonic()))
        producer.flush(timeout=30)
        emit('producer_finished', event_count=sequence)
    finally:
        producer.close(timeout=30)


def main(mode):
    request = json.loads(sys.stdin.readline())
    try:
        if mode == 'snapshot':
            print(json.dumps(snapshot(request), default=str), flush=True)
        elif mode == 'produce':
            produce(request)
        else:
            raise ValueError('Unsupported remote mode')
    except Exception as exc:
        emit('error', error=sanitize_text(exc))
        raise SystemExit(1)
