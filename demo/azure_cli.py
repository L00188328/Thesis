#!/usr/bin/env python3
"""Disposable Azure CLI processes sharing a persistent login volume.

Never resolve or store a container ID. Each invocation creates its own helper,
and Docker removes only that helper when the command ends. An existing config
volume is required so a missing volume never silently creates an empty login.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.experiments.common import sanitize_text

DEFAULT_IMAGE = 'mcr.microsoft.com/azure-cli:2.89.0'
DEFAULT_VOLUME = 'thesis-azure-cli-config'


def settings(config=None):
    config = config or {}
    volume = os.environ.get('DEMO_AZURE_CLI_CONFIG_VOLUME', config.get('azure_cli_config_volume', DEFAULT_VOLUME))
    image = os.environ.get('DEMO_AZURE_CLI_IMAGE', config.get('azure_cli_image', DEFAULT_IMAGE))
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', volume):
        raise ValueError('Invalid Azure CLI config volume name')
    if not image or image.startswith('-') or any(c.isspace() for c in image):
        raise ValueError('Invalid Azure CLI image name')
    return volume, image


def command_args(config, *args, interactive=False):
    volume, image = settings(config)
    command = ['docker', 'run', '--rm']
    if interactive:
        command.append('-i')
    return command + [
        '--mount', f'type=volume,source={volume},target=/root/.azure',
        '--mount', f'type=bind,source={ROOT},target=/work',
        '--workdir', '/work',
        '--env', 'AZURE_CONFIG_DIR=/root/.azure',
        '--env', 'AZURE_CORE_COLLECT_TELEMETRY=false',
        '--env', 'AZURE_CORE_LOGIN_EXPERIENCE_V2=off',
        image, 'az', *args,
    ]


def execute(command, timeout=1800):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(sanitize_text(result.stderr[-6000:]))
    return result.stdout


def require_volume(config, executor):
    volume, _ = settings(config)
    try:
        actual = executor(['docker', 'volume', 'inspect', volume, '--format', '{{.Name}}'], timeout=30)
    except RuntimeError as exc:
        raise RuntimeError(f'Cannot access existing Azure CLI config volume {volume}. '
                           'Check Docker Desktop is running and the original volume exists. '
                           'No empty replacement volume was created. ' + str(exc)) from exc
    if actual.strip() != volume:
        raise RuntimeError('Azure CLI config volume identity mismatch')


def run_cli(config, *args, executor=None, timeout=1800):
    executor = executor or execute
    require_volume(config, executor)
    try:
        return executor(command_args(config, *args), timeout=timeout)
    except RuntimeError as exc:
        message = str(exc)
        if 'AADSTS' in message or 'az login' in message or 'az account set' in message:
            message += '\nRenew the persistent login with: ./demo/azure-cli.sh login --use-device-code'
        raise RuntimeError(message) from exc


def main():
    if len(sys.argv) == 1:
        print('Usage: ./demo/azure-cli.sh <az arguments>')
        return 2
    path = Path(os.environ.get('DEMO_STATE_FILE', str(ROOT / 'demo/.private/state.json')))
    config = json.loads(path.read_text()) if path.exists() else {}
    require_volume(config, execute)
    # Inherit the operator terminal for device-code authentication. No logout,
    # account reset or resource operation is performed implicitly.
    return subprocess.call(command_args(config, *sys.argv[1:], interactive=sys.stdin.isatty()))


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print('Azure CLI helper failed: ' + sanitize_text(exc), file=sys.stderr)
        sys.exit(1)
