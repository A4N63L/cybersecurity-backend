"""Comprueba todos los logs actuales sin guardar posibles tokens en el informe."""
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone
from local_config import load_local_credentials

load_local_credentials()

root = Path(__file__).resolve().parents[1]
result = subprocess.run(['bash','lab.sh','logs','--no-color'],cwd=root,capture_output=True,text=True,check=True)
lines = result.stdout.splitlines()
# Access logs are regular files, deliberately separate from Docker stdout.
for service, path in [('frontend', '/var/log/security/access.log'),
                      ('backend', '/var/log/security/access.log'),
                      ('keycloak', '/opt/keycloak/data/log/keycloak-http-access.log'),
                      ('openldap', '/var/log/security/access.log')]:
    content = subprocess.check_output(['bash', 'lab.sh', 'exec', '-T', service, 'python3', '-c',
        'from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text())', path], cwd=root, text=True)
    assert '?' not in content, f'Query string in {service} access log'
    assert not re.search(r'Authorization|Cookie|header-canary|cookie-canary', content, re.I), f'Header in {service} access log'
    lines.extend(content.splitlines())
shutdowns = [line for line in lines if re.search(r'^postgres-\d+\s+\| .*FATAL:  terminating connection due to administrator command$', line)]
errors = [line for line in lines if re.search(r'\b(ERROR|FATAL|Traceback|Exception)\b',line) and line not in shutdowns]
tokens = [line for line in lines if re.search(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',line)]
assert not any(value in '\n'.join(lines) for key, value in os.environ.items()
               if ('PASSWORD' in key or 'SECRET' in key) and len(value) >= 8), 'Private credential found in logs (value omitted)'
for line in errors:
    for key, value in os.environ.items():
        if ('PASSWORD' in key or 'SECRET' in key) and value:
            line = line.replace(value, '[REDACTED]')
    line = re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[JWT REDACTED]', line)
    line = re.sub(r'\?[^\s\"]+', '?[QUERY REDACTED]', line)
    print(line)
assert not errors, f'{len(errors)} errores en los logs actuales; revisar bash lab.sh logs'
assert not tokens, 'Hay valores JWT en logs de servidor'
report={'checked_at':datetime.now(timezone.utc).isoformat(),'lines_reviewed':len(lines),'important_errors':len(errors),'expected_postgres_shutdowns':len(shutdowns),'jwt_values_in_server_logs':len(tokens),'queries_or_headers_in_access_logs':False,'warnings':'Keycloak sigue en start-dev para este laboratorio local.'}
(root/'test-results'/'log-audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
print('PASS: logs actuales sin ERROR/FATAL/Traceback/Exception y sin valores JWT:',len(lines),'líneas')
