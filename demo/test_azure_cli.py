"""Offline regression checks for persistent auth and disposable CLI processes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from demo import azure_cli
from demo.demo_failover import Demo


class AzureCLIHelperTests(unittest.TestCase):
    def test_each_call_creates_new_helper_and_ignores_legacy_container_id(self):
        executor = Mock(side_effect=[azure_cli.DEFAULT_VOLUME, '{}', azure_cli.DEFAULT_VOLUME, '{}'])
        config = {'container': 'deleted-ephemeral-helper'}
        for _ in range(2):
            self.assertEqual(azure_cli.run_cli(config, 'vm', 'list', executor=executor), '{}')
        calls = [call.args[0] for call in executor.call_args_list]
        for command in (calls[1], calls[3]):
            self.assertEqual(command[:3], ['docker', 'run', '--rm'])
            self.assertIn('type=volume,source=thesis-azure-cli-config,target=/root/.azure', command)
            self.assertIn(f'type=bind,source={azure_cli.ROOT},target=/work', command)
            self.assertNotIn('deleted-ephemeral-helper', command)
            self.assertNotIn('--name', command)

    def test_missing_volume_never_creates_an_empty_replacement(self):
        executor = Mock(side_effect=RuntimeError('no such volume'))
        with self.assertRaisesRegex(RuntimeError, 'No empty replacement volume'):
            azure_cli.run_cli({}, 'account', 'show', executor=executor)
        self.assertEqual(executor.call_count, 1)
        self.assertEqual(executor.call_args.args[0][:3], ['docker', 'volume', 'inspect'])

    def test_expired_login_gives_stable_login_command_without_automatic_retry(self):
        executor = Mock(side_effect=[azure_cli.DEFAULT_VOLUME, RuntimeError('AADSTS50173: fresh auth needed')])
        with self.assertRaisesRegex(RuntimeError, r'./demo/azure-cli.sh login --use-device-code'):
            azure_cli.run_cli({}, 'vm', 'show', executor=executor)
        self.assertEqual(executor.call_count, 2)

    def test_readonly_runner_works_with_stale_state_without_accessing_old_helper(self):
        demo = Demo.__new__(Demo)
        demo.c = {'subscription': 'demo-sub', 'container': 'deleted-ephemeral-helper'}
        demo.command = Mock(side_effect=[azure_cli.DEFAULT_VOLUME, '{"powerState":"VM running"}'])
        self.assertEqual(demo.az_read('vm', 'show', '-n', 'vm-demo-appzone1')['powerState'], 'VM running')
        command = demo.command.call_args.args[0]
        self.assertEqual(command[:3], ['docker', 'run', '--rm'])
        self.assertIn('demo-sub', command)
        self.assertNotIn('deleted-ephemeral-helper', command)

    def test_reset_start_uses_same_disposable_helper_and_exact_validated_vm_id(self):
        target = '/subscriptions/demo-sub/resourceGroups/rg-thesis-demo-k3s-test/providers/Microsoft.Compute/virtualMachines/vm-demo-appzone1'
        demo = Demo.__new__(Demo)
        demo.mode = 'reset'
        demo.c = {'subscription': 'demo-sub', 'rg': 'rg-thesis-demo-k3s-test', 'container': 'deleted-ephemeral-helper'}
        demo.target_id = target
        demo.event = Mock()
        demo.az_read = Mock(return_value={'id': target, 'name': 'vm-demo-appzone1', 'zones': ['1'],
                                         'location': 'italynorth', 'tags': {'configuration': 'k3s-phase-f-demo'}})
        demo.command = Mock(side_effect=[azure_cli.DEFAULT_VOLUME, '{}'])
        with patch('sys.stdout'):
            demo.vm_action('start')
        command = demo.command.call_args.args[0]
        self.assertEqual(command[:3], ['docker', 'run', '--rm'])
        self.assertEqual(command[command.index('az') + 1:command.index('az') + 3], ['vm', 'start'])
        self.assertIn(target, command)
        self.assertNotIn('deleted-ephemeral-helper', command)

    def test_login_wrapper_mounts_same_volume_and_inherits_interactive_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'state.json'
            state.write_text(json.dumps({'container': 'deleted-ephemeral-helper'}))
            with patch.dict('os.environ', {'DEMO_STATE_FILE': str(state)}), \
                    patch('sys.argv', ['azure_cli.py', 'login', '--use-device-code']), \
                    patch('sys.stdin.isatty', return_value=True), \
                    patch.object(azure_cli, 'execute', return_value=azure_cli.DEFAULT_VOLUME), \
                    patch.object(azure_cli.subprocess, 'call', return_value=0) as call:
                self.assertEqual(azure_cli.main(), 0)
            command = call.call_args.args[0]
            self.assertIn('-i', command)
            self.assertIn('type=volume,source=thesis-azure-cli-config,target=/root/.azure', command)
            self.assertEqual(command[-3:], ['az', 'login', '--use-device-code'])


if __name__ == '__main__':
    unittest.main()
