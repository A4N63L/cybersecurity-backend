"""Privileged, staged recovery. Snapshot first, extract separately; never merge PGDATA.

Run with sudo -n python3 scripts/recover_data.py prepare|restore-postgres <directory>.
Reports contain metadata/counts only; no credentials, certificate keys or user rows.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent
ORIGINAL = BASE / '.lab-backups/20261019-194554/lab-before-tls.tar'
os.umask(0o077)


def inventory(path):
    result = {'exists': path.exists()}
    if not path.exists():
        return result
    files = [p for p in path.rglob('*') if p.is_file()]
    result.update(files=len(files), bytes=sum(p.stat().st_size for p in files),
                  uid=path.stat().st_uid, gid=path.stat().st_gid,
                  mode=oct(path.stat().st_mode & 0o777))
    if (path / 'PG_VERSION').is_file():
        result['pg_version'] = (path / 'PG_VERSION').read_text().strip()
        result['pg_structure'] = all((path / p).is_dir() for p in ('base', 'global', 'pg_wal'))
    if (path / 'games.db').is_file():
        with sqlite3.connect(f'file:{path / "games.db"}?mode=ro', uri=True) as db:
            result['sqlite_integrity'] = db.execute('PRAGMA integrity_check').fetchone()[0]
            result['games'] = db.execute('SELECT count(*) FROM games').fetchone()[0]
    return result


def manifest(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*') if p.is_file()}


def prepare():
    target = BASE / '.lab-backups' / ('recovery-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    target.mkdir(mode=0o700)
    archive = target / 'current-state.tar'
    subprocess.run(['tar', '--numeric-owner', '-cpf', str(archive), '-C', str(ROOT),
                    '.lab-data', '.env', 'compose.yaml', 'compose.live.yaml', 'lab.sh'], check=True)
    with tarfile.open(archive) as saved:
        assert any(m.name == '.lab-data/tls/ca.key' for m in saved.getmembers())
    extracted = target / 'original-extracted'
    extracted.mkdir(mode=0o700)
    # Validate names before asking tar to preserve owners/modes.
    with tarfile.open(ORIGINAL) as saved:
        for member in saved:
            assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            assert not member.issym() and not member.islnk(), 'Unexpected archive link'
    subprocess.run(['tar', '--numeric-owner', '-xpf', str(ORIGINAL), '-C', str(extracted)], check=True)
    data = ROOT / '.lab-data'
    old = extracted / '.lab-data'
    report = {'original_archive': str(ORIGINAL), 'current_snapshot': str(archive),
              'recovered_separately': str(extracted), 'current': {}, 'original': {}, 'identical': {}}
    for name in ('ldap-data', 'ldap-config', 'games', 'keycloak-db', 'tls'):
        report['current'][name] = inventory(data / name)
        report['original'][name] = inventory(old / name)
        if (data / name).exists() and (old / name).exists():
            report['identical'][name] = manifest(data / name) == manifest(old / name)
    (target / 'inventory.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'recovery_directory': str(target), **report}, indent=2))


def restore_pg(target):
    target = target.resolve()
    assert target.parent == BASE / '.lab-backups'
    source = target / 'original-extracted/.lab-data/keycloak-db'
    dest = ROOT / '.lab-data/keycloak-db'
    assert inventory(source).get('pg_version') == '16'
    assert inventory(source)['pg_structure']
    current = inventory(dest)
    assert not dest.exists() or current.get('files', 0) == 0, 'Existing PGDATA: compare/recover it instead of replacing'
    if dest.exists():
        dest.rename(target / 'previous-keycloak-db')
    # Copy the entire cold cluster, ownership and permissions intact. No mixing.
    subprocess.run(['cp', '-a', str(source), str(dest)], check=True)
    assert manifest(source) == manifest(dest)
    (target / 'restored-postgres.json').write_text(json.dumps({'source': str(source), 'destination': str(dest),
        'complete_copy_verified': True, **inventory(dest)}, indent=2))
    print('Complete PostgreSQL 16 cluster restored and byte-verified; LDAP, SQLite and TLS untouched.')


if __name__ == '__main__':
    assert os.geteuid() == 0, 'Use sudo to avoid hidden permission errors'
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'restore-postgres':
        restore_pg(Path(sys.argv[2]))
    else:
        raise SystemExit('Unknown recovery operation')
