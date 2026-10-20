"""Cold, recoverable snapshot before LDAP/realm migrations. Never prints secrets."""
import datetime
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DOCKER = ['docker', '--host', subprocess.check_output(['bash', str(ROOT / 'lab.sh'), 'docker-host'], text=True).strip()]


def main():
    parent = ROOT.parent / '.lab-backups'
    parent.mkdir(mode=0o700, exist_ok=True)
    target = parent / datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    target.mkdir(mode=0o700)
    names = ['ciber-p1-games-' + name + '-1' for name in
             ('frontend', 'backend', 'keycloak', 'openldap', 'postgres')]
    running = json.loads(subprocess.check_output(DOCKER + ['inspect', *names]))
    assert all(c['State']['Running'] for c in running), 'Expected running lab'
    image_tags = {}
    for service in ('frontend', 'backend', 'keycloak', 'openldap'):
        tag = f'ciber-p1-games-{service}:snapshot-{target.name}'
        image_tags[service] = tag
        subprocess.run(DOCKER + ['tag', f'ciber-p1-games-{service}:dev',
                       tag], check=True)
    subprocess.run(DOCKER + ['stop', *names], check=True, stdout=subprocess.DEVNULL)
    try:
        archive = target / 'lab-snapshot.tar'
        subprocess.run(['sudo', '-n', 'tar', '--numeric-owner', '-cpf', str(archive),
                        '-C', str(ROOT), '.lab-data', '.env', 'compose.yaml',
                        'compose.live.yaml', 'lab.sh', 'infra'], check=True)
        subprocess.run(['sudo', '-n', 'chown', f'{os.getuid()}:{os.getgid()}', str(archive)], check=True)
        archive.chmod(0o600)
        members = subprocess.check_output(['tar', '-tf', str(archive)], text=True)
        assert all(x in members for x in ('.lab-data/ldap-data/', '.lab-data/ldap-config/',
                                          '.lab-data/keycloak-db/', '.lab-data/games/', '.env'))
        (target / 'manifest.json').write_text(json.dumps({
            'daemon': DOCKER[-1], 'services': {c['Name']: c['Image'] for c in running},
            'archive': archive.name, 'image_tags': image_tags, 'cold_snapshot': True}, indent=2))
        print('Snapshot verified:', target)
    finally:
        subprocess.run(DOCKER + ['start', *reversed(names)], check=True, stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    main()
