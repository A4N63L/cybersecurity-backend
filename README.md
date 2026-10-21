# GameVault · Backend y laboratorio Fail2Ban

FastAPI + SQLite, frontend Angular y autenticación Keycloak/OpenLDAP con LDAPS.
Las tres superficies HTTP protegidas son **frontend, backend y Keycloak**.
OpenLDAP es adicional, con protección específica de conexiones a 636;
PostgreSQL es el almacenamiento de apoyo de Keycloak.

## Proyectos y arranque

Conserva estas carpetas hermanas. Los cuatro repositorios ya están publicados
en la cuenta `A4N63L`; frontend/backend se reutilizaron, auth/loadtest son nuevos:

```text
Ciberseguridad/
├── videojuegos-frontend/    # Angular compilado + Nginx + Fail2Ban
├── videojuegos-backend/     # FastAPI + Nginx + Fail2Ban; orquestación y datos
├── videojuegos-auth/        # Keycloak, OpenLDAP, PostgreSQL y seguridad común
└── videojuegos-loadtest/    # Generador y resultados; opcional para arrancar la aplicación
```

Requisitos: Docker Compose con contextos de construcción adicionales, Bash,
Python 3 y OpenSSL en el host. Internet en la primera construcción.
La rama de Docker aislado de Mint Live también utiliza `sudo`, `util-linux`
(`flock`, `mount`, `losetup`, `blkid`) y `e2fsprogs` (`mkfs.ext4`).

Desde este proyecto:

```bash
python3 scripts/setup_env.py
bash lab.sh docker-host
bash lab.sh up
bash lab.sh ps -a
```

El generador de `.env` nunca sobrescribe credenciales existentes. `lab.sh up`
genera una CA/certificado solo si no existen, combina los dos Compose con rutas
explícitas y conserva el proyecto `ciber-p1-games`, servicios y volúmenes.
`ldap-init` y `auth-migrate` deben terminar en 0; los cinco servicios permanentes
deben estar `healthy`.

| Servicio | Acceso publicado |
|---|---|
| Frontend | http://localhost:4200, bind `127.0.0.1:4200` |
| Backend | http://localhost:8001, bind `127.0.0.1:8001` |
| Keycloak | http://localhost:8082, bind `127.0.0.1:8082` |
| LDAP | `ldaps://openldap:636`, solo red bridge; 389 cerrado |
| PostgreSQL | `postgres:5432`, solo red bridge |

Navega usando **localhost**: issuer, CORS y callbacks conservan esos orígenes.
`alice` y `bob` usan las contraseñas privadas `ALICE_PASSWORD` y `BOB_PASSWORD`;
la administración de Keycloak usa `KEYCLOAK_ADMIN_PASSWORD`. No publiques `.env`.

## Docker y persistencia existentes

En esta máquina el daemon predeterminado usa `vfs`; `lab.sh` selecciona el
daemon `overlay2` en `unix:///tmp/opencode/games-docker.sock`. La opción
`GAMES_ISOLATED_DOCKER=1` lo fuerza; `0` usa el Docker seleccionado por el entorno.
`bash lab.sh docker-host` informa el endpoint seleccionado sin arrancar servicios.

Las imágenes y la caché ya no residen en el tmpfs de `/tmp`: se guardan en la
imagen ext4 persistente `../.lab-docker/games-docker.ext4` (4 GiB lógicos, sparse),
montada automáticamente en `/tmp/opencode/games-docker-store`. El `data-root` real
es `/tmp/opencode/games-docker-store/data`; el socket y exec-root sí son temporales.
`scripts/docker_store.py` comprueba el dispositivo de respaldo antes de reutilizar
el montaje y nunca reformatea un almacén existente. Usa el almacenamiento persistente
del Live, por lo que conservar `.lab-docker` es necesario para mantener las imágenes.

`lab.sh up` construye **un servicio cada vez**, con salida detallada; las descargas
del daemon están limitadas a una simultánea. Un lock impide construcciones duplicadas
mediante el lanzador. Angular se compila con un solo worker.

Para una construcción larga observable que sobreviva al timeout del terminal/API:

```bash
python3 scripts/build_observed.py start keycloak
python3 scripts/build_observed.py status keycloak
```

La salida plain se conserva en `test-results/build-keycloak.log`. No inicies otra
construcción hasta que el estado indique `exit_code`; el mismo procedimiento admite
`frontend`, `backend` y `openldap`. También puedes usar `bash lab.sh build keycloak`
en primer plano, sin `--quiet`.

El daemon aislado mantiene `--iptables=false`. Las jails instalan reglas dentro
del namespace de cada contenedor, no en el firewall del host. No se monta el
socket Docker en ningún servicio ni se utiliza modo privilegiado.

`compose.live.yaml` mantiene los volúmenes existentes como bind a `.lab-data/`:
`ldap-data`, `ldap-config`, `keycloak-db`, `games`. El SQLite original sigue en
`.lab-data/games/games.db`. Los certificados están en `.lab-data/tls/`, ignorado
por Git. No cambies de daemon para operar sobre una instalación existente.

```bash
bash lab.sh stop                  # conserva los volúmenes
bash lab.sh up
bash lab.sh up --force-recreate   # conserva datos y repite migraciones
```

No elimines volúmenes ni `.lab-data`. Para TLS, migración y restauración consulta
`../videojuegos-auth/README.md`.

## Implementación HTTP

- Frontend: build de producción servido por Nginx en 4200, con fallback SPA.
- Backend: Nginx en 8000; Uvicorn **solo en `127.0.0.1:8008`**, sin access log
  propio ni confianza en cabeceras proxy. CORS permanece en FastAPI.
- Keycloak: distribución oficial 26.7.4 copiada a Debian con Java 21; access log
  nativo usando `%a - - %t "%m %R" %s`. `%R` omite la consulta.
- Cada imagen instala y ejecuta Fail2Ban, Python e iptables con `NET_ADMIN`.
  Configuración común única en `videojuegos-auth/common/`.
- Supervisor PID 1: señales a los grupos de procesos y salida 1 ante la muerte
  de cualquier proceso crítico. Healthchecks comprueban HTTP y Fail2Ban.

Jail `http-flood`: **60 peticiones por IP en 10 s**, veto inicial **10 min**,
incremento por reincidencia, factor 2 y máximo 1 día. Acción `iptables-allports`
en INPUT del propio contenedor. Se conservan los valores iniciales de la práctica:
la navegación funcional comprobada no produjo vetos.

Logs regulares en `/var/log/security/access.log` (frontend/backend) y
`/opt/keycloak/data/log/keycloak-http-access.log` (Keycloak). Solo IP del socket,
fecha, método, ruta sin query y estado. Sin JWT, Authorization, cookies ni cuerpos.
El error log genérico de Nginx se descarta porque puede incluir peticiones completas;
el supervisor registra las salidas de procesos y los healthchecks detectan fallos.
Los logs y la base de vetos son locales al contenedor; las BD de negocio son
persistentes. Keycloak rota su access log diariamente.

## Autenticación y API

Authorization Code + **PKCE S256**, cliente público `games-spa`, realm `games-lab`.
Password Grant/Implicit/Service Accounts deshabilitados en ese cliente. Tokens
en memoria; renovación antes de las peticiones y Bearer limitado a `/api/games`.
No existe logger JWT en desarrollo ni producción.

Endpoints: `/health` público; GET y POST `/api/games`; `/docs` para OpenAPI.
SQLite conserva los juegos; la semilla se añade únicamente si la tabla está vacía.

**Limitación académica existente:** el backend comprueba el formato Bearer y tres
segmentos Base64URL, pero no verifica firma, expiración, issuer, audience ni
permisos. La protección Fail2Ban no cambia esa validación.

## Comprobaciones breves reproducibles

```bash
python3 tests/integration.py --recreate
python3 tests/security_checks.py
python3 tests/supervisor_checks.py
python3 tests/audit_logs.py
python3 -m unittest discover -s tests -p test_publication.py
bash lab.sh exec -T backend python -m pytest -q tests/test_backend.py
```

El test de integración crea un juego y comprueba catálogo idéntico tras recrear.
`security_checks.py` crea dos clientes efímeros sin privilegios en la red existente,
verifica primero su IP observada y envía una secuencia fija de hasta 65 operaciones
por jail. Exige evento Ban, regla y aumento del contador de paquetes, fallo de A,
éxito de B y recuperación al desbanear. También comprueba CA/nombre, rechazos TLS,
cierre de 389 y ausencia de bypass a Uvicorn. No es un benchmark.

`supervisor_checks.py` usa copias efímeras del frontend sin puertos publicados:
termina Nginx o Fail2Ban y exige que PID 1 salga con error. `audit_logs.py` revisa
stdout y access logs sin imprimir tokens; distingue el cierre administrativo normal
de conexiones PostgreSQL de errores operativos.

Navegador real:

```bash
python3 -m venv /tmp/opencode/browser-venv
/tmp/opencode/browser-venv/bin/pip install playwright==1.64.0
/tmp/opencode/browser-venv/bin/playwright install chromium --only-shell
/tmp/opencode/browser-venv/bin/python tests/browser_demo.py
```

El test adelanta únicamente el reloj del navegador para provocar una renovación
real sin esperar la caducidad. Comprueba login/logout de usuarios LDAP, callback,
alta/listado, recarga, responsive y ausencia de JWT en consola. Los artefactos
saneados se guardan en `test-results/`, ignorado por Git.

Para comprobar contra el respaldo anterior a la migración:

```bash
python3 tests/verify_preserved_games.py ../.lab-backups/20261019-194554/lab-before-tls.tar
```

El generador y las mediciones acotadas reales están en `../videojuegos-loadtest/`.
Su README contiene los comandos y el protocolo previo; `results/20261020T040045Z/`
incluye tablas por servicio y muestras saneadas. Se observaron y repitieron 19 RPS
sin veto dentro del presupuesto de 20 RPS/4 conexiones, sin buscar capacidad máxima.
El estado final de ambas etapas está en `INFORME-FAIL2BAN.md`.
El [contraste con el enunciado](CONTRASTE-ENUNCIADO.md) distingue las evidencias:
el original se ejecutó el 21 de octubre de 2026, seguido de una comprobación del
adaptado, como subsanación posterior; no se acredita que ocurriera antes del
desarrollo. LDAP/Keycloak se separaron de este backend hacia un repo auth nuevo,
en lugar de reutilizar un tercer repositorio LDAP previo identificado.
