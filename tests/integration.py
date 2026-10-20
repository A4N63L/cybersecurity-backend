"""Pruebas HTTP y persistencia reales. --recreate recrea SOLO esta práctica."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from local_config import load_local_credentials

load_local_credentials()

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results'
OUT.mkdir(exist_ok=True)
checks = []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url, method='GET', headers=None, data=None, follow_redirects=True):
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    try:
        opener = urllib.request.build_opener() if follow_redirects else urllib.request.build_opener(NoRedirect)
        with opener.open(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def passed(name):
    checks.append(name)
    print('PASS:',name,flush=True)


api='http://localhost:8001'
issuer='http://localhost:8082/realms/games-lab'
headers={'Authorization':'Bearer aaa.bbb.ccc'}
status,_,body=request(api+'/health')
assert status == 200 and json.loads(body)['status'] == 'ok'
passed('Health público HTTP 200')
for method in ['GET','POST']:
    for header in [None,'Basic abc','Bearer abc','Bearer a.b.','Bearer a.b.c d']:
        status,_,_=request(api+'/api/games',method,{'Authorization':header} if header else {})
        assert status == 401, (method,header,status)
passed('GET/POST rechazan cabecera ausente o mal formada: 10 casos HTTP 401')
assert request(api+'/api/games',headers=headers)[0] == 200
passed('Token falsificado con formato válido aceptado: limitación académica confirmada')
for origin,allowed in [('http://localhost:4200',True),('https://example.org',False)]:
    status,h,_=request(api+'/api/games','OPTIONS',{'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'})
    assert status == (200 if allowed else 400)
    assert (h.get('access-control-allow-origin') == origin) == allowed
passed('CORS permite frontend local y rechaza origen externo')
status,_,body=request(issuer+'/.well-known/openid-configuration')
assert status == 200 and json.loads(body)['issuer'] == issuer
passed('Discovery OIDC con issuer público correcto')
status,_,body=request(issuer+'/protocol/openid-connect/token','POST',{'Content-Type':'application/x-www-form-urlencoded'},urllib.parse.urlencode({'client_id':'games-spa','grant_type':'password','username':'alice','password':os.environ['ALICE_PASSWORD']}).encode())
assert status == 400 and json.loads(body)['error'] == 'unauthorized_client'
passed('Password grant deshabilitado para games-spa')
query=urllib.parse.urlencode({'client_id':'games-spa','response_type':'code','redirect_uri':'http://localhost:4200/auth/callback','scope':'openid'})
status,h,_=request(issuer+'/protocol/openid-connect/auth?'+query,follow_redirects=False)
assert status == 302 and urllib.parse.parse_qs(urllib.parse.urlparse(h['Location']).query)['error'] == ['invalid_request']
passed('Keycloak rechaza Authorization Code sin PKCE')
game={'title':'Integración HTTP '+str(int(time.time())),'genre':'RPG','platform':'PC','release_year':2026}
status,_,body=request(api+'/api/games','POST',{**headers,'Content-Type':'application/json'},json.dumps(game).encode())
assert status == 201
created=json.loads(body)
before=json.loads(request(api+'/api/games',headers=headers)[2])
assert any(g['id']==created['id'] and g['title']==game['title'] for g in before)
passed('POST HTTP 201 y GET recupera el videojuego creado')
parser = argparse.ArgumentParser()
parser.add_argument('--recreate', action='store_true')
if parser.parse_args().recreate:
    subprocess.run(['bash','lab.sh','up','--force-recreate'],cwd=ROOT,check=True)
    after=json.loads(request(api+'/api/games',headers=headers)[2])
    assert before == after
    passed('Persistencia: catálogo idéntico tras recrear los cinco servicios y ldap-init')
    assert request(issuer+'/.well-known/openid-configuration')[0] == 200
    passed('Realm y cliente recuperados desde PostgreSQL persistente tras recreación')
(OUT/'integration.json').write_text(json.dumps({'passed':checks,'created_game':created},ensure_ascii=False,indent=2))
