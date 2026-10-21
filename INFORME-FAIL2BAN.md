# Recuperación y verificación de Fail2Ban / LDAPS

Ejecución: 19 de octubre de 2026, hora local (20 de octubre en los logs UTC).
La sección de recuperación recoge las comprobaciones funcionales anteriores.
Las mediciones acotadas posteriores se documentan en el apartado final de este informe.

## Datos recuperados y evidencia

El daemon aislado quedó vacío tras el reinicio. Se reconstruyeron las imágenes
desde el código existente, conservando servicios, proyecto `ciber-p1-games`, puertos,
`.env` y la ubicación de `.lab-data`.

**No fue necesario reemplazar bases:** PostgreSQL estaba oculto al usuario normal
por UID/GID 70 y modo 700, pero su cluster completo de versión 16 seguía presente.
SQLite pasó `integrity_check=ok`, con 11 juegos antes de la recuperación. LDAP y
los certificados actuales estaban presentes, con TLS ya configurado.

Antes de intervenir se creó fuera de Git:

```text
../.lab-backups/recovery-20261019-203712/
├── current-state.tar          # datos actuales, .env, certificados/claves y configuración
├── original-extracted/        # extracción separada del respaldo anterior
├── inventory.json
└── verified.json
```

El original `../.lab-backups/20261019-194554/lab-before-tls.tar` se conservó intacto.
Su SQLite contiene 8 juegos. La copia LDAP se leyó con `slapcat`; los DNs y hashes
de contraseñas originales siguen presentes en el servicio actual. El cluster
PostgreSQL extraído se arrancó con PostgreSQL 16 en un contenedor temporal **sin red**:
se pudo consultar y coincidieron los IDs de realm, cliente y proveedor LDAP, con
dos usuarios del realm antes y después. Esta es una validación funcional del
respaldo, además de la lectura del índice del tar.

Los 11 juegos previos se conservaron con IDs y campos iguales; los archivos TLS
actuales se compararon byte a byte con la nueva copia. Las dos altas de prueba
posteriores dejaron **13 juegos**. No se mezclaron clusters ni se reinicializaron BD.
El archivo `rollback-images.tar.gz` de cero bytes es inválido y no se utilizó.

## Docker y construcción

- Endpoint conservado: `unix:///tmp/opencode/games-docker.sock`.
- Driver: `overlay2`; `--iptables=false` permanece en el daemon.
- Almacén persistente: `../.lab-docker/games-docker.ext4`, montado automáticamente
  en `/tmp/opencode/games-docker-store`; data-root `.../data`. Solo socket/exec-root
  permanecen temporales. No se ha provocado un nuevo reinicio físico de la PC.
- Construcciones secuenciales con lock, una descarga simultánea y un worker Angular.
- No se borraron imágenes/cachés, no se ejecutó prune y no se archivaron imágenes viejas.

Después de interrumpir la construcción silenciosa de Keycloak no quedaba un build
activo. Al reanudar con salida plain, bases, paquetes y copia de la distribución
estaban en caché; acabaron las capas finales y la exportación. No hay evidencia
suficiente para atribuir el tiempo del intento silencioso a una sola causa.
Los registros detallados de Keycloak y frontend están en `test-results/build-*.log`.
`scripts/build_observed.py` permite observar una única construcción sin perderla
por un timeout de la terminal/API.

## Protección instalada

| Servicio | Implementación | Jail / umbral final |
|---|---|---|
| Frontend | Angular compilado + Nginx, fallback SPA y callback | `http-flood`: 60 peticiones/IP en 10 s |
| Backend | Nginx en 8000; Uvicorn solo `127.0.0.1:8008` | `http-flood`: 60 peticiones/IP en 10 s |
| Keycloak | Distribución oficial 26.7.4 sobre Java 21/Debian; access log nativo | `http-flood`: 60 peticiones/IP en 10 s |
| OpenLDAP | OpenLDAP 1.5.0; LDAPS 636, sin listener 389 ni publicación al host | `ldaps-connections`: 60 conexiones/IP en 10 s |

Las cuatro imágenes ejecutan Fail2Ban e iptables con `NET_ADMIN`, sin modo
privilegiado ni socket Docker. Veto inicial: **10 minutos**. Las HTTP incrementan
por reincidencia (factor 2, máximo 1 día), con `iptables-allports` en INPUT del
contenedor. LDAP usa `iptables-multiport` solo para TCP/636, sin jail de contraseñas.

Los filtros se validaron contra logs reales mediante `fail2ban-regex`. Los HTTP
registran IP del socket, fecha, método, ruta sin consulta y estado; no cabeceras
ni cuerpos. Se retiraron el logger JWT, llamadas y configuración de demostración.
Keycloak usa la CA local y validación de nombre; no se desactivó TLS. Las migraciones
del `cn=config` y proveedor del realm son idempotentes y se repitieron al recrear.

## Resultados observados

- Cinco servicios permanentes `healthy`; `ldap-init` y `auth-migrate` en `Exited (0)`.
- Chromium: **12 comprobaciones correctas**, incluidos login de alice/bob, callback
  PKCE S256, renovación real, listado, alta 201, recarga, logout y ausencia de JWT
  en consola. Password Grant continúa deshabilitado para `games-spa`.
- Integración: **10 comprobaciones correctas**, CORS/estados HTTP y catálogo
  idéntico después de recrear los servicios; realm/cliente conservados.
- TLS: CA y nombre correctos aceptados; CA no confiable y nombre incorrecto
  rechazados. 389 cerrado y Uvicorn inaccesible desde la red bridge.
- Dos clientes independientes en la red existente: A `172.29.0.7`, B `172.29.0.8`.
  Se verificó la IP del socket antes de superar cada umbral, sin simular IPs con cabeceras.

| Jail en servicio | Ban de A | Contador de la regla de A | B durante el veto | A tras desbanear |
|---|---|---|---|---|
| Frontend | Sí | 0 → 1 paquete | HTTP 200 | HTTP 200 |
| Backend | Sí | 0 → 1 paquete | HTTP 200 | HTTP 200 |
| Keycloak | Sí | 0 → 1 paquete | HTTP 200 | HTTP 200 |
| OpenLDAP | Sí | 0 → 1 paquete | TLS correcto | TLS correcto |

Cada prueba envió una secuencia fija de 65 operaciones para activar la jail;
el bloqueo se acreditó mediante Ban, regla, contador y fallo de conexión de A,
no a partir de respuestas HTTP de error. Keycloak no fue vetado por LDAP.

- Supervisor: en copias efímeras sin puertos publicados, terminar Nginx o Fail2Ban
  produjo salida 1 del contenedor, sin aparentar salud.
- Auditoría: 437 líneas de stdout/access logs revisadas, sin errores operativos,
  JWT, credenciales privadas, cabeceras ni consultas en access logs.
- 26 pruebas del backend y 3 comprobaciones de publicación correctas.

Evidencias saneadas: `test-results/recovery.json`, `browser.json`,
`integration.json`, `security.json`, `log-audit.json` y capturas. Fuera de Git.

## Arranque y repetición de verificaciones

```bash
bash /home/mint/Documentos/Ciberseguridad/videojuegos-backend/lab.sh up
bash /home/mint/Documentos/Ciberseguridad/videojuegos-backend/lab.sh ps -a
```

Desde `videojuegos-backend`:

```bash
/tmp/opencode/browser-venv/bin/python tests/browser_demo.py
python3 tests/integration.py --recreate
python3 tests/security_checks.py
python3 tests/supervisor_checks.py
python3 tests/audit_logs.py
```

Frontend: http://localhost:4200; backend: http://localhost:8001;
Keycloak: http://localhost:8082. Los tres siguen publicados solo en `127.0.0.1`.

## Etapa final: generador y mediciones acotadas reales

Proyecto local nuevo: `../videojuegos-loadtest/`. Adapta el `flood.py` del maestro
con host/puerto por argumentos, esquema, ruta, duración, concurrencia y RPS global.
Se ejecutó en clientes independientes `python:3.12-slim`, fuera de las imágenes
protegidas. No se reconstruyó ni recuperó de nuevo el laboratorio para esta etapa.

El protocolo se escribió antes de medir en `videojuegos-loadtest/PROTOCOL.md`:
escalones de 10 s, cero errores, 100 % HTTP esperado, ≥95 % del RPS solicitado,
p95 ≤250 ms, p99 ≤500 ms, B disponible en <1 s, sin reinicios/OOM, MemAvailable
≥1 GiB y CPU host <85 % sostenido en dos muestras. Se probó un servicio a la vez.

Campaña UTC: **2026-10-20 04:00:45 → 04:06:10**. Basal activo 2 RPS;
capacidad sin veto 5/10/19 RPS; repetición de 19 y comparación protegida de 19.
Se reservaron una conexión y 1 RPS de presupuesto para el observador B: carga A
máxima 19 RPS/3 workers, presupuesto global hasta 20 RPS/4 conexiones. Los
healthchecks existentes siguieron como tráfico de fondo, sin cambios.

No se paró ninguna jail: durante cada escalón sin veto se exceptuó únicamente
la IP de A, con restauración en `finally` y watchdog de 25 s. Las cuatro jails
permanecieron activas y la lista final de excepciones fue idéntica a la inicial.
También se verificó sin carga HTTP la restauración ante error y SIGKILL del
controlador, usando una dirección TEST-NET sin cliente real.

### Mayor escalón estable y repetición

| Servicio / operación pública | RPS solicitados | RPS HTTP repetición | HTTP completadas | p50 ms | p95 ms | p99 ms | Errores |
|---|---|---|---|---|---|---|---|
| Frontend: HTML `GET /` | 19 | 18.937 | 190 | 1.871 | 2.412 | 24.901 | 0 |
| Backend: Nginx + FastAPI `GET /health` | 19 | 18.841 | 189 | 3.496 | 4.376 | 5.747 | 0 |
| Keycloak: `GET /realms/games-lab/.well-known/openid-configuration` | 19 | 18.937 | 190 | 5.213 | 6.182 | 9.214 | 0 |

Todos los escalones sin veto pasaron el criterio y el mayor se confirmó con una
repetición. Conclusión: **mayor carga estable observada dentro del límite probado**,
no capacidad máxima. Solo se midieron esas rutas; no login/LDAP, CRUD/SQLite,
assets completos ni rendimiento simultáneo de las tres superficies.

### Protección activa, sin excepción

| Servicio | HTTP 200 completadas | Timeouts | Conexiones rechazadas | Nuevo Ban / paquetes bloqueados | Observador B |
|---|---|---|---|---|---|
| Frontend | 64 | 18 | 12 | Sí / 31 | HTTP 200 |
| Backend | 62 | 20 | 12 | Sí / 32 | HTTP 200 |
| Keycloak | 70 | 18 | 11 | Sí / 29 | HTTP 200 |

A fue `172.29.0.7`, B `172.29.0.8`; se verificó la IP del socket antes de medir.
Las respuestas HTTP no se mezclaron con timeouts/errores de conexión. Los fallos
de A en estas filas fueron vetos de IP demostrados por evento Ban y firewall,
con B disponible; **no caídas generales ni evidencia de capacidad agotada**.

Se observaron 24 sondeos B por servicio, todos HTTP 200; latencia máxima B
85.877 ms. En las muestras: CPU host máxima 42.365 %, MemAvailable mínima
5.248 GiB, cero reinicios y sin OOM. Son valores muestreados, no picos instantáneos
garantizados. Las tablas por servicio incluyen también CPU/RAM de contenedores.

Evidencias versionables y saneadas:
`../videojuegos-loadtest/results/20261020T040045Z/` contiene los 18 escalones,
`campaign.json`, `SUMMARY.md`, `summary.json` y `restoration-checks.json`.
No contienen tokens, contraseñas, cabeceras ni cuerpos. Cuatro comprobaciones
locales del generador verificaron HTTP de error, timeout/conexión, límite global
entre workers e interrupción limpia. No se repitió la batería funcional anterior.

Comandos exactos de instalación/ejecución y explicación de los resultados en
`../videojuegos-loadtest/README.md`. Las comprobaciones técnicas descritas pasaron
dentro de estos límites. No se aumentó la carga ni se buscó la capacidad máxima.
Los cuatro proyectos se publicaron después de esta campaña, sin cambiar sus cifras.

## Contraste posterior con los requisitos del maestro

La afirmación anterior de ausencia de pendientes se limita al protocolo técnico
medido; **no acredita cumplimiento íntegro del enunciado**. Véase
[CONTRASTE-ENUNCIADO.md](CONTRASTE-ENUNCIADO.md):

1. **Pendiente de acreditar:** no se encontró evidencia de haber ejecutado primero
   el `flood.py` original y después modificarlo. Los resultados publicados pertenecen
   al adaptado. Una ejecución futura no demostrará retroactivamente ese orden;
   la subsanación debe registrarse con sus fechas reales.
2. **Diferencia de repositorios:** LDAP/Keycloak/PostgreSQL estaban originalmente
   en `cybersecurity-backend`. `cybersecurity-auth` es una separación nueva de esa
   infraestructura, no un tercer repositorio previo reutilizado. No se identificó
   otro repo LDAP anterior omitido en el directorio y la cuenta revisados. Hace falta
   confirmar la aceptación de esa correspondencia o facilitar el repo anterior
   si existe en otra ubicación.

Esta revisión solo corrige documentación: no reconstruye imágenes, ejecuta el
original ni repite benchmarks, y no altera los resultados históricos.
