import subprocess
from types import SimpleNamespace

import pytest

from packages.core.doctor import launcher_checks, show_setup


@pytest.mark.parametrize('version,ready', [('v22.0.0\n', True), ('v24.19.0\n', True), ('v20.0.0\n', False),
                                          ('invalid synthetic-secret', False)])
def test_node_version_is_checked_without_echoing_raw_output(monkeypatch, version, ready):
    monkeypatch.setattr('packages.core.doctor.shutil.which', lambda tool: '/trusted/' + tool)
    monkeypatch.setattr('packages.core.doctor.subprocess.run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=version))
    checks = launcher_checks()
    assert checks[0]['ready'] is ready and 'synthetic-secret' not in str(checks)


def test_missing_and_timed_out_tools_are_actionable(monkeypatch):
    monkeypatch.setattr('packages.core.doctor.shutil.which', lambda tool: None)
    output = []
    show_setup(output.append)
    assert 'Install Node.js 22' in '\n'.join(output) and 'Source-only' in '\n'.join(output)
    monkeypatch.setattr('packages.core.doctor.shutil.which', lambda tool: '/trusted/' + tool)
    def timed_out(*a, **k):
        raise subprocess.TimeoutExpired('node', 5)
    monkeypatch.setattr('packages.core.doctor.subprocess.run', timed_out)
    assert launcher_checks()[0]['ready'] is False
