"""Mount a persistent ext4 Docker store on the persistent Mint Live filesystem.

Only socket/exec state lives in /tmp. The sparse image stays beside the projects.
Existing stores are never reformatted. Must run as root (mount/loop permissions).
"""
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
directory = ROOT.parent / '.lab-docker'
image = directory / 'games-docker.ext4'
mountpoint = Path('/tmp/opencode/games-docker-store')
assert os.geteuid() == 0
directory.mkdir(mode=0o700, exist_ok=True)
mountpoint.mkdir(parents=True, exist_ok=True)
if subprocess.run(['mountpoint', '-q', str(mountpoint)]).returncode == 0:
    assert image.exists(), 'Mounted store without persistent backing image'
    device = subprocess.check_output(['findmnt', '-n', '-o', 'SOURCE', '--target', str(mountpoint)], text=True).strip()
    backing = subprocess.check_output(['losetup', '-n', '-O', 'BACK-FILE', device], text=True).strip()
    assert Path(backing).resolve() == image.resolve(), 'Different loop image mounted at Docker store'
else:
    if not image.exists():
        assert shutil.disk_usage(directory).free > 4 * 1024**3, 'Need 4 GiB free before first store creation'
        with image.open('xb') as file:
            file.truncate(4 * 1024**3)
        image.chmod(0o600)
        subprocess.run(['mkfs.ext4', '-q', '-F', str(image)], check=True)
    kind = subprocess.check_output(['blkid', '-p', '-s', 'TYPE', '-o', 'value', str(image)], text=True).strip()
    assert kind == 'ext4', 'Refusing to format/reuse unknown existing store'
    subprocess.run(['mount', '-o', 'loop,noatime', str(image), str(mountpoint)], check=True)
print(str(mountpoint / 'data'))
