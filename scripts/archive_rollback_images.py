"""Make the initial rollback independent of the ephemeral Docker image store."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

root = Path(__file__).resolve().parents[1]
directory = Path(sys.argv[1]).resolve()
assert directory.is_dir() and (directory / 'lab-before-tls.tar').is_file()
host = subprocess.check_output(['bash', str(root / 'lab.sh'), 'docker-host'], text=True).strip()
target = directory / 'rollback-images.tar.gz'
assert not target.exists(), 'Refusing to overwrite rollback images'
os.umask(0o077)
images = ['ciber-p1-games-frontend:pre-fail2ban', 'ciber-p1-games-backend:pre-fail2ban',
          'quay.io/keycloak/keycloak:26.7.4', 'osixia/openldap:1.5.0', 'postgres:16-alpine']
process = subprocess.Popen(['docker', '--host', host, 'image', 'save', *images], stdout=subprocess.PIPE)
with gzip.open(target, 'wb', compresslevel=1) as output:
    while block := process.stdout.read(1024 * 1024):
        output.write(block)
assert process.wait() == 0, 'Docker image save failed'
with tarfile.open(target) as archive:
    manifest = json.load(archive.extractfile('manifest.json'))
assert len(manifest) == 5
with target.open('rb') as file:
    digest = hashlib.file_digest(file, 'sha256').hexdigest()
(directory / 'rollback-images.sha256').write_text(digest + '  rollback-images.tar.gz\n')
(directory / 'rollback-images.yaml').write_text('services:\n  frontend:\n'
    '    image: ciber-p1-games-frontend:pre-fail2ban\n  backend:\n'
    '    image: ciber-p1-games-backend:pre-fail2ban\n')
print('Verified five rollback images in private archive:', target)
