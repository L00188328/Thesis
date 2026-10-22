"""Offline safety/integrity tests. No Azure, SSH, Kafka or PostgreSQL access."""
import copy
import io
import json
import queue
import threading
import time
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from demo.demo_failover import (
    CONTROL_VM, Demo, TARGET_VM, count_probes, integrity, two_consumers,
    validate_target, zero_lag, shipments_observable, consumer_lag, presentation_lines,
)


def vm(name=TARGET_VM, zone='1', group='rg-thesis-demo-k3s-test'):
    return {'id': f'/subscriptions/test-sub/resourceGroups/{group}/providers/Microsoft.Compute/virtualMachines/{name}',
            'name': name, 'zones': [zone], 'location': 'italynorth',
            'tags': {'configuration': 'k3s-phase-f-demo'}}


def offset_snapshot():
    rows = [{'topic': t, 'partition': p, 'committed_offset': 7, 'end_offset': 7,
             'lag': 0, 'collector_error': ''} for t in ('logistic-center-events', 'delivery-base-events') for p in (0, 1)]
    return {'offsets': rows + [{'topic': '__TOTAL__', 'partition': -1, 'total_lag': 0, 'collector_error': ''}]}


def fixture():
    expected = []
    for n in range(1, 5):
        expected.append({'event': {'event_id': f'e{n}', 'shipment_id': 'A' if n % 2 else 'B',
                                  'event_version': (n + 1) // 2, 'domain': 'test', 'event_type': 'event',
                                  'location': 'hub', 'occurred_at': '2026-10-22T12:00:00+00:00',
                                  'details': {'runId': 'offline'}}})
    ack = [{'event_id': e['event']['event_id']} for e in expected]
    snapshot = {'history': [copy.deepcopy(e['event']) for e in expected],
                'states': [{'shipment_id': s, 'event_version': 2} for s in ('A', 'B')], 'duplicate_rows': []}
    return expected, ack, snapshot


class TargetSafetyTests(unittest.TestCase):
    def test_only_exact_zone1_demo_vm_is_accepted(self):
        self.assertTrue(validate_target(vm(), 'test-sub', 'rg-thesis-demo-k3s-test').endswith('/' + TARGET_VM))
        for changed in (vm(CONTROL_VM, '3'), vm('vm-demo-appzone2', '2'), vm(zone='2'), vm(group='production')):
            with self.subTest(vm=changed), self.assertRaises(RuntimeError):
                validate_target(changed, 'test-sub', 'rg-thesis-demo-k3s-test')

    def test_wrong_subscription_or_owner_is_rejected(self):
        candidate = vm()
        with self.assertRaises(RuntimeError):
            validate_target(candidate, 'different-sub', 'rg-thesis-demo-k3s-test')
        candidate['tags'] = {}
        with self.assertRaises(RuntimeError):
            validate_target(candidate, 'test-sub', 'rg-thesis-demo-k3s-test')

    def test_dry_run_and_check_reject_all_mutations_before_any_command(self):
        for mode in ('dry-run', 'check'):
            demo = Demo.__new__(Demo)
            demo.mode = mode
            demo.survivor_pod = 'aggregator-survivor'
            with patch.object(demo, 'command') as command:
                for action in ('stop', 'start', 'deallocate', 'delete'):
                    with self.subTest(mode=mode, action=action), self.assertRaises(RuntimeError):
                        demo.vm_action(action)
                with self.assertRaises(RuntimeError):
                    demo.kube_args('cordon', 'demo-appzone2', mutation=True)
                with self.assertRaises(RuntimeError):
                    demo.remote_args('produce')
                with self.assertRaises(RuntimeError):
                    demo.az_read('vm', 'stop', '-n', TARGET_VM)
                command.assert_not_called()

    def test_reset_cannot_stop_vm_and_live_cannot_start_or_deallocate(self):
        for mode, action in (('reset', 'stop'), ('auto', 'start'), ('auto', 'deallocate'), ('presentation-mode', 'delete')):
            demo = Demo.__new__(Demo)
            demo.mode = mode
            with self.subTest(mode=mode, action=action), self.assertRaises(RuntimeError):
                demo.vm_action(action)


class EvidenceTests(unittest.TestCase):
    def test_known_nonzero_lag_is_displayed_and_unknown_lag_is_not_zero(self):
        snapshot = offset_snapshot()
        snapshot['offsets'][0].update(end_offset=10, lag=3)
        snapshot['offsets'][-1]['total_lag'] = 3
        self.assertEqual(consumer_lag(snapshot), 3)
        self.assertFalse(zero_lag(snapshot))
        summary = {'outcomes': dict.fromkeys(('event_integrity', 'failover_observed', 'replica_capacity_restored'), 'PASS'),
                   'observed_success_percentage': 90, 'successful_graphql_probes': 9,
                   'total_graphql_probes': 10, 'failed_graphql_probes': 1,
                   'missing_event_count': 0, 'duplicate_event_count': 0, 'final_consumer_lag': consumer_lag(snapshot)}
        self.assertIn('Final consumer lag: 3', presentation_lines(summary))
        snapshot['offsets'][0]['committed_offset'] = None
        summary['final_consumer_lag'] = consumer_lag(snapshot)
        self.assertIsNone(summary['final_consumer_lag'])
        self.assertIn('Final consumer lag: UNKNOWN', presentation_lines(summary))

    def test_missing_or_partial_offsets_are_never_zero_lag(self):
        self.assertTrue(zero_lag(offset_snapshot()))
        for mutate in (
            lambda d: d['offsets'].pop(0),
            lambda d: d['offsets'][0].update(committed_offset=None),
            lambda d: d['offsets'][0].update(committed_offset=8),
            lambda d: d['offsets'][0].update(lag=1, end_offset=8),
            lambda d: d['offsets'][-1].update(total_lag='', collector_error='partial_lag'),
        ):
            d = offset_snapshot()
            mutate(d)
            self.assertFalse(zero_lag(d))

    def test_members_must_cover_four_partitions_without_duplication(self):
        members = [{'member_id': str(p), 'assignments': [{'topic': t, 'partition': p}
                    for t in ('logistic-center-events', 'delivery-base-events')]} for p in (0, 1)]
        self.assertTrue(two_consumers({'assignments': members}))
        members[1]['assignments'][0]['partition'] = 0
        self.assertFalse(two_consumers({'assignments': members}))
        self.assertFalse(two_consumers({'assignments': []}))

    def test_exact_acknowledged_persisted_events_and_versions_pass(self):
        self.assertTrue(integrity(*fixture())['pass'])

    def test_duplicate_event_count_includes_id_and_version_duplicates_without_double_counting(self):
        expected, ack, snapshot = fixture()
        snapshot['history'].append(copy.deepcopy(snapshot['history'][0]))
        snapshot['history'].append({**snapshot['history'][0], 'event_id': 'different-id-same-version'})
        report = integrity(expected, ack, snapshot)
        self.assertEqual(report['duplicate_event_count'], 2)
        self.assertFalse(report['pass'])

    def test_missing_unexpected_duplicate_payload_and_version_fail(self):
        mutations = (
            lambda e, a, s: s['history'].pop(),
            lambda e, a, s: s['history'].append({**s['history'][0], 'event_id': 'unexpected'}),
            lambda e, a, s: s['history'].append(s['history'][0]),
            lambda e, a, s: a.pop(),
            lambda e, a, s: a.append(a[0]),
            lambda e, a, s: s['states'][0].update(event_version=1),
            lambda e, a, s: s['history'][0].update(location='wrong'),
            lambda e, a, s: s['history'][0].update(occurred_at='2026-10-22T12:00:01+00:00'),
        )
        for mutation in mutations:
            e, a, s = fixture()
            mutation(e, a, s)
            with self.subTest(mutation=mutation):
                self.assertFalse(integrity(e, a, s)['pass'])

    def test_failures_are_counted_without_filtering(self):
        result = count_probes([{'success': 'true'}, {'success': 'false'}, {'success': 'false'}],
                              [{'success': True}, {'success': False}])
        self.assertEqual(result['total_graphql_probes'], 5)
        self.assertEqual(result['successful_graphql_probes'], 2)
        self.assertEqual(result['failed_graphql_probes'], 3)
        self.assertEqual(result['observed_success_percentage'], 40)
        self.assertIsNone(count_probes([], [])['observed_success_percentage'])

    def test_only_explicit_startup_checks_are_excluded_from_scored_totals(self):
        rows = [{'success': False, 'phase': 'startup', 'scored': False},
                {'success': False, 'phase': 'post-failure', 'scored': True},
                {'success': False, 'phase': 'post-failure', 'scored': False},
                {'success': False}, {'success': True}]
        counts = count_probes([], rows)
        self.assertEqual(counts['total_graphql_probes'], 4)
        self.assertEqual(counts['failed_graphql_probes'], 3)
        self.assertEqual(len(rows), 5)

    def test_dry_run_main_never_dispatches_live_or_reset(self):
        from demo import demo_failover
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.private').mkdir()
            fake = Demo.__new__(Demo)
            fake.failure_submitted = False
            fake.preflight = lambda: {'pass': True, 'failure_injected': False}
            fake.plan = lambda: None
            saved = {}
            fake.write = lambda name, value: saved.update({name: value})
            with patch.object(demo_failover, 'HERE', root), patch.object(demo_failover, 'Demo', return_value=fake), \
                    patch.object(fake, 'live') as live, patch.object(fake, 'reset') as reset:
                self.assertEqual(demo_failover.main(['appzone1', '--dry-run']), 0)
                live.assert_not_called()
                reset.assert_not_called()
            self.assertEqual(saved['summary.json']['events_produced'], 0)
            self.assertFalse(saved['summary.json']['azure_resources_modified'])


class ProgressGateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.demo = Demo.__new__(Demo)
        self.demo.output = Path(self.directory.name)
        self.demo.events_lock = threading.Lock()
        self.demo.progress_ready = threading.Event()
        self.demo.progress_scoring_started_utc = None
        self.demo.failure_submitted = False
        self.shipments = ['A', 'B']
        self.acks = [{'shipment_id': s} for s in self.shipments]
        self.snapshot = {'states': [{'shipment_id': s, 'event_version': 1} for s in self.shipments]}
        self.graph = {'success': True, 'response': {'data': {k: {'shipmentId': s, 'latestEventVersion': 1}
                                                         for k, s in zip(('a', 'b'), self.shipments)}}}

    def test_gate_requires_both_acknowledged_and_observable_shipments(self):
        self.assertTrue(shipments_observable(self.shipments, self.acks, self.snapshot, self.graph))
        for mutation in ('no_second_ack', 'no_second_sql_state', 'null_graphql_shipment', 'wrong_graphql_shipment'):
            ack, snapshot, graph = copy.deepcopy((self.acks, self.snapshot, self.graph))
            if mutation == 'no_second_ack':
                ack.pop()
            elif mutation == 'no_second_sql_state':
                snapshot['states'].pop()
            elif mutation == 'null_graphql_shipment':
                graph['response']['data']['b'] = None
            else:
                graph['response']['data']['b']['shipmentId'] = 'different-run'
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                self.demo.start_progress_scoring(self.shipments, ack, snapshot, graph)
            self.assertFalse(self.demo.progress_ready.is_set())
        self.demo.start_progress_scoring(self.shipments, self.acks, self.snapshot, self.graph)
        self.assertTrue(self.demo.progress_ready.is_set())

    def test_startup_and_post_failure_errors_are_preserved_with_correct_scoring(self):
        error = {'success': False, 'http_status': 0, 'error': 'timed out'}
        self.demo.record_progress(error, 'readiness')
        self.demo.start_progress_scoring(self.shipments, self.acks, self.snapshot, self.graph)
        self.demo.failure_submitted = True
        self.demo.progress_ready.clear()  # Post-failure errors must still be scored.
        self.demo.record_progress(error, 'probe')
        rows = [json.loads(l) for l in (self.demo.output / 'graphql-progress.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual([r['success'] for r in rows], [False, False])
        self.assertEqual([r['error'] for r in rows], ['timed out', 'timed out'])
        self.assertEqual([r['scored'] for r in rows], [False, True])
        self.assertEqual([r['phase'] for r in rows], ['startup', 'post-failure'])
        self.assertEqual(count_probes([], rows)['failed_graphql_probes'], 1)

    def test_background_progress_waits_for_gate_and_records_post_failure_timeout(self):
        demo = self.demo
        demo.endpoint, demo.canary, demo.availability = 'http://unused.invalid', 'existing-canary', []
        calls = []
        test = self

        class Halt:
            cycles = 0

            def is_set(self):
                return self.cycles >= 6

            def wait(self, seconds):
                self.cycles += 1
                if self.cycles == 3:
                    test.assertEqual(calls, [])
                    demo.start_progress_scoring(test.shipments, test.acks, test.snapshot, test.graph)
                if self.cycles == 5:
                    demo.failure_submitted = True

        def graphql(ids):
            test.assertTrue(demo.progress_ready.is_set())
            test.assertTrue(demo.failure_submitted)
            calls.append(ids)
            return {'success': False, 'http_status': 0, 'error': 'timed out'}

        demo.graphql_states = graphql
        with patch('demo.demo_failover.execute_probe', return_value={'success': 'true'}), \
                patch('demo.demo_failover.subprocess.run', side_effect=AssertionError('Network forbidden')):
            demo.probes(Halt(), self.shipments)
        self.assertEqual(calls, [['A', 'B']])
        rows = [json.loads(l) for l in (demo.output / 'graphql-progress.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]['scored'])
        self.assertFalse(rows[0]['success'])


class OfflineOrchestrationTests(unittest.TestCase):
    """Exercise live control flow against a fully fake process/cluster/database.

    subprocess.run is forbidden throughout; no network or real event send exists.
    Synthetic evidence stays in a temporary directory, never demo/results.
    """
    def exercise(self, mode='auto', failed_probe=False, confirm='\n', startup_pending=False, missing_event=False, failed_progress=False):
        from demo import demo_failover as runner
        real_sleep = time.sleep
        with tempfile.TemporaryDirectory() as directory:
            demo = Demo.__new__(Demo)
            demo.output = Path(directory)
            demo.mode = mode
            demo.c = {'rg': 'rg-thesis-demo-k3s-test'}
            demo.events_lock = threading.Lock()
            demo.failure_submitted = False
            demo.failure_utc = None
            demo.thread_errors = []
            demo.availability = []
            demo.progress_ready = threading.Event()
            demo.progress_scoring_started_utc = None
            demo.target_id = 'fake-target'
            demo.remote_args = lambda kind: ['fake-' + kind]
            clock = [0]
            observations = [0]
            actions = []
            failure_started = threading.Event()
            graphql_calls = [0]

            def condition(value):
                return {'conditions': [{'type': 'Ready', 'status': 'True' if value else 'False'}], 'phase': 'Running'}

            def pod(app, zone, uid):
                return {'kind': 'Pod', 'metadata': {'name': uid, 'uid': uid, 'labels': {'app': app},
                        'creationTimestamp': '2026-10-22T12:00:00Z'},
                        'spec': {'nodeName': 'demo-appzone' + zone}, 'status': condition(True)}

            initial = {'items': [{'kind': 'Node', 'metadata': {'name': n}, 'status': condition(True)}
                                 for n in ('demo-server', 'demo-appzone1', 'demo-appzone2')]
                       + [pod(a, z, a + '-old-' + z) for a in ('aggregator', 'api') for z in ('1', '2')]}
            demo.initial = initial
            events = []
            for n in range(1, 17):
                events.append({'event_id': f'e{n}', 'shipment_id': 'A' if n % 2 else 'B',
                               'event_version': (n + 1) // 2, 'domain': 'test', 'event_type': 'event',
                               'location': 'hub', 'occurred_at': '2026-10-22T12:00:00+00:00', 'details': {}})

            class FakeProcess:
                def __init__(self, *args, **kwargs):
                    self.items = queue.Queue()
                    self.returncode = None
                    self.count = 0
                    self.stdin = self
                    self.stdout = iter(self.lines())

                def lines(self):
                    while True:
                        item = self.items.get(timeout=10)
                        if item is None:
                            return
                        yield json.dumps(item) + '\n'

                def push(self, start, end):
                    for n in range(start, end):
                        topic = ('logistic-center-events' if n % 4 < 2 else 'delivery-base-events')
                        self.items.put({'kind': 'expected', 'sequence': n + 1, 'topic': topic, 'event': events[n]})
                        self.items.put({'kind': 'acknowledged', 'sequence': n + 1, 'event_id': events[n]['event_id'],
                                        'shipment_id': events[n]['shipment_id'], 'topic': topic, 'partition': n % 2, 'offset': n})
                    self.count = end

                def write(self, text):
                    if text == 'STOP\n':
                        self.items.put({'kind': 'producer_finished', 'event_count': self.count})
                        self.items.put(None)
                    else:
                        self.items.put({'kind': 'shipments', 'shipments': ['A', 'B']})
                        self.push(0, 8)

                def flush(self):
                    pass

                def close(self):
                    pass

                def wait(self, timeout):
                    self.returncode = 0
                    return 0

            process = FakeProcess()

            def action(kind):
                self.assertEqual(kind, 'stop')
                actions.append(kind)
                demo.failure_submitted = True
                process.push(8, 16)
                failure_started.set()
                real_sleep(0.01)

            def cluster():
                if not demo.failure_submitted:
                    return copy.deepcopy(initial)
                observations[0] += 1
                value = copy.deepcopy(initial)
                value['items'][1]['status'] = condition(False)
                if observations[0] >= 2:
                    value['items'] = [i for i in value['items'] if i['kind'] == 'Node' or i['spec']['nodeName'] != 'demo-appzone1']
                    value['items'] += [pod(a, '2', a + '-replacement') for a in ('aggregator', 'api')]
                return value

            def snapshot(ids):
                count = 16 if demo.failure_submitted else 8
                result = offset_snapshot()
                result.update(postgresql=True, event_hubs=True, history=copy.deepcopy(events[:count]), duplicate_rows=[],
                              states=[{'shipment_id': s, 'event_version': count // 2, 'event_type': 'event',
                                       'domain': 'test', 'location': 'hub'} for s in ('A', 'B')],
                              assignments=[{'member_id': str(p), 'assignments': [{'topic': t, 'partition': p}
                                           for t in ('logistic-center-events', 'delivery-base-events')]} for p in (0, 1)])
                if missing_event and demo.failure_submitted:
                    result['history'].pop()
                return result

            def graphql(ids):
                graphql_calls[0] += 1
                result = {'success': True, 'response': {'data': {k: {'shipmentId': s,
                        'latestEventVersion': 8 if demo.failure_submitted else 4, 'latestEventType': 'event',
                        'latestEventDomain': 'test', 'latestLocation': 'hub'} for k, s in zip(('a', 'b'), ids)}}}
                if startup_pending and graphql_calls[0] == 1:
                    result['success'] = False
                    result['response']['data']['b'] = None
                return result

            def probes(halt, shipments):
                demo.availability.append({'success': 'true'})
                (demo.output / 'graphql-probes.csv').write_text('success,error_category,http_status\ntrue,,200\n')
                if (failed_probe or failed_progress) and failure_started.wait(10):
                    if failed_probe:
                        demo.availability.append({'success': 'false'})
                        with (demo.output / 'graphql-probes.csv').open('a') as f:
                            f.write('false,timeout,0\n')
                    if failed_progress:
                        demo.record_progress({'success': False, 'http_status': 0, 'error': 'timed out'}, 'probe')
                halt.wait(10)

            def sleep(seconds):
                # Leave room for multiple startup readiness attempts while the
                # producer collector thread is being scheduled. Accelerate only
                # the post-injection observation/drain window.
                clock[0] += 60 if demo.failure_submitted else 1
                real_sleep(0.01)

            demo.vm_action, demo.cluster, demo.snapshot, demo.graphql_states, demo.probes = action, cluster, snapshot, graphql, probes
            demo.az_read = lambda *args: {'powerState': 'VM stopped'}
            with patch.object(runner.subprocess, 'Popen', return_value=process), \
                    patch.object(runner.subprocess, 'run', side_effect=AssertionError('Real command forbidden in offline test')), \
                    patch.object(runner.time, 'monotonic', side_effect=lambda: clock[0]), \
                    patch.object(runner.time, 'sleep', side_effect=sleep), \
                    patch('select.select', return_value=([1], [], [])), \
                    patch.object(runner.sys, 'stdin', io.StringIO(confirm)), \
                    patch.object(runner.sys, 'stdout', io.StringIO()) as console:
                code = demo.live()
                self.console = console.getvalue()
            self.progress_rows = [json.loads(l) for l in (demo.output / 'graphql-progress.jsonl').read_text().splitlines()]
            self.probe_csv = (demo.output / 'graphql-probes.csv').read_text()
            return code, json.loads((demo.output / 'summary.json').read_text()), actions

    def test_auto_flow_records_integrity_redundancy_and_evidence(self):
        code, summary, actions = self.exercise()
        self.assertEqual(code, 0)
        self.assertTrue(summary['execution_completed'])
        self.assertEqual(set(summary['outcomes'].values()), {'PASS'})
        self.assertTrue(summary['strict_pass'])
        self.assertTrue(summary['integrity']['pass'])
        self.assertTrue(summary['processing_observed_before_replacement_readiness'])
        self.assertEqual(summary['post_failure_acknowledgements'], 8)
        self.assertEqual(actions, ['stop'])

    def test_failed_post_injection_request_is_reported_separately_without_blanket_failure(self):
        code, summary, actions = self.exercise(failed_probe=True)
        self.assertEqual(code, 0)
        self.assertEqual(set(summary['outcomes'].values()), {'PASS'})
        self.assertFalse(summary['strict_pass'])
        self.assertFalse(summary['strict_graphql_availability_pass'])
        self.assertTrue(summary['integrity']['pass'])
        self.assertEqual(summary['failed_graphql_probes'], 1)
        self.assertLess(summary['observed_success_percentage'], 100)
        self.assertIn('false,timeout,0', self.probe_csv)
        for label in ('Event integrity: PASS', 'Failover observed: PASS', 'Replica capacity restored: PASS',
                      'GraphQL successful probes:', 'GraphQL failed probes: 1', 'Missing events: 0',
                      'Duplicate events: 0', 'Final consumer lag: 0'):
            self.assertIn(label, self.console)
        self.assertNotIn('FAIL failover:', self.console)

    def test_post_failure_progress_timeout_stays_scored_and_does_not_mask_component_outcomes(self):
        code, summary, actions = self.exercise(failed_progress=True)
        self.assertEqual(code, 0)
        self.assertEqual(set(summary['outcomes'].values()), {'PASS'})
        self.assertEqual(summary['failed_graphql_probes'], 1)
        failed = [r for r in self.progress_rows if not r['success']]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]['phase'], 'post-failure')
        self.assertTrue(failed[0]['scored'])
        self.assertEqual(failed[0]['error'], 'timed out')

    def test_null_shipment_during_startup_is_kept_and_scoring_starts_after_visibility(self):
        code, summary, actions = self.exercise(startup_pending=True)
        self.assertEqual(code, 0)
        self.assertFalse(self.progress_rows[0]['success'])
        self.assertIsNone(self.progress_rows[0]['response']['data']['b'])
        self.assertEqual(self.progress_rows[0]['phase'], 'startup')
        self.assertFalse(self.progress_rows[0]['scored'])
        self.assertEqual(summary['startup_progress_failed_count'], 1)
        self.assertEqual(summary['failed_graphql_probes'], 0)
        self.assertTrue(all(r['scored'] for r in self.progress_rows if r['phase'] == 'post-failure'))

    def test_real_integrity_failure_remains_a_failed_component_and_nonzero_exit(self):
        code, summary, actions = self.exercise(missing_event=True)
        self.assertEqual(code, 1)
        self.assertEqual(summary['outcomes']['event_integrity'], 'FAIL')
        self.assertEqual(summary['outcomes']['failover_observed'], 'PASS')
        self.assertEqual(summary['outcomes']['replica_capacity_restored'], 'PASS')
        self.assertEqual(summary['missing_event_count'], 1)
        self.assertFalse(summary['strict_pass'])

    def test_presentation_eof_never_injects_failure(self):
        code, summary, actions = self.exercise(mode='presentation-mode', confirm='')
        self.assertEqual(code, 1)
        self.assertFalse(summary['failure_injected'])
        self.assertEqual(actions, [])
        self.assertIn('ENTER', summary['error'])


class ResetSafetyTests(unittest.TestCase):
    def exercise(self, already_balanced=False, fail_eviction=False):
        with tempfile.TemporaryDirectory() as directory:
            demo = Demo.__new__(Demo)
            demo.mode = 'reset'
            demo.output = Path(directory)
            demo.c = {'rg': 'rg-thesis-demo-k3s-test', 'subscription': 'test-sub'}
            demo.failure_submitted = False
            candidate = vm()
            candidate['powerState'] = 'VM running' if already_balanced else 'VM stopped'
            demo.az_read = lambda *args: [candidate]
            actions, edits = [], []
            demo.vm_action = lambda action: actions.append(action)
            balanced = {a: already_balanced for a in ('aggregator', 'api')}

            def pods(app):
                return [{'kind': 'Pod', 'metadata': {'name': app + '-' + str(i), 'uid': app + '-uid-' + str(i), 'labels': {'app': app}},
                         'spec': {'nodeName': 'demo-appzone' + ('1' if balanced[app] and i == 0 else '2')},
                         'status': {'conditions': [{'type': 'Ready', 'status': 'True'}]}} for i in range(2)]

            demo.cluster = lambda: {'items': [{'kind': 'Node', 'metadata': {'name': 'demo-appzone' + str(i)},
                                              'status': {'conditions': [{'type': 'Ready', 'status': 'True'}]}}
                                             for i in (1, 2)] + pods('aggregator') + pods('api')}

            def kube(*args, **kwargs):
                if args[0] == 'get':
                    app = args[args.index('-l') + 1].split('=')[1]
                    return json.dumps({'items': pods(app)})
                self.assertTrue(kwargs['mutation'])
                edits.append(args)
                if args[0] == 'create':
                    body = json.loads(kwargs['data'])
                    self.assertEqual(body['kind'], 'Eviction')
                    self.assertIn('uid', body['deleteOptions']['preconditions'])
                    if fail_eviction:
                        raise RuntimeError('simulated eviction rejection')
                    app = body['metadata']['name'].rsplit('-', 1)[0]
                    balanced[app] = True
                return ''

            demo.kube = kube
            demo.preflight = lambda: {'pass': True, 'failure_injected': False}
            if fail_eviction:
                with self.assertRaisesRegex(RuntimeError, 'eviction rejection'):
                    demo.reset()
            else:
                with patch('sys.stdout', io.StringIO()) as stdout:
                    self.assertEqual(demo.reset(), 0)
                    self.assertTrue(stdout.getvalue().rstrip().endswith('DEMO ENVIRONMENT READY'))
            return actions, edits

    def test_balanced_running_environment_requires_no_mutations(self):
        actions, edits = self.exercise(already_balanced=True)
        self.assertEqual(actions, [])
        self.assertEqual(edits, [])

    def test_stopped_worker_is_started_and_one_replica_each_is_evicted(self):
        actions, edits = self.exercise()
        self.assertEqual(actions, ['start'])
        self.assertEqual([e[0] for e in edits], ['cordon', 'create', 'create', 'uncordon'])
        self.assertEqual(edits[0][1], 'demo-appzone2')
        self.assertEqual(edits[-1][1], 'demo-appzone2')

    def test_eviction_failure_still_uncordons_surviving_worker(self):
        actions, edits = self.exercise(fail_eviction=True)
        self.assertEqual(edits[-1], ('uncordon', 'demo-appzone2'))


if __name__ == '__main__':
    unittest.main()
