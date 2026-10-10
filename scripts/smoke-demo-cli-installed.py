"""Exercise the installed one-shot bundled CLI, browser proof and cleanup outside checkout."""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix='shadow-cli-demo-') as directory:
        caller = Path(directory)
        package = caller / 'package.json'
        package.write_text('{"scripts":{"postinstall":"touch MUST_NOT_RUN"}}')
        result = subprocess.run([executable, 'demo', '--bundled', '--browser'], cwd=caller,
                                env={**os.environ, 'SHADOWLAB_NO_OPEN': '1'},
                                text=True, capture_output=True, timeout=1000)
        assert result.returncode == 0, result.stderr
        assert 'Bundled demo finished' in result.stdout
        paths = re.findall(r'Sanitized report: (.+)', result.stdout)
        assert len(paths) == 2
        json_path = next(Path(path) for path in paths if path.endswith('.json'))
        payload = json.loads(json_path.read_text())
        assert payload['scan']['status'] == 'completed' and payload['scan']['browser'] is True
        categories = {finding['category']: finding for finding in payload['findings']}
        for category in ('authentication', 'bola', 'exposure'):
            finding = categories[category]
            assert finding['state'] == 'CONFIRMED'
            assert finding['browser']['verdict'] == 'CONFIRMED'
        token = (json_path.parent / 'api-token').read_text()
        combined = result.stdout + result.stderr + ''.join(Path(path).read_text() for path in paths)
        for secret in (token, 'demo-alice', 'demo-bob', 'alice-password-hash', 'sk-demo-private-key'):
            assert secret not in combined, 'Private value appeared in output or exported report'
        for path in paths:
            assert Path(path).stat().st_mode & 0o777 == 0o600
        ports = set()
        for name in ('api.log', 'web.log', 'demo.log'):
            ports.update(re.findall(r'http://127\.0\.0\.1:(\d+)', (json_path.parent / name).read_text()))
        assert len(ports) == 3
        for port in ports:
            with socket.socket() as probe:
                probe.settimeout(1)
                assert probe.connect_ex(('127.0.0.1', int(port))) != 0, 'Owned service still listening'
        assert sorted(path.name for path in caller.iterdir()) == ['package.json']
        print(json.dumps({'installed_bundled_cli': 'passed', 'browser_cases_confirmed': 3,
                          'closed_service_ports': len(ports), 'reports_sanitized': True,
                          'caller_source_unchanged': True, 'evidence_directory': str(json_path.parent)}))


if __name__ == '__main__':
    main()
