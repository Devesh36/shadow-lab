"""Linux validation: interrupt an installed console during a real disposable patch experiment."""
import json
import os
import queue
import re
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

lines = queue.Queue()
transcript = []
with tempfile.TemporaryDirectory() as cwd:
    process = subprocess.Popen([str(Path(sys.argv[1]).resolve()), 'repl'], cwd=cwd, text=True,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               env={**os.environ, 'SHADOWLAB_NO_OPEN': '1'})
    def read():
        for line in process.stdout:
            lines.put(line)
    threading.Thread(target=read, daemon=True).start()
    def wait_for(fragment, timeout=90):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                line = lines.get(timeout=.2)
            except queue.Empty:
                if process.poll() is not None:
                    raise ValueError('Console exited before ' + fragment)
                continue
            transcript.append(line)
            if fragment in line:
                return
        raise TimeoutError('Console did not reach ' + fragment)
    try:
        wait_for('1  Demo')
        process.stdin.write('/demo\n')
        process.stdin.flush()
        wait_for('Next:', timeout=900)
        run = Path(re.search(r'Private demo records and logs: (.+)', ''.join(transcript)).group(1))
        process.stdin.write('/fix 1\n')
        process.stdin.flush()
        wait_for('Approving a disposable')
        children = []
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not children:
            for item in Path('/proc').glob('[0-9]*'):
                try:
                    if ((item / 'cwd').resolve().is_relative_to(run / 'patches')
                            and (item / 'comm').read_text().strip().startswith(('node', 'next-server'))):
                        children.append(int(item.name))
                except (OSError, RuntimeError):
                    pass
            time.sleep(.05)
        assert children, 'No live disposable patch process observed; cannot claim cancellation coverage'
        process.send_signal(signal.SIGINT)
        wait_for('Cancelled. Local demo services stopped', timeout=20)
        for pid in children:
            state = Path(f'/proc/{pid}/stat')
            assert not state.exists() or state.read_text().split()[2] == 'Z', 'Patch subprocess still running'
        ports = set()
        for name in ('api.log', 'web.log', 'demo.log'):
            ports.update(re.findall(r'http://127\.0\.0\.1:(\d+)', (run / name).read_text()))
        assert len(ports) == 3
        for port in ports:
            with socket.socket() as probe:
                probe.settimeout(1)
                assert probe.connect_ex(('127.0.0.1', int(port))) != 0, 'Local service still listening'
        process.stdin.write('quit\n')
        process.stdin.flush()
        assert process.wait(timeout=10) == 0
        print(''.join(transcript))
        print(json.dumps({'result': 'passed', 'cancelled_during': 'live disposable patch',
                          'observed_patch_processes': len(children), 'closed_service_ports': len(ports),
                          'run': str(run)}))
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            process.stdin.close()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
