# Informe de recuperación y pruebas reales

> Informe histórico anterior a la actividad Fail2Ban. Las referencias a JWT en
> consola, LDAP sin TLS e infraestructura dentro del backend describen aquella
> versión y ya no corresponden al estado actual. Consulta `INFORME-FAIL2BAN.md`.

Fecha de ejecución: 14 de octubre de 2026, hora local del host
(15 de octubre de 2026 en los logs UTC). Entorno: Linux Mint Live, Docker 29.1.3,
Compose 2.40.3. El sistema se deja iniciado.

## 1. Estado recuperado tras el reinicio

Se encontraron y conservaron las dos carpetas de aplicación, el ZIP de referencia,
el frontend Angular completo con `package-lock.json`, el backend FastAPI por capas,
los Dockerfiles, Compose, el realm Keycloak y el LDIF LDAP.

La carpeta `.lab-data` conservaba:

- Base SQLite con los tres videojuegos semilla; `PRAGMA integrity_check`: `ok`.
- Directorio/configuración OpenLDAP.
- Base PostgreSQL de Keycloak.

El Docker original seguía conteniendo sus diez contenedores detenidos/creados y
el volumen `bank-key-rotation-lab_bank_data`. No había servicios de esta práctica
ejecutándose al iniciar la recuperación.

El daemon aislado y sus imágenes estaban en `/tmp` y desaparecieron con el
reinicio. Se arrancó de nuevo mediante `lab.sh`, se descargaron las imágenes y
se reconstruyeron las aplicaciones usando **los archivos existentes**. Las bases
de datos y los usuarios se recuperaron desde `.lab-data`, sin reinicializarlos.

### Trabajo anterior completado

- Código de Angular, FastAPI e infraestructura.
- Construcción de imágenes y arranque saludable del stack.
- Inicialización LDAP con binds correctos de alice/bob.
- Comprobación HTTP inicial de health, API sin Bearer y discovery Keycloak.

### Trabajo interrumpido y completado ahora

- Instalación de Chromium/Playwright y prueba completa de navegador.
- Pruebas automatizadas del backend e integración HTTP.
- Recreación de contenedores para demostrar persistencia.
- Comprobación del bundle de producción y logging JWT.
- Auditoría de logs, capturas y documentación.

## 2. Resultados

| Comprobación ejecutada | Resultado real |
|---|---|
| Construcción Docker backend | Correcta, FastAPI y dependencias instaladas |
| Construcción Docker frontend | Correcta; compila development y production |
| OpenLDAP | healthy; bind de alice y bob correcto |
| ldap-init | Exited (0); repetible sin sobrescribir directorio |
| PostgreSQL | healthy; recuperó BD anterior |
| Keycloak | healthy; realm games-lab existente conservado |
| Backend | healthy; `/health` devuelve 200 |
| Frontend | healthy; Angular funciona en Chromium |
| Pytest backend | **26 passed**, 1 advertencia de deprecación de TestClient/httpx |
| Integración HTTP | **10 grupos de comprobaciones correctos**, incluyendo recreación |
| Playwright / Chromium | **12 comprobaciones correctas**, sin errores JS no controlados |
| Producción | Bundle sin mensaje/logger JWT de demostración |
| Persistencia | Catálogo idéntico antes/después de recrear todos los servicios |
| Integridad SQLite final | `ok`; 6 juegos tras las altas de prueba |
| Federación real | alice y bob con `federation_link` no nulo en Keycloak |
| Logs actuales auditados | 486 líneas, 0 ERROR/FATAL/Traceback/Exception y 0 valores JWT |
| Proyectos anteriores | Mismos diez contenedores y mismo volumen en el daemon original |

Los recuentos de filas/líneas corresponden al momento de la verificación. Los
healthchecks continúan generando líneas; repetir las pruebas agrega videojuegos.

### Backend: cobertura significativa

Las pruebas usan una SQLite temporal, separada de la demostración. Se verifica:

- GET público de salud.
- GET y POST protegidos: encabezado ausente, esquema Basic, Bearer vacío y formatos
  incorrectos, incluyendo espacios dentro del token.
- Aceptación deliberada de JWT ficticio con forma `aaa.bbb.ccc`.
- POST correcto, respuesta 201 y campos de salida.
- Entradas inválidas: título en blanco y años fuera de rango.
- Preflight CORS permitido para localhost y rechazado para un origen externo.

### Integración HTTP sobre servicios reales

`tests/integration.py --recreate` comprobó:

1. Health público 200.
2. Diez casos de GET/POST sin Bearer válido con respuesta 401.
3. Token falsificado de formato correcto aceptado, conforme a la limitación académica.
4. CORS local permitido y origen externo rechazado.
5. Discovery OIDC y issuer `http://localhost:8082/realms/games-lab`.
6. Password Grant del cliente games-spa rechazado con `unauthorized_client`.
7. Authorization Code sin PKCE rechazado mediante redirección OIDC con
   `error=invalid_request` y falta de `code_challenge_method`.
8. POST 201 seguido de GET que recupera exactamente el juego nuevo.
9. Recreación de OpenLDAP, PostgreSQL, Keycloak, backend, frontend y ldap-init;
   el listado antes/después resultó idéntico.
10. Realm disponible tras recreación, conservado en PostgreSQL.

El registro de esta ejecución es el videojuego ID 5, `Integración HTTP 1792040077`.
El primer script de prueba asumía HTTP 400 para el punto 7 y seguía automáticamente
la redirección al frontend: se corrigió la prueba para inspeccionar la respuesta
OIDC real. La configuración PKCE estaba rechazando correctamente la solicitud.

### Playwright sin mocks

Se ejecutó `tests/browser_demo.py` con Playwright 1.64.0 y Chromium headless shell:

1. Guard de dashboard sin sesión y pantalla login Angular.
2. Petición con `response_type=code`, `code_challenge_method=S256`, cliente y callback exactos.
3. Login alice desde la página real de Keycloak y mensaje JWT en consola local.
4. Bearer de Keycloak en GET HttpClient real; claims issuer y usuario correctos.
5. Dashboard a 390px sin desbordamiento horizontal.
6. Página de alta y validación de formulario vacío.
7. Alta desde Angular con POST 201, Bearer automático, mensaje JWT local y listado actualizado.
8. Recarga completa con recuperación de SSO y juego conservado.
9. Búsqueda del juego devuelve una sola tarjeta.
10. Logout OIDC y bloqueo de `/games/new` sin sesión.
11. Ningún error JavaScript no controlado.
12. Login bob mediante el mismo flujo real de Keycloak/LDAP.

La ejecución final creó el videojuego ID 6. La ejecución previa al ajuste del
logger creó el ID 4; se conservaron ambos como evidencia de las pruebas.

La consulta real ejecutada en PostgreSQL:

```sql
SELECT username, federation_link IS NOT NULL AS ldap_federated
FROM user_entity WHERE username IN ('alice','bob');
```

Devolvió `alice | t` y `bob | t`.

### Producción y logs

Se detectó que la condición de entorno desactivaba la ejecución del logger JWT,
pero el texto seguía incluido en el bundle compilado. Se añadió reemplazo de
archivo Angular por una función vacía en producción. Se recompiló y ejecutó
`verify-production.mjs`: **PASS**, el mensaje no está en el bundle final.
Se repitió Playwright para comprobar que la demostración local sigue mostrándolo.

`tests/audit_logs.py` revisó todos los logs actuales del stack: sin errores
importantes y sin valores JWT. Se observan advertencias informativas del modo
desarrollo de Angular/Keycloak y features deprecadas de Keycloak. El TestClient
de Starlette también avisa de una deprecación de su integración con httpx;
las 26 pruebas pasan y la aplicación no depende del TestClient en ejecución.

## 3. Evidencias conservadas

```text
test-results/
├── browser.json
├── integration.json
├── log-audit.json
├── login-desktop.png
├── dashboard-desktop.png
├── dashboard-mobile.png
└── add-game-desktop.png
```

Se inspeccionaron las capturas de escritorio y móvil. Los artefactos no guardan
los JWT ni las contraseñas usados durante las pruebas.

## 4. Estado final y pendientes

No quedan fallos funcionales conocidos en el alcance probado. El sistema queda
activo en localhost:4200, localhost:8001 y localhost:8082.

Limitaciones intencionadas del alcance:

- El backend **no verifica criptográficamente** JWT; acepta tokens falsificados
  con formato válido, según el requisito del profesor.
- Entorno de demostración HTTP local, Angular dev server y Keycloak start-dev.
- El daemon aislado pierde imágenes/caché al reiniciar por usar `/tmp`, pero los
  datos sobreviven en `.lab-data`; `bash lab.sh up` recupera el entorno.
- Se probó Chromium, no se afirma compatibilidad verificada con otros navegadores.

No se creó ningún repositorio Git ni se realizaron commits o pushes.
