"""Exercise actual PID-1 behavior in disposable frontend copies, no published ports."""
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
host = subprocess.check_output(['bash', str(ROOT / 'lab.sh'), 'docker-host'], text=True).strip()
docker = ['docker', '--host', host]

for name, failure in [('games-supervisor-server', ['nginx', '-s', 'quit']),
                      ('games-supervisor-f2b', ['fail2ban-client', 'stop'])]:
    try:
        subprocess.run(docker + ['run', '-d', '--name', name, '--network', 'none', '--cap-add', 'NET_ADMIN',
                                'ciber-p1-games-frontend:dev'], check=True, stdout=subprocess.DEVNULL)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            ready = subprocess.run(docker + ['exec', name, 'python3', '/opt/security/health.py'],
                                   capture_output=True).returncode == 0
            if ready:
                break
            time.sleep(.2)
        assert ready, 'Disposable copy did not become ready'
        subprocess.run(docker + ['exec', name, *failure], check=True, capture_output=True)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            state = subprocess.check_output(docker + ['inspect', name,
                '--format', '{{.State.Running}} {{.State.ExitCode}}'], text=True).strip()
            if state.startswith('false'):
                break
            time.sleep(.2)
        assert state == 'false 1', 'Critical process failure did not terminate PID 1'
        print('PASS:', name, 'container exits with status 1 on critical process failure')
    finally:
        subprocess.run(docker + ['rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
