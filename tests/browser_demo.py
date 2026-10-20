"""Integración REAL contra servicios activos. No guarda JWT ni contraseñas en artefactos.

Ejecutar desde el host con Python + playwright; crea un juego de prueba.
"""
import base64
import json
import os
from pathlib import Path
import time
from urllib.parse import parse_qs, urlparse
from playwright.sync_api import sync_playwright, expect
from local_config import load_local_credentials

load_local_credentials()

OUTPUT = Path(__file__).resolve().parents[1] / "test-results"
OUTPUT.mkdir(exist_ok=True)
results = []


def passed(name):
    results.append(name)
    print("PASS:", name, flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(viewport={"width":1440,"height":1000})
    page = context.new_page()
    errors, token_logs, requests, token_grants = [], [], [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # Solo clasifica los mensajes; nunca conserva el valor del token.
    page.on("console", lambda msg: token_logs.append(msg.text.split(' JWT')[0]) if '[DEMO LOCAL]' in msg.text else None)

    def track(request):
        if '/protocol/openid-connect/token' in request.url:
            token_grants.append(parse_qs(request.post_data or '').get('grant_type', [''])[0])
        if request.url == 'http://localhost:8001/api/games':
            requests.append((request.method, request.headers.get('authorization', '')))
    page.on('request', track)
    page.goto('http://localhost:4200/dashboard')
    expect(page).to_have_url('http://localhost:4200/login', timeout=60000)
    expect(page.get_by_role('button', name='Entrar con Keycloak')).to_be_visible()
    passed('Guard bloquea dashboard sin sesión y muestra login Angular')
    page.screenshot(path=str(OUTPUT/'login-desktop.png'), full_page=True)
    page.get_by_role('button', name='Entrar con Keycloak').click()
    page.wait_for_url('**/protocol/openid-connect/auth**',timeout=30000)
    params = parse_qs(urlparse(page.url).query)
    assert params['code_challenge_method'] == ['S256'] and params['code_challenge'][0]
    assert params['client_id'] == ['games-spa'] and params['response_type'] == ['code']
    assert params['redirect_uri'] == ['http://localhost:4200/auth/callback']
    passed('Solicitud Authorization Code con PKCE S256 y callback exacto')
    page.locator('#username').fill('alice')
    page.locator('#password').fill(os.environ['ALICE_PASSWORD'])
    page.locator('#kc-login').click()
    expect(page).to_have_url('http://localhost:4200/dashboard', timeout=60000)
    expect(page.locator('.game-card').first).to_be_visible(timeout=30000)
    assert 'authorization_code' in token_grants and 'password' not in token_grants
    assert token_logs, 'Falta JWT de inicio de sesión en consola local'
    passed('Login LDAP alice vía Keycloak; intercambio de código y JWT en consola local')
    get_token = next(token for method,token in requests if method == 'GET')
    assert get_token.startswith('Bearer ')
    token = get_token.removeprefix('Bearer ')
    claims = json.loads(base64.urlsafe_b64decode(token.split('.')[1] + '=='))
    assert claims['iss'] == 'http://localhost:8082/realms/games-lab'
    assert claims['preferred_username'] == 'alice'
    passed('HttpInterceptor adjunta access token de Keycloak al GET real')
    page.screenshot(path=str(OUTPUT/'dashboard-desktop.png'), full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(OUTPUT/'dashboard-mobile.png'), full_page=True)
    passed('Dashboard responsive 390px sin desbordamiento horizontal')
    page.set_viewport_size({'width':1440,'height':1000})
    page.get_by_role('link', name='＋ Agregar videojuego').click()
    expect(page).to_have_url('http://localhost:4200/games/new')
    page.get_by_role('button', name='Guardar videojuego').click()
    expect(page.get_by_role('alert')).to_be_visible()
    passed('Página de alta independiente y validación de formulario vacío')
    title = 'Playwright · Recuperación ' + str(int(time.time()))
    page.locator('#title').fill(title)
    page.locator('#genre').fill('Aventura')
    page.locator('#platform').fill('PC')
    page.locator('#release_year').fill('2026')
    page.screenshot(path=str(OUTPUT/'add-game-desktop.png'), full_page=True)
    with page.expect_response(lambda r: r.url == 'http://localhost:8001/api/games' and r.request.method == 'POST') as created:
        page.get_by_role('button', name='Guardar videojuego').click()
    assert created.value.status == 201
    game = created.value.json()
    expect(page).to_have_url('http://localhost:4200/dashboard')
    expect(page.get_by_role('heading',name=title,exact=True)).to_be_visible()
    assert any(method == 'POST' and value.startswith('Bearer ') for method,value in requests)
    assert len(token_logs) >= 2
    passed('Alta real desde Angular: POST 201, Bearer automático, JWT en consola y listado actualizado')
    page.reload()
    expect(page.get_by_role('heading',name=title,exact=True)).to_be_visible(timeout=60000)
    passed('Recarga completa conserva sesión SSO y videojuego')
    page.get_by_role('textbox',name='Buscar videojuegos').fill(title)
    expect(page.locator('.game-card')).to_have_count(1)
    passed('Búsqueda filtra el listado')
    page.get_by_role('button',name='Salir',exact=True).click()
    expect(page).to_have_url('http://localhost:4200/login', timeout=30000)
    page.goto('http://localhost:4200/games/new')
    expect(page).to_have_url('http://localhost:4200/login',timeout=60000)
    passed('Logout OIDC y guard de página de alta')
    assert not errors, errors
    passed('Sin errores JavaScript no controlados en Chromium')
    # Segundo usuario: prueba federación sin usar Password Grant.
    page.get_by_role('button', name='Entrar con Keycloak').click()
    page.locator('#username').fill('bob')
    page.locator('#password').fill(os.environ['BOB_PASSWORD'])
    page.locator('#kc-login').click()
    expect(page).to_have_url('http://localhost:4200/dashboard',timeout=60000)
    expect(page.locator('.user')).to_contain_text('bob')
    passed('Login LDAP bob mediante el mismo flujo PKCE')
    browser.close()
    report = {'passed':results,'game':game,'javascript_errors':errors,'token_values_saved':False}
    (OUTPUT/'browser.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
print(f'{len(results)} comprobaciones de navegador correctas. Artefactos: {OUTPUT}')
