"""POSIX smoke test for the installed console's actual terminal editor, without a scan."""
import errno
import json
import os
import pty
import select
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main():
    executable = str(Path(sys.argv[1]).resolve())
    master, slave = pty.openpty()
    transcript = bytearray()
    with tempfile.TemporaryDirectory(prefix='shadow-terminal-') as directory:
        process = subprocess.Popen([executable, 'repl'], cwd=directory,
                                   stdin=slave, stdout=slave, stderr=slave, start_new_session=True,
                                   env={**os.environ, 'TERM': 'xterm', 'SHADOWLAB_NO_OPEN': '1'})
        os.close(slave)
        def wait_for(fragment, offset=0):
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if fragment in transcript[offset:]:
                    return
                if select.select([master], [], [], .1)[0]:
                    try:
                        data = os.read(master, 65536)
                    except OSError as exc:
                        if exc.errno == errno.EIO:
                            break
                        raise
                    if not data:
                        break
                    transcript.extend(data)
            raise AssertionError('Terminal did not produce expected output: ' + repr(fragment))
        try:
            wait_for(b'shadow> ')
            os.write(master, b'/sta\t\n')
            wait_for(b'Context: none.')
            mark = len(transcript)
            os.write(master, b'\033[A\n')  # recall the completed /status command
            wait_for(b'Context: none.', mark)
            mark = len(transcript)
            os.write(master, b'/clear\n')
            wait_for(b'\033[2J\033[H', mark)
            os.write(master, b'/help fix\n')
            wait_for(b'review the diff before use')
            os.write(master, b'/quit\n')
            wait_for(b'ShadowLab closed.')
            assert process.wait(timeout=10) == 0
            assert not list(Path(directory).iterdir()), 'Help/status editing created caller state'
            print(json.dumps({'tab_completion': 'passed', 'input_recall': 'passed',
                              'clear_display': 'passed', 'command_help': 'passed',
                              'outside_checkout': 'passed', 'caller_state_unchanged': True}))
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
            os.close(master)


if __name__ == '__main__':
    main()
