"""One serial build with durable plain progress, surviving API/tool timeouts.

python3 scripts/build_observed.py start|status SERVICE
"""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
action, service = sys.argv[1:]
assert service in ('backend', 'openldap', 'keycloak', 'frontend')
output = ROOT / 'test-results'
output.mkdir(exist_ok=True)
state = output / f'build-{service}.json'
log = output / f'build-{service}.log'

if action == 'worker':
    result = subprocess.run(['bash', str(ROOT / 'lab.sh'), 'build', service], cwd=ROOT)
    state.write_text(json.dumps({'pid': os.getpid(), 'exit_code': result.returncode}))
elif action == 'start':
    if state.exists():
        previous = json.loads(state.read_text())
        if 'exit_code' not in previous:
            try:
                os.kill(previous['pid'], 0)
            except ProcessLookupError:
                pass
            else:
                raise SystemExit('Build already active; use status instead of starting another.')
    with log.open('a', buffering=1) as stream:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'worker', service],
            cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    state.write_text(json.dumps({'pid': process.pid}))
    print(f'Build PID {process.pid}; detailed log: {log}')
elif action == 'status':
    print(state.read_text() if state.exists() else 'Not started')
    if log.exists():
        print('\n'.join(log.read_text().splitlines()[-45:]))
else:
    raise SystemExit('Unknown action')
