"""Bounded prerequisite checks with actionable, credential-free output."""
import os
import re
import shutil
import subprocess

from packages.core.demo_runtime import child_environment


def launcher_checks():
    checks = []
    node = shutil.which('node')
    version = None
    if node:
        try:
            result = subprocess.run([node, '--version'], capture_output=True, text=True,
                                    timeout=5, env=child_environment())
            match = re.fullmatch(r'v(\d+)\.\d+\.\d+', result.stdout.strip())
            if result.returncode == 0 and match:
                version = int(match[1])
        except (OSError, subprocess.TimeoutExpired):
            pass
    checks.append({'name': 'node', 'ready': version is not None and version >= 22,
                   'detail': f'Node major version {version}' if version is not None else 'Missing or version check failed',
                   'action': 'Install Node.js 22 or newer (includes npm).'})
    for tool in ('npm', 'git'):
        checks.append({'name': tool, 'ready': bool(shutil.which(tool)),
                       'detail': 'Found' if shutil.which(tool) else 'Missing',
                       'action': 'Install Node.js 22 or newer.' if tool == 'npm' else 'Install Git.'})
    checks.append({'name': 'platform', 'ready': os.name == 'posix',
                   'detail': 'macOS/Linux supported' if os.name == 'posix' else 'Native Windows launcher unsupported',
                   'action': 'Use a Linux environment such as WSL on Windows.'})
    return checks


def show_setup(output):
    checks = launcher_checks()
    for check in checks:
        output(f"{check['name']}: {'ready' if check['ready'] else 'needs attention'} — {check['detail']}")
        if not check['ready']:
            output(check['action'])
    output('Demo prerequisites ready.' if all(check['ready'] for check in checks)
           else 'Demo setup incomplete. Source-only project analysis does not require Node or npm.')
    output('Browser demo also requires Chromium. Install it with the Playwright in your ShadowLab environment; '
           'see the browser setup commands in the documentation.')
    output('No installation, credential changes or permissions were applied.')
