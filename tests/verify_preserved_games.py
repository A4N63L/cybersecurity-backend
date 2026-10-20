"""Compare the cold pre-migration SQLite snapshot to the live catalog, no data writes."""
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys
import tarfile
import tempfile
import urllib.request

archive = Path(sys.argv[1]).resolve()
with tarfile.open(archive) as backup, tempfile.TemporaryDirectory() as temp:
    database = Path(temp) / 'games.db'
    database.write_bytes(backup.extractfile('.lab-data/games/games.db').read())
    with sqlite3.connect(f'file:{database}?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        old = [dict(row) for row in connection.execute('SELECT * FROM games')]
request = urllib.request.Request('http://localhost:8001/api/games', headers={'Authorization':'Bearer check.format.only'})
with urllib.request.urlopen(request) as response:
    current = json.load(response)
def equivalent(item, game):
    return all(datetime.fromisoformat(item[key]) == datetime.fromisoformat(value)
               if key == 'created_at' else item.get(key) == value for key, value in game.items())


assert all(any(equivalent(item, game) for item in current) for game in old)
print('PASS: all', len(old), 'pre-migration games preserved with identical IDs and fields')
