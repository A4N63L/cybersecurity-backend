"""Genera credenciales únicas para un laboratorio NUEVO; nunca sobrescribe .env."""
from pathlib import Path
import os
import secrets

KEYS = ("POSTGRES_PASSWORD", "KEYCLOAK_ADMIN_PASSWORD", "LDAP_ADMIN_PASSWORD", "ALICE_PASSWORD", "BOB_PASSWORD")


def create_env(path: Path) -> bool:
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w") as target:
        target.write("# Credenciales privadas de esta instalación local. No publicar.\n")
        for key in KEYS:
            target.write(f"{key}={secrets.token_hex(24)}\n")
    return True


if __name__ == "__main__":
    path = Path(__file__).resolve().parents[1] / ".env"
    created = create_env(path)
    print(".env privado creado con credenciales aleatorias." if created else ".env ya existe; se conserva sin cambios.")
