"""Bounded integration checks, NOT a load generator or benchmark.

Creates two unprivileged disposable clients on the existing bridge. Sends at most
65 sequential requests/connections per jail, verifies actual packet counters,
and always unbans/removes its own clients. Does not print credentials or bodies.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
HOST = subprocess.check_output(['bash', str(ROOT / 'lab.sh'), 'docker-host'], text=True).strip()
DOCKER = ['docker', '--host', HOST]
NETWORK = 'ciber-p1-games_lab'
CLIENTS = ['games-check-a', 'games-check-b']
report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'daemon': HOST, 'jails': []}

PROBE = r'''
import http.client, json, socket, ssl, sys
mode, host, port, path, count = sys.argv[1:]
port, count = int(port), int(count)
out = []
for _ in range(count):
    try:
        if mode == 'http':
            conn = http.client.HTTPConnection(host, port, timeout=1)
            conn.request('GET', path, headers={'Connection':'close', 'Authorization':'Bearer header-canary', 'Cookie':'cookie-canary'})
            response = conn.getresponse()
            response.read()
            out.append(str(response.status))
            conn.close()
        else:
            context = ssl.create_default_context(cafile='/tls/ca.crt')
            if mode == 'untrusted':
                context = ssl.create_default_context()
            name = 'wrong-name.invalid' if mode == 'wrong-name' else 'openldap'
            with socket.create_connection((host, port), timeout=1) as raw:
                with context.wrap_socket(raw, server_hostname=name):
                    out.append('TLS_OK')
    except ssl.SSLCertVerificationError:
        out.append('CERT_REJECTED')
    except (OSError, http.client.HTTPException):
        out.append('CONNECTION_FAILED')
print(json.dumps(out))
'''


def docker(*args):
    return subprocess.check_output(DOCKER + list(args), text=True)


def execute(service, *args):
    return docker('exec', f'ciber-p1-games-{service}-1', *args)


def probe(client, service, port, path='/', count=1, mode='http'):
    return json.loads(docker('exec', client, 'python3', '-c', PROBE,
                            mode, service, str(port), path, str(count)))


def access_log(service):
    path = '/opt/keycloak/data/log/keycloak-http-access.log' if service == 'keycloak' else '/var/log/security/access.log'
    return execute(service, 'python3', '-c', 'from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text())', path)


def banned(service, jail):
    status = execute(service, 'fail2ban-client', 'status', jail)
    return status.split('Banned IP list:', 1)[1].split()


def counter(service, jail, ip):
    rules = execute(service, 'iptables', '-nvxL', 'f2b-' + jail)
    for line in rules.splitlines():
        fields = line.split()
        if ip in fields and fields[2] in ('REJECT', 'DROP'):
            return int(fields[0])
    raise AssertionError('Missing source-specific firewall rule')


def main():
    backend = json.loads(docker('inspect', 'ciber-p1-games-backend-1'))[0]
    assert NETWORK in backend['NetworkSettings']['Networks']
    assert not any(json.loads(docker('inspect', name))[0]['HostConfig']['Privileged']
                   for name in [f'ciber-p1-games-{s}-1' for s in ('frontend', 'backend', 'keycloak', 'openldap')])
    ips = []
    for client in CLIENTS:
        docker('run', '-d', '--name', client, '--network', NETWORK,
               '--mount', f'type=bind,source={ROOT}/.lab-data/tls/ca.crt,target=/tls/ca.crt,readonly',
               '--entrypoint', 'python3', 'ciber-p1-games-backend:dev', '-c', 'import time; time.sleep(600)')
        ips.append(json.loads(docker('inspect', client))[0]['NetworkSettings']['Networks'][NETWORK]['IPAddress'])
    assert ips[0] != ips[1]
    report['client_ips'] = ips
    print('Client socket IPs:', ', '.join(ips), flush=True)

    assert probe(CLIENTS[1], 'openldap', 636, mode='tls') == ['TLS_OK']
    assert probe(CLIENTS[1], 'openldap', 636, mode='untrusted') == ['CERT_REJECTED']
    assert probe(CLIENTS[1], 'openldap', 636, mode='wrong-name') == ['CERT_REJECTED']
    cleartext = docker('exec', CLIENTS[1], 'python3', '-c',
        "import socket; s=socket.socket(); s.settimeout(2); print(s.connect_ex(('openldap',389)) != 0)")
    assert cleartext.strip() == 'True', 'Cleartext LDAP listener remains accessible'
    bypass = docker('exec', CLIENTS[1], 'python3', '-c',
        "import socket; s=socket.socket(); s.settimeout(2); print(s.connect_ex(('backend',8008)) != 0)")
    assert bypass.strip() == 'True', 'Uvicorn reachable from bridge'
    report['tls'] = {'trusted_ca_and_name': True, 'untrusted_ca_rejected': True,
                     'wrong_name_rejected': True, 'port_389_closed': True, 'uvicorn_bridge_closed': True}
    print('PASS: TLS CA/name verification, cleartext closed, Uvicorn not bypassable', flush=True)

    targets = [('frontend', 4200, '/', 'http-flood', 'http', '200'),
               ('backend', 8000, '/health', 'http-flood', 'http', '200'),
               ('keycloak', 8080, '/realms/games-lab/.well-known/openid-configuration', 'http-flood', 'http', '200'),
               ('openldap', 636, '/', 'ldaps-connections', 'tls', 'TLS_OK')]
    try:
        for service, port, path, jail, mode, good in targets:
            assert ips[0] not in banned(service, jail)
            # Verify observed peer before exceeding the threshold; no spoofed headers.
            query = '?query-canary=not-for-logs' if mode == 'http' else ''
            assert probe(CLIENTS[0], service, port, path + query, mode=mode) == [good]
            time.sleep(.3)
            logs = access_log(service)
            assert any(line.startswith(ips[0] + ' ') if mode == 'http' else
                       'ACCEPT from IP=' + ips[0] + ':' in line for line in logs.splitlines()), 'Peer IP mismatch'
            assert all(value not in logs for value in ('query-canary', 'header-canary', 'cookie-canary', '?'))
            matches = probe(CLIENTS[0], service, port, path, count=65, mode=mode)
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline and ips[0] not in banned(service, jail):
                time.sleep(.2)
            assert ips[0] in banned(service, jail), service + ': no Ban'
            before = counter(service, jail, ips[0])
            assert probe(CLIENTS[0], service, port, path, mode=mode) == ['CONNECTION_FAILED']
            after = counter(service, jail, ips[0])
            assert after > before, service + ': no packet counter increase'
            assert probe(CLIENTS[1], service, port, path, mode=mode) == [good], 'Client B unavailable'
            f2blog = execute(service, 'python3', '-c',
                'from pathlib import Path; print(Path("/var/log/fail2ban.log").read_text())')
            assert re.search(r'\[' + jail + r'\]\s+Ban\s+' + re.escape(ips[0]), f2blog)
            path_log = '/opt/keycloak/data/log/keycloak-http-access.log' if service == 'keycloak' else '/var/log/security/access.log'
            regex_output = execute(service, 'fail2ban-regex', path_log,
                '/etc/fail2ban/filter.d/' + jail + '.conf', '--print-no-missed')
            summary = re.search(r'Lines: (\d+) lines, (\d+) ignored, (\d+) matched, (\d+) missed', regex_output)
            assert summary and int(summary[3]) >= 60, 'Filter did not match real events'
            assert int(summary[4]) == 0, 'Unexpected unmatched access records'
            execute(service, 'fail2ban-client', 'set', jail, 'unbanip', ips[0])
            assert probe(CLIENTS[0], service, port, path, mode=mode) == [good], 'No recovery after unban'
            report['jails'].append({'service': service, 'jail': jail, 'observed_ip': ips[0],
                'ban_logged': True, 'counter_before': before, 'counter_after': after,
                'client_b_ok': True, 'recovered': True, 'regex_matched': int(summary[3]),
                'bounded_attempts': len(matches)})
            print(f'PASS: {service}: Ban, packets {before}->{after}, B OK, unban recovery, regex OK', flush=True)
    finally:
        for service, _, _, jail, _, _ in targets:
            if ips[0] in banned(service, jail):
                execute(service, 'fail2ban-client', 'set', jail, 'unbanip', ips[0])
    keycloak_ip = json.loads(docker('inspect', 'ciber-p1-games-keycloak-1'))[0]['NetworkSettings']['Networks'][NETWORK]['IPAddress']
    assert keycloak_ip not in banned('openldap', 'ldaps-connections')
    report['keycloak_not_banned_by_ldap'] = True
    out = ROOT / 'test-results'
    out.mkdir(exist_ok=True)
    (out / 'security.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    finally:
        for client in CLIENTS:
            subprocess.run(DOCKER + ['rm', '-f', client], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
