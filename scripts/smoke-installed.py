"""Run the installed CLI from outside its checkout and verify real results and service cleanup."""
import os
import re
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

base = Path(os.environ['SHADOWLAB_HOME']).resolve()
with tempfile.TemporaryDirectory() as working:
    result = subprocess.run([str(Path(sys.argv[1]).resolve()), 'Repl'], cwd=working,
                            input='demo\nreport\nquit\n', text=True, capture_output=True,
                            env={**os.environ, 'SHADOWLAB_NO_OPEN': '1'}, timeout=1000)
    print(result.stdout)
    assert result.returncode == 0, result.stderr
    assert 'Demo incomplete' not in result.stdout
    assert 'Investigation: completed' in result.stdout
    for fragment in ('CONFIRMED — Endpoint may be missing authentication',
                     'CONFIRMED — Object access may omit ownership validation',
                     'CONFIRMED — Response may expose sensitive fields'):
        assert fragment in result.stdout, fragment
    assert not (Path(working) / '.shadowlab').exists()
    reports = list((base / 'runs').glob('*/report-*.md'))
    assert reports, 'No report exported'
    latest = max(reports, key=lambda path: path.stat().st_mtime)
    text = latest.read_text()
    for value in ('demo-alice', 'demo-bob', 'alice-password-hash', 'sk-demo-private-key'):
        assert value not in text, 'Synthetic credential appeared in the report'
    token = (latest.parent / 'api-token').read_text()
    assert token not in text and token not in result.stdout
    # Logs contain only local service addresses; never print token-bearing state.
    for log in ('api.log', 'web.log', 'demo.log'):
        ports = re.findall(r'http://127\.0\.0\.1:(\d+)', (latest.parent / log).read_text())
        assert ports, f'No launched address recorded in {log}'
        for port in set(ports):
            with socket.socket() as probe:
                probe.settimeout(1)
                assert probe.connect_ex(('127.0.0.1', int(port))) != 0, f'{log} still listening'
print('Installed demo passed; all three service ports closed; report sanitized')
