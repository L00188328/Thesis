#!/usr/bin/env python3
"""Phase F K3s demo runner. Only --dry-run/check are authorized for first use.

Dry-run and check have no path to an Azure or Kubernetes mutation. Live modes
must be selected explicitly. The sole failure target is the tagged demo Zone-1
application VM, rebound and validated immediately before the stop command.
"""
import argparse
import base64
import collections
import concurrent.futures
import csv
import fcntl
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from scripts.experiments.availability_probe import build_payload, execute_probe
from scripts.experiments.common import sanitize_text, utc_now_iso
from demo.azure_cli import run_cli

NAMESPACE = 'thesis-ha'
TARGET_VM = 'vm-demo-appzone1'
CONTROL_VM = 'vm-demo-k3s-server'
NODES = {'demo-server': ('3', CONTROL_VM, '10.60.1.10'),
         'demo-appzone1': ('1', TARGET_VM, '10.60.1.11'),
         'demo-appzone2': ('2', 'vm-demo-appzone2', '10.60.1.12')}
HISTORICAL = {'api': 'sha256:2bfab63b2894046a842b36fd792a7530a6a28731775a886b081a6fdc3e556b5f',
              'aggregator': 'sha256:a41041c885ba594685d1533e6b436ce536015c1effd06a41651ec401a5ca34ff'}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def ready(obj):
    return any(c.get('type') == 'Ready' and c.get('status') == 'True'
               for c in obj.get('status', {}).get('conditions', []))


def app_pods(items, app):
    return [p for p in items if p['metadata'].get('labels', {}).get('app') == app
            and not p['metadata'].get('deletionTimestamp')]


def validate_vm(vm, subscription, group, name, zone):
    expected = f'/subscriptions/{subscription}/resourceGroups/{group}/providers/Microsoft.Compute/virtualMachines/{name}'
    require(vm.get('id', '').lower() == expected.lower(), 'VM resource ID does not match exact demo identity')
    require(vm.get('name') == name and vm.get('zones') == [zone], 'VM name/zone mismatch: ' + name)
    require(vm.get('location', '').lower() == 'italynorth', 'VM is outside Italy North')
    require(vm.get('tags', {}).get('configuration') == 'k3s-phase-f-demo', 'VM lacks demo ownership tag')
    return expected


def validate_target(vm, subscription, group):
    require(group.startswith('rg-thesis-demo-k3s-'), 'Failure target group is not a dedicated demo group')
    target = validate_vm(vm, subscription, group, TARGET_VM, '1')
    require(CONTROL_VM.lower() not in target.lower(), 'Control plane can never be a failure target')
    return target


def consumer_lag(snapshot):
    rows = snapshot.get('offsets', [])
    detail = [r for r in rows if r.get('topic') != '__TOTAL__']
    total = [r for r in rows if r.get('topic') == '__TOTAL__']
    wanted = {(t, p) for t in ('logistic-center-events', 'delivery-base-events') for p in (0, 1)}
    if not (len(detail) == 4 and len(total) == 1
            and {(r['topic'], r['partition']) for r in detail} == wanted
            and not total[0].get('collector_error')
            and all(not r.get('collector_error')
                    and isinstance(r.get('committed_offset'), int) and isinstance(r.get('end_offset'), int)
                    and r['end_offset'] >= r['committed_offset'] >= 0
                    and r.get('lag') == r['end_offset'] - r['committed_offset'] for r in detail)):
        return None
    measured = sum(r['lag'] for r in detail)
    return measured if total[0].get('total_lag') == measured else None


def zero_lag(snapshot):
    return consumer_lag(snapshot) == 0


def two_consumers(snapshot):
    members = snapshot.get('assignments', [])
    assignments = [a for m in members for a in m.get('assignments', [])]
    return (len(members) == 2 and all(len(m.get('assignments', [])) == 2 for m in members)
            and len({m.get('member_id') for m in members}) == 2
            and len(assignments) == 4 and {(a['topic'], a['partition']) for a in assignments} ==
            {(t, p) for t in ('logistic-center-events', 'delivery-base-events') for p in (0, 1)})


def scored_progress(row):
    # Only explicitly recorded startup checks are outside the measurement window.
    # Historical rows have no phase/scored fields and retain their original score.
    return not (row.get('phase') == 'startup' and row.get('scored') is False)


def count_probes(probes, progress):
    progress = [r for r in progress if scored_progress(r)]
    successful = sum(r['success'] == 'true' for r in probes) + sum(r['success'] is True for r in progress)
    total = len(probes) + len(progress)
    return {'total_graphql_probes': total, 'successful_graphql_probes': successful,
            'failed_graphql_probes': total - successful,
            'observed_success_percentage': round(100 * successful / total, 3) if total else None}


def shipments_observable(shipments, acknowledged, snapshot, graphql):
    """Require actual sends and both exact run shipments visible in SQL/GraphQL."""
    if len(shipments) != 2 or len(set(shipments)) != 2:
        return False
    if not set(shipments).issubset({r.get('shipment_id') for r in acknowledged}):
        return False
    states = {s['shipment_id']: s['event_version'] for s in snapshot.get('states', [])}
    if not all(isinstance(states.get(s), int) and states[s] > 0 for s in shipments):
        return False
    data = graphql.get('response', {}).get('data') or {}
    return bool(graphql.get('success') and all(
        data.get(alias) and data[alias].get('shipmentId') == shipment
        and isinstance(data[alias].get('latestEventVersion'), int)
        and data[alias]['latestEventVersion'] > 0
        for alias, shipment in zip(('a', 'b'), shipments)))


def presentation_lines(summary):
    outcomes = summary['outcomes']
    percentage = summary['observed_success_percentage']
    lag = summary['final_consumer_lag']
    return [
        'Event integrity: ' + outcomes['event_integrity'],
        'Failover observed: ' + outcomes['failover_observed'],
        'Replica capacity restored: ' + outcomes['replica_capacity_restored'],
        f'GraphQL successful probes: {summary["successful_graphql_probes"]}/{summary["total_graphql_probes"]} '
        + (f'({percentage}%)' if percentage is not None else '(not measured)'),
        f'GraphQL failed probes: {summary["failed_graphql_probes"]}',
        f'Missing events: {summary["missing_event_count"]}',
        f'Duplicate events: {summary["duplicate_event_count"]}',
        'Final consumer lag: ' + (str(lag) if lag is not None else 'UNKNOWN'),
    ]


def integrity(expected, acknowledged, snapshot):
    events = [r['event'] for r in expected]
    expected_ids = [e['event_id'] for e in events]
    ack_ids = [r['event_id'] for r in acknowledged]
    history = snapshot.get('history', [])
    actual_ids = [r['event_id'] for r in history]
    expected_set, actual_set = set(expected_ids), set(actual_ids)
    versions = {}
    for event in events:
        versions[event['shipment_id']] = max(versions.get(event['shipment_id'], 0), event['event_version'])
    states = {r['shipment_id']: r['event_version'] for r in snapshot.get('states', [])}
    actual_by_id = {r['event_id']: r for r in history}
    mismatches = []
    for event in events:
        actual = actual_by_id.get(event['event_id'])
        if actual:
            fields = ('shipment_id', 'event_version', 'domain', 'event_type', 'location', 'details')
            # PostgreSQL renders timezone offsets differently; compare instants.
            same_time = datetime.fromisoformat(str(actual['occurred_at'])) == datetime.fromisoformat(event['occurred_at'])
            if not same_time or any(actual[k] != event[k] for k in fields):
                mismatches.append(event['event_id'])
    duplicates = {key: n for key, n in collections.Counter(actual_ids).items() if n > 1}
    version_duplicates = [{'shipment_id': key[0], 'event_version': key[1], 'rows': n}
                          for key, n in collections.Counter((r['shipment_id'], r['event_version']) for r in history).items() if n > 1]
    seen_ids, seen_versions = set(), set()
    duplicate_event_count = 0
    for row in history:
        version = (row['shipment_id'], row['event_version'])
        duplicate_event_count += row['event_id'] in seen_ids or version in seen_versions
        seen_ids.add(row['event_id'])
        seen_versions.add(version)
    report = {'expected_event_ids': expected_ids, 'acknowledged_event_ids': ack_ids,
              'persisted_unique_event_ids': sorted(actual_set),
              'missing_events': sorted(expected_set - actual_set),
              'unexpected_events': sorted(actual_set - expected_set),
              'unacknowledged_events': sorted(expected_set - set(ack_ids)),
              'unexpected_acknowledgements': sorted(set(ack_ids) - expected_set),
              'duplicate_expected_ids': len(expected_ids) - len(expected_set),
              'duplicate_acknowledgements': len(ack_ids) - len(set(ack_ids)),
              'duplicate_rows': duplicates or snapshot.get('duplicate_rows', []),
              'duplicate_shipment_versions': version_duplicates,
              'duplicate_event_count': duplicate_event_count,
              'payload_mismatches': mismatches,
              'expected_event_versions': versions, 'actual_event_versions': states}
    report['pass'] = (bool(events) and len(events) % 4 == 0
                      and not any(report[k] for k in (
                          'missing_events', 'unexpected_events', 'unacknowledged_events',
                          'unexpected_acknowledgements', 'duplicate_expected_ids',
                          'duplicate_acknowledgements', 'duplicate_rows', 'duplicate_shipment_versions', 'payload_mismatches'))
                      and versions == states)
    return report


class Demo:
    def __init__(self, mode, output):
        state = Path(os.environ.get('DEMO_STATE_FILE', str(HERE / '.private/state.json')))
        require(state.is_file(), 'Missing ignored demo state file: ' + str(state))
        self.c = json.loads(state.read_text())
        self.mode, self.output = mode, output
        self.private = HERE / '.private'
        self.endpoint = 'http://' + self.c['ips']['server'] + ':30080/graphql/'
        self.bundle = self.remote_bundle()
        self.events_lock = threading.Lock()
        self.target_id = None
        self.canary = None
        self.survivor_pod = None
        self.stop_requested = False
        self.failure_submitted = False
        self.availability = []
        self.thread_errors = []
        self.failure_utc = None
        self.progress_ready = threading.Event()
        self.progress_scoring_started_utc = None

    def write(self, name, obj):
        (self.output / name).write_text(json.dumps(obj, indent=2, default=str) + '\n')

    def event(self, label, **data):
        with self.events_lock:
            with (self.output / 'timeline.jsonl').open('a') as f:
                f.write(json.dumps({'timestamp_utc': utc_now_iso(), 'label': label, **data}, default=str) + '\n')

    def command(self, args, data=None, timeout=90):
        p = subprocess.run(args, input=data, capture_output=True, text=True, timeout=timeout)
        require(p.returncode == 0, 'Command failed: ' + sanitize_text(p.stderr[-4000:]))
        return p.stdout

    def az_read(self, *args):
        allowed = {('vm', 'list'), ('vm', 'show'), ('group', 'show'), ('network', 'nic', 'list')}
        require(any(tuple(args[:len(prefix)]) == prefix for prefix in allowed), 'Non-read-only Azure request rejected')
        return json.loads(run_cli(self.c, *args, '--subscription', self.c['subscription'],
                                  '--only-show-errors', '-o', 'json', executor=self.command, timeout=90))

    def vm_action(self, action):
        require(self.mode in ('auto', 'presentation-mode', 'reset'), 'VM action forbidden in read-only mode')
        require((self.mode == 'reset' and action == 'start') or
                (self.mode in ('auto', 'presentation-mode') and action == 'stop'), 'VM action not allowed')
        if action == 'stop':
            require(self.progress_ready.is_set(), 'Progress scoring must be armed before failure injection')
        fresh = self.az_read('vm', 'show', '-g', self.c['rg'], '-n', TARGET_VM, '--show-details')
        target = validate_target(fresh, self.c['subscription'], self.c['rg'])
        require(target.lower() == self.target_id.lower(), 'Failure target changed since preflight')
        print(f'AZURE ACTION: {action} only {TARGET_VM} (Zone 1)', flush=True)
        self.event('azure_action_submitted', action=action, vm=TARGET_VM, resource_id=target)
        if action == 'stop':
            self.failure_submitted = True
            self.failure_utc = utc_now_iso()
        # stop (not deallocate) preserves allocation and the static networking.
        return run_cli(self.c, 'vm', action, '--ids', target, '--subscription', self.c['subscription'],
                       '--no-wait', '--only-show-errors', '-o', 'json', executor=self.command, timeout=90)

    def ssh_args(self, command):
        return ['ssh', '-i', str(self.private / 'id_ed25519'), '-o', 'IdentitiesOnly=yes',
                '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(self.private / 'known_hosts'),
                '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=2',
                'demoops@' + self.c['ips']['server'], command]

    def kube_args(self, *args, mutation=False):
        if mutation:
            require(self.mode == 'reset', 'Kubernetes mutations are restricted to explicit reset')
        else:
            require(args and args[0] in ('get', 'exec', 'logs'), 'Non-read-only Kubernetes request rejected')
        return self.ssh_args(shlex.join(['sudo', 'k3s', 'kubectl', *args]))

    def kube(self, *args, data=None, mutation=False):
        return self.command(self.kube_args(*args, mutation=mutation), data=data)

    def cluster(self):
        # A single API List retains raw node conditions, Pod UIDs, deletion times,
        # readiness, tolerations and event timestamps for subsequent interpretation.
        return json.loads(self.kube('get', 'nodes,pods,events,deployments', '-n', NAMESPACE, '-o', 'json'))

    @staticmethod
    def remote_bundle():
        modules = {}
        for name in ('common', 'partition_key_manifest', 'controlled_workload', 'kafka_consumer_progress'):
            modules['scripts.experiments.' + name] = (HERE.parent / 'scripts/experiments' / (name + '.py')).read_text()
        payload = base64.b64encode(json.dumps({'modules': modules, 'source': (HERE / 'remote_evidence.py').read_text()}).encode()).decode()
        return ("import base64,json,sys,types; b=json.loads(base64.b64decode(" + repr(payload) + ")); "
                "[(sys.modules.setdefault(n,types.ModuleType(n))) for n in ['scripts','scripts.experiments']]; "
                "[(setattr(sys.modules[n],'__path__',[])) for n in ['scripts','scripts.experiments']]; "
                "[(sys.modules.setdefault(n,types.ModuleType(n)),exec(compile(s,n,'exec'),sys.modules[n].__dict__)) "
                "for n,s in b['modules'].items()]; exec(compile(b['source'],'demo/remote_evidence.py','exec')); main(sys.argv[1])")

    def remote_args(self, mode):
        require(self.survivor_pod, 'Surviving Aggregator is not identified')
        require(mode == 'snapshot' or (mode == 'produce' and self.mode in ('auto', 'presentation-mode')),
                'Event production forbidden in read-only mode')
        return self.kube_args('exec', '-i', '-n', NAMESPACE, self.survivor_pod,
                              '--', 'python', '-u', '-c', self.bundle, mode)

    def snapshot(self, shipments):
        request = {'shipments': shipments}
        if self.mode in ('auto', 'presentation-mode'):
            request['run_id'] = self.output.name
        raw = self.command(self.remote_args('snapshot'), json.dumps(request) + '\n', timeout=100)
        result = json.loads(raw)
        require(result.get('postgresql') and result.get('event_hubs'), 'External dependency read failed: ' + sanitize_text(raw[-1000:]))
        return result

    def preflight(self):
        print('READ-ONLY PREFLIGHT', flush=True)
        # Independent Azure/Kubernetes inventory reads; all failures propagate.
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            vm_future = pool.submit(self.az_read, 'vm', 'list', '-g', self.c['rg'], '--show-details')
            nic_future = pool.submit(self.az_read, 'network', 'nic', 'list', '-g', self.c['rg'])
            cluster = self.cluster()
            vms, nics = vm_future.result(), nic_future.result()
        self.write('azure-vms.json', [{k: v.get(k) for k in ('id', 'name', 'zones', 'location', 'tags', 'powerState', 'hardwareProfile', 'networkProfile')} for v in vms])
        self.write('cluster-before.json', cluster)
        by_vm = {v['name']: v for v in vms}
        nodes = {i['metadata']['name']: i for i in cluster['items'] if i['kind'] == 'Node'}
        for name, (zone, vm_name, ip) in NODES.items():
            require(vm_name in by_vm and name in nodes, 'Missing expected demo VM/node: ' + name)
            vm, node = by_vm[vm_name], nodes[name]
            validate_vm(vm, self.c['subscription'], self.c['rg'], vm_name, zone)
            require(vm.get('powerState') == 'VM running', 'VM is not running: ' + vm_name)
            expected_sku = 'Standard_B2s' if zone == '3' else 'Standard_D2as_v4'
            require(vm['hardwareProfile']['vmSize'] == expected_sku, 'Unexpected VM SKU')
            nic_ids = {n['id'].lower() for n in vm['networkProfile']['networkInterfaces']}
            addresses = [c['privateIPAddress'] for n in nics if n['id'].lower() in nic_ids for c in n['ipConfigurations']]
            require(ip in addresses, 'Azure VM/private address binding mismatch: ' + name)
            require(ready(node), name + ' is not Ready')
            require(node['metadata']['labels'].get('topology.kubernetes.io/zone') == 'italynorth-' + zone,
                    'Kubernetes zone label does not match Azure VM zone: ' + name)
            require(any(a['address'] == ip and a['type'] == 'InternalIP' for a in node['status']['addresses']), 'Node IP mismatch')
            require(not node.get('spec', {}).get('unschedulable'), 'Node is cordoned: ' + name)
            require(node['metadata']['labels'].get('workload') == ('system' if zone == '3' else 'thesis-app'), 'Node workload label mismatch')
            if zone != '3':
                require(any(t.get('key') == 'workload' and t.get('value') == 'thesis-app' and t.get('effect') == 'NoSchedule'
                            for t in node.get('spec', {}).get('taints', [])), 'Missing application-worker taint')
            print(f'PASS {name}: Ready, Azure Zone {zone}, {expected_sku}', flush=True)
        pods = [i for i in cluster['items'] if i['kind'] == 'Pod']
        deployments = {i['metadata']['name']: i for i in cluster['items'] if i['kind'] == 'Deployment'}
        for app in ('aggregator', 'api'):
            group = app_pods(pods, app)
            require(len(group) == 2 and all(ready(p) for p in group), app + ': expected exactly two Ready replicas')
            require({p['spec']['nodeName'] for p in group} == {'demo-appzone1', 'demo-appzone2'}, app + ': initial distribution is incorrect')
            require(deployments[app]['spec']['replicas'] == 2 and deployments[app]['status'].get('updatedReplicas') == 2,
                    app + ': deployment is not stable at two updated replicas')
            for pod in group:
                spec = pod['spec']
                for key in ('node.kubernetes.io/not-ready', 'node.kubernetes.io/unreachable'):
                    require(any(t.get('key') == key and t.get('effect') == 'NoExecute' and t.get('operator') == 'Exists'
                                and t.get('tolerationSeconds') == 30 for t in spec.get('tolerations', [])), 'Missing demo-only 30-second tolerance')
                require(spec['containers'][0]['image'].endswith('@' + HISTORICAL[app]), 'Application historical image digest mismatch')
                affinity = spec.get('affinity', {})
                require(not spec.get('nodeSelector'), 'Unexpected node selector')
                # Both workers must remain eligible after one fails. Be explicit
                # about the original required node affinity rather than inferring
                # eligibility from the currently successful spread alone.
                require(affinity.get('nodeAffinity', {}).get('requiredDuringSchedulingIgnoredDuringExecution') ==
                        {'nodeSelectorTerms': [{'matchExpressions': [{'key': 'workload', 'operator': 'In', 'values': ['thesis-app']}]}]},
                        'Required node affinity differs from the original application-worker rule')
                require(not affinity.get('podAntiAffinity', {}).get('requiredDuringSchedulingIgnoredDuringExecution'), 'Hard anti-affinity would prevent co-location')
                require(all(x['whenUnsatisfiable'] == 'ScheduleAnyway' for x in spec.get('topologySpreadConstraints', [])), 'Hard topology spreading would prevent co-location')
            print('PASS ' + app + ': one Ready replica per worker; historical digest; demo tolerations 30s; co-location allowed', flush=True)
        self.survivor_pod = next(p['metadata']['name'] for p in app_pods(pods, 'aggregator') if p['spec']['nodeName'] == 'demo-appzone2')
        baseline = json.loads((HERE / 'results/baseline.json').read_text())
        self.canary = baseline['seed_shipments'][0]
        deps = self.snapshot(baseline['seed_shipments'])
        self.write('dependencies-before.json', deps)
        require(deps['postgresql'], 'PostgreSQL is unreachable')
        require(two_consumers(deps), 'Expected two distinct consumer members with two partitions each, covering all four partitions')
        require(zero_lag(deps), 'Baseline consumer lag is nonzero or cannot be reliably measured')
        canary_state = next((s for s in deps['states'] if s['shipment_id'] == self.canary), None)
        require(canary_state and canary_state['event_version'] == 2, 'Existing immutable GraphQL canary is absent/changed')
        probe = execute_probe(self.endpoint, build_payload(self.canary), self.canary, 2, 5)
        self.write('graphql-preflight.json', probe)
        require(probe['success'] == 'true', 'External GraphQL preflight failed: ' + str(probe))
        print('PASS GraphQL: externally reachable; existing shipment version 2', flush=True)
        print('PASS PostgreSQL: reachable; read-only SELECT; existing projection schema', flush=True)
        print('PASS Event Hubs: reachable; 2 consumer members; all 4 partitions assigned; measured lag 0', flush=True)
        self.target_id = validate_target(by_vm[TARGET_VM], self.c['subscription'], self.c['rg'])
        print('PASS failure target: appzone1 -> vm-demo-appzone1, Azure Zone 1', flush=True)
        print('PASS control plane: vm-demo-k3s-server is excluded from every VM action', flush=True)
        self.initial = cluster
        return {'pass': True, 'failure_target': TARGET_VM, 'failure_target_resource_id': self.target_id,
                'control_plane_excluded': True, 'nodes': list(NODES), 'consumer_members': 2,
                'baseline_lag': 0, 'graphql': probe, 'failure_injected': False}

    def plan(self):
        plan = [
            'Generate unique run shipment IDs mapped to both partitions using the original thesis generator.',
            'Start acknowledged event production in the existing Zone-2 Aggregator container (1 event/second).',
            'Start external GraphQL availability probes immediately; keep startup readiness requests as raw evidence.',
            'Require 8 acknowledgements, both topics/partitions and both exact new shipments observable in SQL/GraphQL; then start scored progress probes before arming.',
            'Presentation: display >>> READY TO INJECT FAILURE: ZONE 1 APPLICATION WORKER <<< and wait for ENTER; auto: proceed after the same gate.',
            'Revalidate the exact demo VM ID; az vm stop --ids ' + self.target_id + ' --no-wait (no deallocation).',
            'Keep production/probes running; record node conditions, Pod UIDs/deletions, Kubernetes events and consumer assignments/lag.',
            'Observe surviving replicas serving and advancing state separately from replacement replica readiness; record taint/deletion timestamps for the 30-second tolerance.',
            'Require both new replicas Ready on Zone 2, zero measured lag and at least 120 seconds of post-stop workload; timeout at 600 seconds.',
            'Finish a full four-event cycle, drain, validate SQL events/payloads/versions and final GraphQL; report integrity, failover and replica capacity separately with all GraphQL failures/counts.',
            'Keep the Zone-1 VM stopped; reset-demo.sh is an explicit separate operation.']
        self.write('planned-actions.json', plan)
        print('\nPLANNED LIVE ACTIONS (not executed):', flush=True)
        for n, line in enumerate(plan, 1):
            print(f'{n}. {line}', flush=True)

    def probes(self, halt, shipments):
        fields = ['sequence', 'category', 'scheduled_timestamp_utc', 'started_timestamp_utc', 'finished_timestamp_utc',
                  'latency_ms', 'http_status', 'instance_id', 'region', 'success', 'error_category', 'error_detail']
        with (self.output / 'graphql-probes.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            sequence = 0
            while not halt.is_set():
                scheduled = time.monotonic()
                sequence += 1
                scheduled_utc = utc_now_iso()
                try:
                    row = execute_probe(self.endpoint, build_payload(self.canary), self.canary, 2, 5)
                except Exception as exc:
                    row = {'started_timestamp_utc': scheduled_utc, 'finished_timestamp_utc': utc_now_iso(),
                           'success': 'false', 'error_category': 'request_exception', 'error_detail': sanitize_text(exc)}
                row.update(sequence=sequence, category='availability', scheduled_timestamp_utc=scheduled_utc)
                writer.writerow(row)
                f.flush()
                self.availability.append(row)
                self.event('graphql_probe', **row)
                # Progress probes are separate measurements, also counted in totals.
                if self.progress_ready.is_set() and len(shipments) == 2 and sequence % 3 == 0:
                    progress = self.graphql_states(list(shipments))
                    self.record_progress(progress, 'probe')
                halt.wait(max(0, 1 - (time.monotonic() - scheduled)))

    def append(self, name, obj):
        with (self.output / name).open('a') as f:
            f.write(json.dumps(obj, default=str) + '\n')

    def record_progress(self, result, purpose):
        # One-way measurement gate. After injection every request is scored even
        # if a future caller accidentally clears the readiness event.
        scored = self.progress_ready.is_set() or self.failure_submitted
        row = {**result, 'purpose': purpose, 'scored': scored,
               'phase': 'post-failure' if self.failure_submitted else ('workload' if scored else 'startup')}
        self.append('graphql-progress.jsonl', row)
        self.event('graphql_progress', **row)
        return row

    def start_progress_scoring(self, shipments, acknowledged, snapshot, graphql):
        require(shipments_observable(shipments, acknowledged, snapshot, graphql),
                'Both emitted run shipments must be observable before scored progress checks')
        if not self.progress_ready.is_set():
            self.progress_scoring_started_utc = utc_now_iso()
            self.event('progress_scoring_started', timestamp_utc=self.progress_scoring_started_utc,
                       shipments=list(shipments), states=snapshot['states'])
            self.progress_ready.set()

    def graphql_states(self, shipments):
        result = {'timestamp_utc': utc_now_iso(), 'success': False, 'http_status': 0}
        query = 'query($a:String!,$b:String!){a:shipment(shipmentId:$a){shipmentId latestEventVersion latestEventType latestEventDomain latestLocation} b:shipment(shipmentId:$b){shipmentId latestEventVersion latestEventType latestEventDomain latestLocation}}'
        req = urllib.request.Request(self.endpoint, data=json.dumps({'query': query, 'variables': dict(zip(('a', 'b'), shipments))}).encode(),
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                result.update(http_status=r.status, instance_id=r.headers.get('X-Instance-ID', ''), response=json.load(r))
            result['success'] = (result['http_status'] == 200 and not result['response'].get('errors')
                                 and all((result['response'].get('data') or {}).get(k)
                                         and result['response']['data'][k].get('shipmentId') == sid
                                         and isinstance(result['response']['data'][k].get('latestEventVersion'), int)
                                         and result['response']['data'][k]['latestEventVersion'] > 0
                                         for k, sid in zip(('a', 'b'), shipments)))
        except urllib.error.HTTPError as exc:
            result.update(http_status=exc.code, response_body=exc.read().decode('utf-8', errors='replace'),
                          error=sanitize_text(exc))
        except Exception as exc:
            result['error'] = sanitize_text(exc)
        return result

    def observe(self, cluster, initial_uids):
        nodes = {x['metadata']['name']: x for x in cluster['items'] if x['kind'] == 'Node'}
        pods = [x for x in cluster['items'] if x['kind'] == 'Pod']
        self.append('cluster-observations.jsonl', {'timestamp_utc': utc_now_iso(), 'cluster': cluster})
        replacements = {}
        surviving = {}
        for app in ('aggregator', 'api'):
            group = app_pods(pods, app)
            replacements[app] = [p['metadata']['name'] for p in group if ready(p)
                                 and p['metadata']['uid'] not in initial_uids and p['spec'].get('nodeName') == 'demo-appzone2']
            surviving[app] = [p['metadata']['name'] for p in group if ready(p)
                              and p['metadata']['uid'] in initial_uids and p['spec'].get('nodeName') == 'demo-appzone2']
        status = {'zone1_node_ready': ready(nodes.get('demo-appzone1', {})),
                  'surviving_ready_pods': surviving, 'replacement_ready_pods': replacements,
                  'replacement_redundancy_restored': all(replacements.values()),
                  'surviving_replicas_ready': all(surviving.values())}
        status['zone1_noexecute_taints'] = [t for t in nodes.get('demo-appzone1', {}).get('spec', {}).get('taints', [])
                                           if t.get('effect') == 'NoExecute']
        status['zone1_application_pod_deletions'] = [{'pod': p['metadata']['name'], 'deletion_timestamp': p['metadata'].get('deletionTimestamp')}
                                                   for p in pods if p['metadata'].get('labels', {}).get('app') in ('aggregator', 'api')
                                                   and p['spec'].get('nodeName') == 'demo-appzone1']
        status['replacement_pods'] = [{'pod': p['metadata']['name'], 'app': p['metadata'].get('labels', {}).get('app'),
                                       'node': p['spec'].get('nodeName'), 'phase': p['status'].get('phase'),
                                       'ready': ready(p), 'created_utc': p['metadata']['creationTimestamp'],
                                       'conditions': p['status'].get('conditions', [])}
                                      for p in pods if p['metadata'].get('labels', {}).get('app') in ('aggregator', 'api')
                                      and p['metadata']['uid'] not in initial_uids]
        self.event('cluster_observation', **status)
        return status

    def live(self):
        require(self.mode in ('auto', 'presentation-mode'), 'Live mode must be explicit')
        print('LIVE MODE: will publish unique events and stop only the Zone-1 demo worker after the readiness gate.', flush=True)
        halt = threading.Event()
        expected, acknowledgements, shipments, errors = [], [], [], []
        stream_finished = threading.Event()
        process = None
        producer_stderr = None
        probe_thread = None
        error = None
        last_status, last_deps = {}, {}
        producer_finished = []
        processing_before_replacements = False
        completed_gate = False
        acknowledgements_at_injection = 0
        seen_unavailable = False
        continued_processing = False
        initial_uids = {p['metadata']['uid'] for p in self.initial['items'] if p['kind'] == 'Pod'}
        try:
            producer_stderr = (self.output / 'producer-stderr.log').open('w')
            process = subprocess.Popen(self.remote_args('produce'), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=producer_stderr, text=True, bufsize=1)
            process.stdin.write(json.dumps({'run_id': self.output.name, 'max_seconds': 2400}) + '\n')
            process.stdin.flush()

            def collect():
                try:
                    for line in process.stdout:
                        self.append('producer-stream.jsonl', json.loads(line))
                        row = json.loads(line)
                        if row['kind'] == 'expected':
                            expected.append(row)
                            self.append('expected-events.jsonl', {'topic': row['topic'], **row['event']})
                        elif row['kind'] == 'acknowledged':
                            acknowledgements.append(row)
                            self.append('acknowledged-events.jsonl', row)
                        elif row['kind'] == 'shipments':
                            shipments.extend(row['shipments'])
                            self.write('shipments.json', shipments)
                        elif row['kind'] == 'error':
                            errors.append(row['error'])
                        elif row['kind'] == 'producer_finished':
                            producer_finished.append(row)
                except Exception as exc:
                    errors.append(sanitize_text(exc))
                finally:
                    stream_finished.set()

            collector = threading.Thread(target=collect, daemon=True)
            collector.start()
            def probe_safely():
                try:
                    self.probes(halt, shipments)
                except Exception as exc:
                    self.thread_errors.append(sanitize_text(exc))
                    self.event('probe_collector_failed', error=sanitize_text(exc))

            probe_thread = threading.Thread(target=probe_safely, daemon=True)
            probe_thread.start()
            deadline = time.monotonic() + 120
            while True:
                require(not stream_finished.is_set() and not errors and not self.thread_errors,
                        'Producer/probes stopped before failure readiness: ' + str(errors + self.thread_errors))
                if len(acknowledgements) >= 8 and len(shipments) == 2:
                    deps = self.snapshot(shipments)
                    graph = self.graphql_states(shipments)
                    self.append('dependency-observations.jsonl', deps)
                    self.record_progress(graph, 'readiness')
                    covered = {(a['topic'], a['partition']) for a in acknowledgements}
                    if (len(covered) == 4 and len(deps['history']) >= 4
                            and shipments_observable(shipments, acknowledgements, deps, graph)
                            and any(p['success'] == 'true' for p in self.availability)
                            and all(s['event_version'] >= 2 for s in deps['states']) and len(deps['states']) == 2):
                        self.event('workload_actively_processing', acknowledgements=len(acknowledgements), states=deps['states'])
                        self.start_progress_scoring(shipments, acknowledgements, deps, graph)
                        print('PASS workload active: acknowledged on both topics/partitions; SQL and GraphQL show processing.', flush=True)
                        break
                require(time.monotonic() < deadline, 'Workload never became demonstrably active')
                time.sleep(2)
            if self.mode == 'presentation-mode':
                print('\n>>> READY TO INJECT FAILURE: ZONE 1 APPLICATION WORKER <<<', flush=True)
                print('Press ENTER to stop only vm-demo-appzone1; Ctrl-C cancels.', flush=True)
                # Bound waiting so a lost console cannot leave production running forever.
                import select
                require(select.select([sys.stdin], [], [], 1200)[0], 'Presentation confirmation timed out; no failure injected')
                require(sys.stdin.readline() == '\n', 'ENTER confirmation not received; no failure injected')
            require(not stream_finished.is_set() and not errors and not self.thread_errors
                    and probe_thread.is_alive() and len(acknowledgements) >= 8 and self.progress_ready.is_set(),
                    'Producer stopped while waiting; failure injection disarmed')
            # Recheck workload, cluster and external dependencies after any presentation pause.
            graph = self.graphql_states(shipments)
            self.record_progress(graph, 'pre-stop')
            deps = self.snapshot(shipments)
            self.append('dependency-observations.jsonl', deps)
            require(graph['success'] and deps['history'], 'Active workload gate failed; injection disarmed')
            before_stop = self.cluster()
            node_list = [n for n in before_stop['items'] if n['kind'] == 'Node' and n['metadata']['name'] in NODES]
            require(len(node_list) == 3 and all(ready(n) for n in node_list), 'Baseline node readiness changed; injection disarmed')
            for app in ('aggregator', 'api'):
                active = app_pods([p for p in before_stop['items'] if p['kind'] == 'Pod'], app)
                require(len(active) == 2 and all(ready(p) for p in active)
                        and {p['spec']['nodeName'] for p in active} == {'demo-appzone1', 'demo-appzone2'},
                        'Baseline placement/readiness changed; injection disarmed')
            require(two_consumers(deps), 'Consumer membership changed; injection disarmed')
            self.observe(before_stop, initial_uids)
            acknowledgements_at_injection = len(acknowledgements)
            self.vm_action('stop')
            injected_at = time.monotonic()
            seen_replacements = False
            at_injection_versions = {s['shipment_id']: s['event_version'] for s in deps['states']}
            deadline = injected_at + 600
            while time.monotonic() < deadline:
                require(not stream_finished.is_set() and not errors and not self.thread_errors and probe_thread.is_alive(),
                        'Producer/probes failed during observation: ' + str(errors + self.thread_errors))
                last_status = self.observe(self.cluster(), initial_uids)
                seen_unavailable |= not last_status['zone1_node_ready']
                seen_replacements |= last_status['replacement_redundancy_restored']
                last_deps = self.snapshot(shipments)
                self.append('dependency-observations.jsonl', last_deps)
                advanced = all(s['event_version'] > at_injection_versions.get(s['shipment_id'], 0) for s in last_deps['states']) and len(last_deps['states']) == 2
                continued_processing |= advanced and seen_unavailable
                processing_before_replacements |= advanced and not last_status['replacement_redundancy_restored']
                elapsed = int(time.monotonic() - injected_at)
                print(f'OBSERVE +{elapsed}s: zone1_ready={last_status["zone1_node_ready"]} '
                      f'survivors_ready={last_status["surviving_replicas_ready"]} '
                      f'replacement_redundancy_restored={last_status["replacement_redundancy_restored"]} '
                      f'processed_versions={[s["event_version"] for s in last_deps["states"]]} '
                      f'zone1_noexecute_taints={len(last_status["zone1_noexecute_taints"])} '
                      f'zone1_deleting_pods={sum(bool(p["deletion_timestamp"]) for p in last_status["zone1_application_pod_deletions"])}', flush=True)
                if (elapsed >= 120 and seen_unavailable and seen_replacements and continued_processing
                        and not last_status['zone1_node_ready'] and processing_before_replacements
                        and len(acknowledgements) >= acknowledgements_at_injection + 8
                        and len({(a['topic'], a['partition']) for a in acknowledgements[acknowledgements_at_injection:]}) == 4
                        and last_status['surviving_replicas_ready'] and zero_lag(last_deps) and two_consumers(last_deps)):
                    completed_gate = True
                    break
                time.sleep(3)
            require(completed_gate, 'Timed out proving node loss, continued processing, replacement redundancy and zero lag')
        except (Exception, KeyboardInterrupt) as exc:
            error = sanitize_text(exc) or 'Interrupted by operator'
            self.event('run_error', error=error)
        finally:
            if process is not None:
                try:
                    process.stdin.write('STOP\n')
                    process.stdin.flush()
                    process.stdin.close()
                except (BrokenPipeError, OSError):
                    pass
                try:
                    process.wait(timeout=75)
                    if not stream_finished.wait(5):
                        errors.append('Producer evidence collector did not finish reading the stream')
                    elif hasattr(process.stdout, 'close'):
                        process.stdout.close()
                    if process.returncode != 0:
                        errors.append('Producer transport/process exited with status ' + str(process.returncode))
                    if not producer_finished:
                        errors.append('Producer completion marker not observed')
                except subprocess.TimeoutExpired:
                    errors.append('Producer did not stop within 75 seconds; evidence may be incomplete')
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
            if producer_stderr is not None:
                producer_stderr.close()
            # Keep probing throughout drain/final checks, including failure paths.
            if shipments:
                try:
                    deadline = time.monotonic() + 120
                    while True:
                        last_deps = self.snapshot(shipments)
                        self.append('dependency-observations.jsonl', last_deps)
                        report = integrity(expected, acknowledgements, last_deps)
                        if (report['pass'] and zero_lag(last_deps) and two_consumers(last_deps)) or time.monotonic() >= deadline:
                            break
                        time.sleep(3)
                    self.write('integrity.json', report)
                    self.write('dependencies-final.json', last_deps)
                except Exception as exc:
                    errors.append('Final SQL/lag evidence unavailable: ' + sanitize_text(exc))
            halt.set()
            if probe_thread:
                probe_thread.join(timeout=20)
        report = integrity(expected, acknowledgements, last_deps)
        if len(shipments) == 2:
            final_graphql = self.graphql_states(shipments)
            self.record_progress(final_graphql, 'final-validation')
        else:
            final_graphql = {'success': False, 'not_requested_reason': 'Both run shipment IDs are unavailable'}
        self.write('graphql-final.json', final_graphql)
        graph_matches = final_graphql.get('success', False)
        if graph_matches:
            states = {s['shipment_id']: s for s in last_deps['states']}
            for value in final_graphql['response']['data'].values():
                state = states.get(value['shipmentId'], {})
                graph_matches &= all(value.get(k) == state.get(v) for k, v in (
                    ('latestEventVersion', 'event_version'), ('latestEventType', 'event_type'),
                    ('latestEventDomain', 'domain'), ('latestLocation', 'location')))
        probes = []
        if (self.output / 'graphql-probes.csv').exists():
            with (self.output / 'graphql-probes.csv').open() as probe_file:
                probes = list(csv.DictReader(probe_file))
        progress = [json.loads(line) for line in (self.output / 'graphql-progress.jsonl').read_text().splitlines()] if (self.output / 'graphql-progress.jsonl').exists() else []
        counts = count_probes(probes, progress)
        successful, total = counts['successful_graphql_probes'], counts['total_graphql_probes']
        stopped_vm = None
        if self.failure_submitted:
            try:
                stopped_vm = self.az_read('vm', 'show', '-g', self.c['rg'], '-n', TARGET_VM, '--show-details')
                self.write('azure-failure-final.json', {k: stopped_vm.get(k) for k in ('id', 'name', 'zones', 'powerState')})
                require(stopped_vm.get('powerState') == 'VM stopped', 'Azure does not confirm the selected VM stopped')
            except Exception as exc:
                errors.append(sanitize_text(exc))
        failure_confirmed = bool(stopped_vm and stopped_vm.get('powerState') == 'VM stopped')
        failover_observed = bool(failure_confirmed and seen_unavailable and continued_processing and processing_before_replacements)
        capacity_restored = bool(last_status.get('replacement_redundancy_restored') and last_status.get('surviving_replicas_ready'))
        execution_completed = bool(not error and not errors and not self.thread_errors and completed_gate)
        validation_pass = bool(execution_completed and report['pass'] and failover_observed and capacity_restored
                               and graph_matches and zero_lag(last_deps) and two_consumers(last_deps) and total)
        startup_progress = [r for r in progress if not scored_progress(r)]
        summary = {'summary_schema_version': 2, 'execution_completed': execution_completed,
                   'outcomes': {'event_integrity': 'PASS' if report['pass'] else 'FAIL',
                                'failover_observed': 'PASS' if failover_observed else 'FAIL',
                                'replica_capacity_restored': 'PASS' if capacity_restored else 'FAIL'},
                   # Retain the former strict assessment for audit/comparison;
                   # presentation and exit status no longer require 100% GraphQL.
                   'strict_pass': bool(validation_pass and successful == total),
                   'strict_graphql_availability_pass': bool(total and successful == total),
                   'exit_code': 0 if validation_pass else 1,
                   'mode': self.mode, 'failure_requested': self.failure_submitted, 'failure_injected': failure_confirmed,
                   'failure_target': TARGET_VM, 'error': error, 'producer_errors': errors,
                   'probe_collector_errors': self.thread_errors,
                   'processing_observed_before_replacement_readiness': processing_before_replacements,
                   'post_failure_acknowledgements': len(acknowledgements) - acknowledgements_at_injection if self.failure_submitted else 0,
                   'integrity': report, 'final_graphql_matches_postgresql': graph_matches,
                   'final_consumer_lag': consumer_lag(last_deps),
                   'missing_event_count': len(report['missing_events']),
                   'duplicate_event_count': report['duplicate_event_count'],
                   **counts,
                   'availability_probe_count': len(probes), 'progress_probe_count': len(progress) - len(startup_progress),
                   'raw_progress_probe_count': len(progress),
                   'startup_progress_probe_count': len(startup_progress),
                   'startup_progress_failed_count': sum(r['success'] is not True for r in startup_progress),
                   'progress_scoring_started_utc': self.progress_scoring_started_utc,
                   'replacement_readiness_meaning': 'Replica redundancy restored; service continuity measured independently by GraphQL probes and advancing shipment state.'}
        self.write('integrity.json', report)
        self.write('summary.json', summary)
        print('\n'.join(presentation_lines(summary)), flush=True)
        print(f'Startup progress checks (unscored): {len(startup_progress)}; '
              f'failed: {summary["startup_progress_failed_count"]}', flush=True)
        if not execution_completed:
            print('Execution incomplete: ' + str(error or errors or self.thread_errors or 'Observation gate not completed'), flush=True)
        elif not validation_pass:
            print('Final validation incomplete or failed; inspect summary.json for component, GraphQL state and lag evidence.', flush=True)
        print('Evidence: ' + str(self.output), flush=True)
        if self.failure_submitted:
            print(('Zone-1 worker is confirmed stopped.' if failure_confirmed else 'Zone-1 stop was requested; completion is unconfirmed.')
                  + ' Restore/check with ./demo/reset-demo.sh', flush=True)
        return summary['exit_code']

    def reset(self):
        require(self.mode == 'reset', 'Reset mode must be explicit')
        vms = self.az_read('vm', 'list', '-g', self.c['rg'], '--show-details')
        vm = next(v for v in vms if v['name'] == TARGET_VM)
        self.target_id = validate_target(vm, self.c['subscription'], self.c['rg'])
        if vm.get('powerState') != 'VM running':
            print('RESET: restore only vm-demo-appzone1; wait for node Ready; rebalance demo replicas.', flush=True)
            self.vm_action('start')
        deadline = time.monotonic() + 360
        while True:
            cluster = self.cluster()
            node = next(i for i in cluster['items'] if i['kind'] == 'Node' and i['metadata']['name'] == 'demo-appzone1')
            if ready(node):
                break
            require(time.monotonic() < deadline, 'Zone-1 worker did not become Ready')
            time.sleep(5)
        pods = [i for i in cluster['items'] if i['kind'] == 'Pod']
        balanced = all({p['spec']['nodeName'] for p in app_pods(pods, a) if ready(p)} == {'demo-appzone1', 'demo-appzone2'}
                       and len(app_pods(pods, a)) == 2 for a in ('aggregator', 'api'))
        if not balanced:
            worker2 = next(i for i in cluster['items'] if i['kind'] == 'Node' and i['metadata']['name'] == 'demo-appzone2')
            require(not worker2.get('spec', {}).get('unschedulable'), 'Surviving worker was already cordoned; do not change external maintenance state')
            print('RESET Kubernetes changes: temporarily cordon demo-appzone2; PDB-respecting eviction of at most one excess replica/service; then uncordon.', flush=True)
            cordoned = False
            try:
                self.kube('cordon', 'demo-appzone2', mutation=True)
                cordoned = True
                for app in ('aggregator', 'api'):
                    current = json.loads(self.kube('get', 'pods', '-n', NAMESPACE, '-l', 'app=' + app, '-o', 'json'))['items']
                    running = [p for p in app_pods(current, app) if ready(p)]
                    if {p['spec']['nodeName'] for p in running} == {'demo-appzone2'} and len(running) == 2:
                        pod = running[0]
                        body = {'apiVersion': 'policy/v1', 'kind': 'Eviction', 'metadata': {'name': pod['metadata']['name'], 'namespace': NAMESPACE},
                                'deleteOptions': {'preconditions': {'uid': pod['metadata']['uid']}}}
                        self.kube('create', '--raw', '/api/v1/namespaces/' + NAMESPACE + '/pods/' + pod['metadata']['name'] + '/eviction',
                                  '-f', '-', data=json.dumps(body), mutation=True)
                    deadline = time.monotonic() + 240
                    while True:
                        current = json.loads(self.kube('get', 'pods', '-n', NAMESPACE, '-l', 'app=' + app, '-o', 'json'))['items']
                        running = [p for p in app_pods(current, app) if ready(p)]
                        if len(running) == 2 and {p['spec']['nodeName'] for p in running} == {'demo-appzone1', 'demo-appzone2'}:
                            break
                        require(time.monotonic() < deadline, 'Could not restore per-worker placement: ' + app)
                        time.sleep(3)
            finally:
                if cordoned:
                    self.kube('uncordon', 'demo-appzone2', mutation=True)
        deadline = time.monotonic() + 180
        while True:
            try:
                result = self.preflight()
                break
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(5)
        result.update(mode='reset', environment_ready=True)
        self.write('summary.json', result)
        print('DEMO ENVIRONMENT READY', flush=True)
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', choices=['appzone1'], nargs='?', default='appzone1')
    mode = parser.add_mutually_exclusive_group(required=True)
    for name in ('dry-run', 'presentation-mode', 'auto', 'check', 'reset'):
        mode.add_argument('--' + name, dest='mode', action='store_const', const=name)
    args = parser.parse_args(argv)
    require(args.mode != 'presentation-mode' or sys.stdin.isatty(), 'Presentation mode requires an interactive terminal')
    (HERE / 'results').mkdir(exist_ok=True)
    lock = (HERE / '.private/orchestrator.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise RuntimeError('Another demo check/run/reset is already active')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8] + '-' + args.mode
    output = HERE / 'results' / run_id
    output.mkdir(mode=0o700)
    demo = Demo(args.mode, output)
    demo.write('run.json', {'run_id': run_id, 'mode': args.mode, 'started_utc': utc_now_iso(), 'target': TARGET_VM})

    def interrupted(signum, frame):
        raise KeyboardInterrupt('Signal ' + str(signum))

    previous_sigterm = signal.signal(signal.SIGTERM, interrupted)
    try:
        if args.mode == 'reset':
            return demo.reset()
        result = demo.preflight()
        demo.write('preflight.json', result)
        if args.mode in ('dry-run', 'check'):
            if args.mode == 'dry-run':
                demo.plan()
            result.update(mode=args.mode, azure_resources_modified=False, kubernetes_objects_modified=False,
                          events_produced=0, failure_injected=False)
            demo.write('summary.json', result)
            print('\nPASS ' + args.mode + ': all baseline checks passed; events produced=0; Azure changes=0; Kubernetes object changes=0; VM stops=0.', flush=True)
            print('Evidence: ' + str(output), flush=True)
            return 0
        return demo.live()
    except (Exception, KeyboardInterrupt) as exc:
        error = sanitize_text(exc) or 'Interrupted by operator'
        demo.write('summary.json', {'pass': False, 'mode': args.mode, 'error': error,
                                   'failure_requested': demo.failure_submitted,
                                   'failure_injected': None if demo.failure_submitted else False})
        print('FAIL ' + args.mode + ': ' + error, file=sys.stderr, flush=True)
        print('Evidence: ' + str(output), flush=True)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        lock.close()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print('FAIL: ' + sanitize_text(exc), file=sys.stderr)
        sys.exit(1)
