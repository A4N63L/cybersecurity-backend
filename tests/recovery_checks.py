"""Validate isolated restored databases against the live lab without exposing rows.

sudo -n python3 tests/recovery_checks.py ../.lab-backups/recovery-<timestamp>
Only the separately extracted old PG cluster is started for validation. Live data
are neither replaced nor merged. The original tar remains untouched.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = Path(sys.argv[1]).resolve()
assert os.geteuid() == 0, 'Use sudo for the private recovery directory'
assert RECOVERY.parent == ROOT.parent / '.lab-backups'
EXTRACTED = RECOVERY / 'original-extracted/.lab-data'
LIVE = ROOT / '.lab-data'
host = subprocess.check_output(['bash', str(ROOT / 'lab.sh'), 'docker-host'], text=True).strip()
DOCKER = ['docker', '--host', host]
checks = {}


def docker(*args):
    return subprocess.check_output(DOCKER + list(args), text=True)


def ldap_entries(data):
    if data == LIVE:
        # A live MDB logical read uses its own lock; do not copy a running DB.
        content = docker('exec', 'ciber-p1-games-openldap-1', 'slapcat', '-n', '1')
    else:
        # slapcat validates a writable DB directory and creates a lock. Give it
        # a disposable copy of the COLD extraction, never the source archive.
        with tempfile.TemporaryDirectory(dir=RECOVERY, prefix='ldap-validation-') as temporary:
            temporary = Path(temporary)
            for part in ('ldap-config', 'ldap-data'):
                shutil.copytree(data / part, temporary / part)
            content = docker('run', '--rm', '--network', 'none', '--mount',
                f'type=bind,source={temporary}/ldap-config,target=/etc/ldap/slapd.d',
                '--mount', f'type=bind,source={temporary}/ldap-data,target=/var/lib/ldap',
                '--mount', f'type=bind,source={LIVE}/tls,target=/container/service/slapd/assets/certs,readonly',
                '--entrypoint', '/usr/sbin/slapcat', 'ciber-p1-games-openldap:dev', '-n', '1')
    entries = {}
    for block in content.split('\n\n'):
        attributes = {}
        for line in block.splitlines():
            if ': ' in line:
                key, value = line.split(': ', 1)
                attributes.setdefault(key, []).append(value)
        if 'dn' in attributes:
            entries[attributes['dn'][0]] = attributes
    assert entries and any(key.startswith('uid=alice,') for key in entries)
    return entries


def sql(container):
    query = """SELECT json_build_object(
      'realm_id', (SELECT id FROM realm WHERE name='games-lab'),
      'client_id', (SELECT id FROM client WHERE client_id='games-spa'),
      'ldap_id', (SELECT id FROM component WHERE name='games-openldap'),
      'user_count', (SELECT count(*) FROM user_entity WHERE realm_id=(SELECT id FROM realm WHERE name='games-lab'))
    );"""
    return json.loads(docker('exec', container, 'psql', '-U', 'keycloak', '-d', 'keycloak', '-At', '-c', query))


with tarfile.open(RECOVERY / 'current-state.tar') as snapshot:
    for member in snapshot.getmembers():
        if member.isfile() and member.name.startswith('.lab-data/tls/'):
            assert snapshot.extractfile(member).read() == (ROOT / member.name).read_bytes()
    checks['current_tls_files_preserved'] = True
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / 'games.db'
        db_path.write_bytes(snapshot.extractfile('.lab-data/games/games.db').read())
        with sqlite3.connect(db_path) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            db.row_factory = sqlite3.Row
            before = [dict(row) for row in db.execute('SELECT * FROM games')]
        request = urllib.request.Request('http://localhost:8001/api/games',
            headers={'Authorization': 'Bearer preservation.format.only'})
        with urllib.request.urlopen(request) as response:
            current = json.load(response)
        def equivalent(a, b):
            return all(datetime.fromisoformat(a[key]) == datetime.fromisoformat(value)
                       if key == 'created_at' else a.get(key) == value for key, value in b.items())
        assert all(any(equivalent(item, original) for item in current) for original in before)
        checks['pre_recovery_games_preserved'] = len(before)
print('PASS: all pre-recovery games and current TLS files preserved', flush=True)

original_ldap = ldap_entries(EXTRACTED)
current_ldap = ldap_entries(LIVE)
assert set(original_ldap) <= set(current_ldap)
for dn, attributes in original_ldap.items():
    for field in ('userPassword', 'userPassword:'):
        if field in attributes:
            assert attributes[field] == current_ldap[dn].get(field)
checks['ldap_snapshot_readable'] = True
checks['ldap_original_dns_and_password_hashes_preserved'] = True
print('PASS: extracted LDAP readable; original DNs/password hashes preserved', flush=True)

pgdata = EXTRACTED / 'keycloak-db'
assert (pgdata / 'PG_VERSION').read_text().strip() == '16'
assert all((pgdata / part).is_dir() for part in ('base', 'global', 'pg_wal'))
control = docker('run', '--rm', '--network', 'none', '--mount',
    f'type=bind,source={pgdata},target=/check,readonly', '--entrypoint', 'pg_controldata',
    'postgres:16-alpine', '/check')
assert 'Database system identifier:' in control
checks['postgres_snapshot_control_readable'] = True
name = 'games-recovery-postgres-check'
try:
    docker('run', '-d', '--name', name, '--network', 'none', '--memory', '256m', '--mount',
        f'type=bind,source={pgdata},target=/var/lib/postgresql/data', 'postgres:16-alpine',
        'postgres', '-c', 'listen_addresses=', '-c', 'default_transaction_read_only=on')
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if subprocess.run(DOCKER + ['exec', name, 'pg_isready', '-U', 'keycloak', '-d', 'keycloak'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            break
        time.sleep(1)
    else:
        raise AssertionError('Extracted PostgreSQL did not become ready')
    old = sql(name)
    current = sql('ciber-p1-games-postgres-1')
    assert old['realm_id'] and old['client_id'] and old['ldap_id']
    assert all(old[key] == current[key] for key in ('realm_id', 'client_id', 'ldap_id'))
    assert current['user_count'] >= old['user_count']
    checks['postgres_snapshot_functionally_restorable'] = True
    checks['realm_client_ldap_ids_preserved'] = True
    checks['realm_users_before'] = old['user_count']
    checks['realm_users_current'] = current['user_count']
    print('PASS: isolated cold PostgreSQL 16 starts; realm, client and LDAP IDs preserved', flush=True)
finally:
    subprocess.run(DOCKER + ['stop', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(DOCKER + ['rm', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
(RECOVERY / 'verified.json').write_text(json.dumps(checks, indent=2))
output = ROOT / 'test-results/recovery.json'
output.write_text(json.dumps(checks, indent=2))
os.chown(output, int(os.environ.get('SUDO_UID', 0)), int(os.environ.get('SUDO_GID', 0)))
