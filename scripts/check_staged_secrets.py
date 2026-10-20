"""Revisa el índice Git antes de publicar. No muestra valores privados.

python3 scripts/check_staged_secrets.py . --env .env
python3 scripts/check_staged_secrets.py ../videojuegos-frontend --env .env
"""
import argparse
import base64
import os
from pathlib import Path
import re
import shlex
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("repository", type=Path)
parser.add_argument("--env", type=Path, required=True)
args = parser.parse_args()
private = []
for line in args.env.read_text().splitlines():
    if line.strip() and not line.lstrip().startswith("#") and "=" in line:
        values = shlex.split(line.split("=", 1)[1], comments=True)
        if values:
            value = " ".join(values).encode()
            private.extend((value, base64.b64encode(value)))

def git(*parts):
    return subprocess.check_output(["git", "-C", str(args.repository), *parts])

paths = git("ls-files", "-z").decode().split("\0")
findings = []
for path in filter(None, paths):
    name = Path(path).name
    segments = Path(path).parts
    if (name.startswith(".env") and name != ".env.example") or any(p in segments for p in (".lab-data", "node_modules", "test-results", "__pycache__", ".venv")) or re.search(r"\.(db|sqlite3?|log|pem|key|har)$", path):
        findings.append((path, "archivo privado en el índice"))
    data = git("show", f":{path}")
    if any(value and value in data for value in private):
        findings.append((path, "credencial local o su Base64"))
    if re.search(rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)", data):
        findings.append((path, "patrón de token o clave privada"))
if findings:
    for path, reason in findings:
        print(f"REVISAR: {path}: {reason}")
    raise SystemExit(1)
print(f"OK: {sum(bool(p) for p in paths)} archivos del índice revisados; sin credenciales locales, JWT reales, claves privadas ni rutas sensibles detectadas.")
