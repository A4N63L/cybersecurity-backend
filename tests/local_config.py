"""Configuración privada para pruebas de integración, sin dependencias extra."""
import os
from pathlib import Path
import shlex


def load_local_credentials():
    path = Path(__file__).resolve().parents[1] / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            # No ejecutar ni expandir el contenido del archivo .env.
            values = shlex.split(value, comments=True)
            os.environ.setdefault(key.strip(), " ".join(values))
    for key in ("ALICE_PASSWORD", "BOB_PASSWORD"):
        if not os.environ.get(key):
            raise RuntimeError(f"Configura {key} en .env o en el entorno")
