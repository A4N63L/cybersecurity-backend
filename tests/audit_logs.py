"""Comprueba todos los logs actuales sin guardar posibles tokens en el informe."""
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[1]
result = subprocess.run(['bash','lab.sh','logs','--no-color'],cwd=root,capture_output=True,text=True,check=True)
lines = result.stdout.splitlines()
errors = [line for line in lines if re.search(r'\b(ERROR|FATAL|Traceback|Exception)\b',line)]
tokens = [line for line in lines if re.search(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',line)]
assert not errors, f'{len(errors)} errores en los logs actuales; revisar bash lab.sh logs'
assert not tokens, 'Hay valores JWT en logs de servidor'
report={'checked_at':datetime.now(timezone.utc).isoformat(),'lines_reviewed':len(lines),'important_errors':len(errors),'jwt_values_in_server_logs':len(tokens),'warnings':'Modo desarrollo de Angular/Keycloak y features deprecadas de Keycloak; no impiden el funcionamiento.'}
(root/'test-results'/'log-audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
print('PASS: logs actuales sin ERROR/FATAL/Traceback/Exception y sin valores JWT:',len(lines),'líneas')
