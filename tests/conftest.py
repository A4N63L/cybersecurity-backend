import os
import tempfile

# Estas pruebas nunca utilizan el volumen de datos de la demostración.
_database = tempfile.TemporaryDirectory(prefix="games-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_database.name}/test.db"
