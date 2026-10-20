"""Comprueba la configuración distribuible sin modificar datos del laboratorio."""
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("setup_env", ROOT / "scripts/setup_env.py")
setup_env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup_env)


class PublicationConfigTests(unittest.TestCase):
    def test_credentials_are_unique_private_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            self.assertTrue(setup_env.create_env(path))
            original = path.read_bytes()
            entries = dict(line.split("=", 1) for line in original.decode().splitlines() if line and not line.startswith("#"))
            self.assertEqual(set(entries), set(setup_env.KEYS))
            self.assertEqual(len(set(entries.values())), len(setup_env.KEYS))
            self.assertTrue(all(len(value) == 48 for value in entries.values()))
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertFalse(setup_env.create_env(path))
            self.assertEqual(original, path.read_bytes())

    def test_example_has_no_credentials(self):
        entries = dict(line.split("=", 1) for line in (ROOT / ".env.example").read_text().splitlines() if line and not line.startswith("#"))
        self.assertEqual(set(entries), set(setup_env.KEYS))
        self.assertTrue(all(value == "" for value in entries.values()))

    def test_templates_reference_private_environment(self):
        auth = ROOT.parent / "videojuegos-auth"
        self.assertIn('"${LDAP_ADMIN_PASSWORD}"', (auth / "keycloak/import/games-lab-realm.json").read_text())
        template = (auth / "ldap/users.ldif.template").read_text()
        self.assertIn("userPassword:: @ALICE_PASSWORD_BASE64@", template)
        self.assertIn("userPassword:: @BOB_PASSWORD_BASE64@", template)


if __name__ == "__main__":
    unittest.main()
