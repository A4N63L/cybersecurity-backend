# GameVault · Backend y laboratorio de Ciberseguridad

Sistema académico nuevo: Angular + FastAPI + SQLite + Keycloak + OpenLDAP.
El frontend es una carpeta independiente, hermana de este proyecto.
Infraestructura única del laboratorio: `compose.yaml`, `compose.live.yaml` e
`infra/` viven **en este repositorio backend**. No se requiere un tercer repositorio.

## Inicio rápido

Clona ambos repositorios como carpetas hermanas, conservando los nombres locales
que espera el contexto de construcción de Compose:

```bash
git clone https://github.com/A4N63L/cybersecurity-dashboard.git videojuegos-frontend
git clone https://github.com/A4N63L/cybersecurity-backend.git videojuegos-backend
cd videojuegos-backend
python3 scripts/setup_env.py
```

El generador crea `.env` privado con cinco contraseñas aleatorias y permisos 600.
Nunca sobrescribe un `.env` existente. Consulta ese archivo **solo localmente**
para conocer las credenciales de tu instalación. No lo publiques ni lo compartas.

Desde `videojuegos-backend`:

```bash
bash lab.sh up
bash lab.sh ps -a
```

Se necesitan Python 3 (para generar `.env`), Docker, Docker Compose, Bash e Internet para la primera
descarga. No hace falta instalar Node.js ni las dependencias Python en el host.
El frontend debe estar en `../videojuegos-frontend`.

El comando construye ambas imágenes, inicia los servicios, carga LDAP de manera
idempotente y espera a los healthchecks. `ldap-init` debe terminar con código 0;
los otros cinco servicios deben aparecer como `healthy`.

Compose exige las variables de `.env`, sin contraseñas predeterminadas. Como
alternativa al generador, copia `.env.example` a `.env` y completa sus cinco valores
con contraseñas propias **antes de la primera inicialización**. Cambiar estas
variables después no cambia automáticamente contraseñas almacenadas en las BD.
En una instalación existente, conserva su `.env` y sus datos: el generador no
rota credenciales ni modifica contenedores o bases de datos.

### Particularidad de esta computadora: Linux Mint Live

El Docker del sistema usa `vfs` sobre el almacenamiento Live. Las extracciones
de capas agotaban los tiempos de espera. `lab.sh` detecta esa configuración y
utiliza un daemon propio con `overlay2`:

```text
Socket:          /tmp/opencode/games-docker.sock
Imágenes/caché:  /tmp/opencode/games-docker-data
Datos duraderos: videojuegos-backend/.lab-data/
```

Puede pedir `sudo` para iniciar exclusivamente ese daemon. No reinicia el daemon
original, no usa sus contenedores ni sus volúmenes y no modifica su configuración.
El daemon usa namespace containerd `gameslab`, bridge predeterminado deshabilitado
e iptables deshabilitado. Compose crea su propia red. Las construcciones usan
la red del host para descargar dependencias; los servicios usan la red del lab.

**Después de reiniciar la computadora**, ejecuta otra vez `bash lab.sh up`.
Las imágenes de `/tmp` se descargarán/reconstruirán si han desaparecido; las bases
de datos y LDAP se recuperan de `.lab-data`. No borres esa carpeta.

`docker ps` sin parámetros muestra el Docker original. Para ver esta práctica,
usa `bash lab.sh ps -a`. También puedes consultar directamente:

```bash
docker -H unix:///tmp/opencode/games-docker.sock ps -a
```

En una instalación Docker normal con overlay2, `lab.sh` usa el daemon habitual y
los volúmenes nuevos de Compose. La misma configuración base puede levantarse
con `docker compose up -d --build --wait`. El arranque y la recuperación se han
verificado en esta máquina mediante `lab.sh` y `compose.live.yaml`.

Variables opcionales del lanzador:

- `GAMES_ISOLATED_DOCKER=1`: fuerza el daemon propio.
- `GAMES_ISOLATED_DOCKER=0`: usa el Docker seleccionado por el entorno.

Mantén la misma selección al parar, consultar y arrancar para no mezclar estados.

## URLs y cuentas locales

| Servicio | URL |
|---|---|
| Frontend | http://localhost:4200 |
| Backend health | http://localhost:8001/health |
| Swagger | http://localhost:8001/docs |
| Keycloak administración | http://localhost:8082/admin/ |
| Discovery OIDC | http://localhost:8082/realms/games-lab/.well-known/openid-configuration |

Usa **localhost**, no `127.0.0.1`, para navegar. Redirect URIs, issuer y CORS
están configurados para esos orígenes exactos.

| Cuenta local de demostración | Contraseña | Uso |
|---|---|---|
| `alice` | Valor privado `ALICE_PASSWORD` de `.env` | Login de aplicación, usuario LDAP |
| `bob` | Valor privado `BOB_PASSWORD` de `.env` | Login de aplicación, usuario LDAP |
| `admin` | Valor privado `KEYCLOAK_ADMIN_PASSWORD` de `.env` | Administración Keycloak, realm master |

LDAP usa `cn=admin,dc=example,dc=com` con `LDAP_ADMIN_PASSWORD` para el bind del
proveedor y la inicialización. PostgreSQL usa `keycloak` con `POSTGRES_PASSWORD`.
Estas cuentas pertenecen únicamente a esta práctica local.
LDAP y PostgreSQL no publican puertos en el host. Los tres servicios web están
publicados exclusivamente sobre `127.0.0.1`.

## Demostración funcional

1. Ejecuta `bash lab.sh up` y confirma los estados con `bash lab.sh ps -a`.
2. Abre http://localhost:4200 y las herramientas de desarrollo del navegador.
3. En la pestaña Console, activa **Preserve log** si quieres conservar mensajes
   a través de redirecciones. Pulsa **Entrar con Keycloak**.
4. En la página de Keycloak, introduce `alice` y el valor `ALICE_PASSWORD` de tu `.env`.
5. El dashboard muestra la biblioteca. La consola muestra
   `[DEMO LOCAL] JWT · inicio de sesión` y el access token.
6. Abre **Agregar videojuego**, completa título, género, plataforma y año, y guarda.
7. La consola muestra `[DEMO LOCAL] JWT · agregar videojuego`; Network muestra
   `POST /api/games`, respuesta 201 y el encabezado `Authorization: Bearer …`.
8. Vuelve al listado, busca el título y recarga la página: el juego permanece.
9. Pulsa **Salir**. Abrir `/dashboard` o `/games/new` sin sesión conduce a `/login`.

La consola imprime tokens exclusivamente en la compilación de demostración,
en un hostname loopback y con `demoTokenLogging=true`. En producción, Angular
sustituye el módulo logger por una función vacía: ni el mensaje ni el logger
de demostración se incluyen en el bundle. Los logs del servidor no imprimen JWT.

## Arquitectura

```text
Navegador Angular ── Authorization Code + PKCE S256 ──► Keycloak
       │                                                 │
       │                                                 ├──► OpenLDAP (usuarios/credenciales)
       │                                                 └──► PostgreSQL (realm/configuración/sesiones)
       │
       └── HttpClient + HttpInterceptor + Bearer ──► FastAPI
                                                      │
                                         rutas → servicios → repositorios
                                                      │
                                                   SQLite
```

Angular introduce las credenciales únicamente en Keycloak. OpenLDAP proporciona
el directorio y verifica la contraseña; **Keycloak emite el JWT**. El backend de
videojuegos no consulta LDAP ni las claves de Keycloak.

### Backend en capas

- `app/api/routes`: endpoints HTTP y dependencias de acceso.
- `app/core/security.py`: comprobación del formato Bearer.
- `app/schemas`: validación Pydantic de entrada/salida.
- `app/services`: casos de uso de videojuegos.
- `app/models`: modelo SQLAlchemy.
- `app/persistence`: sesiones SQLite y repositorios.
- `app/main.py`: aplicación, CORS, creación de tablas y tres juegos semilla
  únicamente cuando la tabla está vacía.

| Método | Endpoint | Resultado |
|---|---|---|
| GET | `/health` | 200 público |
| GET | `/api/games` | 200, lista protegida por formato Bearer |
| POST | `/api/games` | 201, registro de videojuego |

Ejemplo de cuerpo POST:

```json
{"title":"Hollow Knight","genre":"Metroidvania","platform":"PC","release_year":2017}
```

Se recortan espacios, se rechazan campos vacíos y se limita el año a 1950–2100.
SQLite está en `/data/games.db` dentro del servicio. En modo Live corresponde
a `.lab-data/games/games.db`. El listado devuelve hasta 200 juegos.

### Limitación académica obligatoria

El backend exige `Authorization: Bearer <token>` y tres segmentos no vacíos
Base64URL separados por puntos. Rechaza tokens vacíos, espacios internos y esquemas
incorrectos con 401. El esquema Bearer no distingue mayúsculas/minúsculas.

**No verifica firma, exp, nbf, issuer, audience ni permisos. Esta comprobación no
protege realmente contra tokens falsificados.** `aaa.bbb.ccc` es aceptado
deliberadamente, como demuestra la prueba de integración. Los guards de Angular
tampoco sustituyen una autorización real del backend.

CORS limita el navegador a `http://localhost:4200`, métodos GET/POST y cabeceras
Authorization/Content-Type. El middleware atiende OPTIONS sin requerir token.

### Configuración de identidad

```text
Realm: games-lab
Cliente: games-spa, público (sin client_secret)
Flujo: Authorization Code; PKCE S256 obligatorio
Password Grant / Implicit / Service Accounts: deshabilitados
Redirect URI: http://localhost:4200/auth/callback
Web Origin: http://localhost:4200
Post logout: http://localhost:4200/login
LDAP: ldap://openldap:389
Base usuarios: ou=users,dc=example,dc=com
Modo: READ_ONLY, username LDAP: uid
```

El import incluye mapeos uid, givenName, sn y mail. Keycloak resuelve
`${LDAP_ADMIN_PASSWORD}` desde su entorno al importar el realm; no hay contraseña
en el JSON versionado. `infra/ldap/users.ldif.template` recibe las contraseñas de
los usuarios en Base64 LDIF mediante stdin, sin guardar un LDIF renderizado con
credenciales. El script verifica los binds y no rota contraseñas existentes.

La configuración se importa
en la primera inicialización. Keycloak omite un realm que ya existe: modificar
el JSON no modifica automáticamente el realm persistido. Usa la consola de
administración para cambios posteriores; no hace falta borrar volúmenes.

## Comandos de operación

```bash
bash lab.sh ps -a
bash lab.sh logs --tail 100 backend frontend keycloak
bash lab.sh stop                  # Quita contenedores/red, conserva los datos
bash lab.sh up                    # Reconstruye si es necesario y arranca
bash lab.sh up --force-recreate   # Recrea contenedores conservando los datos
```

No uses `down -v` ni borres `.lab-data` si quieres conservar la práctica.

## Pruebas reproducibles

### Backend aislado de los datos reales

```bash
bash lab.sh exec -T backend python -m pytest -q tests/test_backend.py
```

26 pruebas; utilizan SQLite temporal, no el volumen de demostración.
Incluyen GET/POST sin Bearer, formatos incorrectos, token ficticio, validación
de entrada y preflight CORS. Puede aparecer una advertencia de deprecación del
TestClient de Starlette/httpx; no afecta a la API ni a los resultados.

### Integración y persistencia

```bash
python3 tests/integration.py --recreate
python3 tests/audit_logs.py
bash lab.sh exec -T frontend node verify-production.mjs
```

La primera prueba agrega un juego y recrea **solo** los servicios de esta práctica,
comparando el catálogo antes/después. Comprueba además que Password Grant está
deshabilitado y que Keycloak rechaza una solicitud sin PKCE. El rechazo OIDC
usa redirección al callback con `error=invalid_request`, no necesariamente HTTP 400.

### Navegador real con Playwright

```bash
python3 -m venv /tmp/opencode/browser-venv
/tmp/opencode/browser-venv/bin/pip install playwright==1.64.0
PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT=180000 /tmp/opencode/browser-venv/bin/playwright install chromium --only-shell
/tmp/opencode/browser-venv/bin/python tests/browser_demo.py
```

En otro sistema pueden hacer falta las dependencias de Chromium indicadas por
Playwright. En esta máquina se ha ejecutado correctamente sin instalarlas.
La prueba realiza 12 comprobaciones reales, incluyendo login de ambos usuarios,
PKCE, Bearer automático, alta 201, sesión SSO, guards, búsqueda, logout y vista
móvil de 390px. Crea un juego nuevo por ejecución.

Los resultados y capturas se guardan en `test-results/`:

- `browser.json`, `integration.json`, `log-audit.json`.
- `login-desktop.png`, `dashboard-desktop.png`, `dashboard-mobile.png`, `add-game-desktop.png`.

Los artefactos locales no guardan tokens ni contraseñas y `test-results/` queda
excluido de Git. Las pruebas de integración leen las contraseñas del entorno o
del `.env` privado, sin valores codificados en su código. Consulta
`INFORME-PRUEBAS.md` para el resultado histórico de la recuperación y ejecución.

## Versiones comprobadas

Angular 22.2.3, Angular CLI/build 22.2.2, keycloak-js 26.2.4; Node 24.22.0.
Python 3.12.15 en el contenedor; FastAPI 0.143.1, Uvicorn 0.54.0,
SQLAlchemy 2.1.4 y Pydantic 2.14.1. Keycloak 26.7.4, OpenLDAP 1.5.0,
PostgreSQL 16.15. Las imágenes base usan los tags definidos en Compose/Dockerfile;
`package-lock.json` fija las dependencias npm.

El ZIP usado como referencia se conserva localmente fuera de ambos proyectos y
no forma parte de lo publicado. Los repositorios contienen todos los archivos
necesarios para levantar esta práctica sin ese ZIP.

## Archivos privados y publicación

Se excluyen `.env`, variantes de entorno privadas, `.lab-data`, SQLite, claves,
dependencias, cachés, logs, trazas y resultados de pruebas. `.env.example` contiene
solo nombres de variables sin valores. No adjuntes exportaciones del realm o de
LDAP de una instalación viva: pueden contener credenciales o datos de usuarios.
