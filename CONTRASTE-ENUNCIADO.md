# Contraste documental de dos requisitos del maestro

Revisión inicial: 20 de octubre de 2026 UTC, únicamente documental.
Actualización: **21 de octubre de 2026 UTC**, tras una ejecución posterior del
original seguida de una comprobación breve del adaptado. No se repitió la campaña
de capacidad anterior ni se reconstruyeron imágenes del dashboard.

## 1. Ejecutar primero el original y después modificarlo

**Estado actualizado:** la ejecución del original intacto **ya está realizada y
documentada**, seguida de una comprobación del adaptado. **Sigue sin acreditarse
históricamente una ejecución anterior al desarrollo de la adaptación.**

El origen inspeccionado es `attacker/flood.py` de `fail2ban-ddos.zip`, conservado
localmente junto a los proyectos. Su SHA-256, calculado leyendo ese miembro del
ZIP, y verificado antes y después de la nueva ejecución, es:

```text
48189b9442150d04c1771d83df3cf57eed3048536e2f44dba7fe17cca9d35434
```

Ese hash por sí solo identifica el archivo; la ejecución ahora se acredita además
con comando, fechas y stdout en
[`original-followup-20261021T033842Z`](https://github.com/A4N63L/cybersecurity-loadtest/blob/main/results/original-followup-20261021T033842Z/FOLLOWUP.md).
La copia sin editar se conserva en `cybersecurity-loadtest/reference/attacker/flood.py`.

En la revisión del día 20 no se había localizado esa evidencia. La campaña anterior
`results/20261020T040045Z/` sigue correspondiendo únicamente al adaptado y conserva
sus datos de 04:00:45 a 04:06:10 UTC del 20 de octubre. No se han cambiado ni
reinterpretado sus fechas como si el original se hubiera ejecutado primero.

El original tiene destinos fijos `victim-protected` y `victim-unprotected` en
HTTP/80; no puede dirigirse al laboratorio actual pasando host y puerto por CLI.
El `run_demo.sh` del ZIP construye imágenes y su Compose configura 150 RPS,
150 workers y 45 s por destino: no se utilizó. Se prepararon solo las dos víctimas
con los archivos originales, en `172.30.240.0/24`, sin publicar puertos ni colisionar
con la red del dashboard. El cliente reutilizó Python 3.12 slim en vez de construir
el cliente Alpine/curl del ZIP, porque el script solo requiere la biblioteca estándar.

### Nueva secuencia efectivamente realizada

1. Original sin editar: **21 de octubre, 03:41:39.712734 → 03:42:02.882472 UTC**,
   con `DURATION=10`, `CONCURRENCY=3`, `REQUESTS_PER_SECOND=20`. El stdout acredita
   primero `victim-protected` y después `victim-unprotected`.
2. Adaptado, después de finalizar el original: comando lanzado a las
   **03:42:07.738100 UTC**, contra `frontend 4200`, con los argumentos reales
   `--scheme http --path / --duration 5 --concurrency 1 --rps 2 --timeout 1`.

| Ejecución | Intentos contabilizados | HTTP 200 | Fallos/no-200 agrupados |
|---|---|---|---|
| Original, `victim-protected` | 87 | 64 | 23 |
| Original, `victim-unprotected` | 200 | 200 | 0 |
| Adaptado, frontend | 10 | 10 | 0; sin timeouts ni errores de conexión/protocolo |

La víctima protegida registró un Ban de `172.30.240.20`, con 35 paquetes rechazados
en su regla, mientras otra IP seguía accediendo. Esto demuestra el veto de esa IP,
**no permite atribuir uno a uno los 23 fallos agregados**: el original mezcla
estados no-200 y errores de transporte, y paquetes no equivalen a peticiones.
La comprobación del adaptado midió 5,003 s y 1,999 RPS; no repite los benchmarks.

Se retiraron solo contenedores, red, etiquetas de imagen y directorios temporales
de esta ejecución. Las cuatro jails del dashboard quedaron activas. El dashboard
se encontró detenido tras reiniciar el daemon y únicamente se arrancaron sus
contenedores existentes: los IDs, imágenes y huellas de configuración se conservaron.
Se documentan dos preparaciones abortadas sin carga, distintas de la ejecución real.

**Diferencia histórica que permanece:** se acredita ahora original → comprobación
del adaptado, pero no original → desarrollo de la adaptación. Esta es una
**subsanación posterior**. Su aceptación respecto al orden literal corresponde al
maestro; no se afirma ni puede demostrarse retroactivamente que la ejecución
del original ocurrió antes del desarrollo ya realizado.

## 2. Reutilizar repositorios anteriores de LDAP, backend y frontend

### Procedencia comprobable

El commit original del backend
[`564ee37`](https://github.com/A4N63L/cybersecurity-backend/tree/564ee37342b7c16f89fe556f24e7a3b276eede30)
ya contenía la infraestructura LDAP/Keycloak/PostgreSQL. Su README decía:

> Infraestructura única del laboratorio: `compose.yaml`, `compose.live.yaml` e
> `infra/` viven en este repositorio backend. No se requiere un tercer repositorio.

| Ubicación anterior, en `cybersecurity-backend` | Ubicación actual, en `cybersecurity-auth` |
|---|---|
| `infra/ldap/init.sh` | `ldap/init.sh`, adaptado a LDAPS |
| `infra/ldap/users.ldif.template` | `ldap/users.ldif.template` |
| `infra/keycloak/import/games-lab-realm.json` | `keycloak/import/games-lab-realm.json`, actualizado para TLS |
| Servicios `openldap`, `ldap-init`, `keycloak`, `postgres` de `compose.yaml` | Fragmento `compose.yaml`, integrado desde `backend/lab.sh` |

El objeto Git de `users.ldif.template` coincide en ambos historiales:
`94699262e911f5932e8c280c6c3a98617a404a8a`. El historial anterior de los archivos
sigue disponible en el backend; auth empieza con el commit nuevo `c55bda7`.
Esto acredita traslado/reutilización de infraestructura existente, **no continuidad
del historial de un repositorio LDAP independiente**.

### Búsqueda de un repositorio LDAP anterior omitido

En el estado inicial del directorio de trabajo había frontend y backend, más los
ZIP del maestro; no había un proyecto LDAP con Git separado. Se revisaron además
los 13 repositorios accesibles de `A4N63L`: los cuatro de la entrega y nueve
anteriores (siete con árbol de rama predeterminada no truncado y dos vacíos).
No se identificaron rutas LDAP/Keycloak ni referencias en los README disponibles
de esos repositorios anteriores. La búsqueda de código `ldap` tampoco devolvió
coincidencias fuera de los cuatro repositorios actuales. Entre los revisados
están `security-api-t2p1`, `security-frontend-t2p2` y `chat_seguro_ciberseguridad`.

**No se identificó un repositorio LDAP previo dejado sin actualizar** en ese
ámbito. Esto no permite afirmar nada sobre una URL o cuenta distinta no facilitada.

### Diferencia real con la lectura literal del enunciado

Se reutilizaron **dos repositorios anteriores**: `cybersecurity-dashboard` y
`cybersecurity-backend`. Se crearon **dos nuevos**: `cybersecurity-auth`, para
separar LDAP/Keycloak/PostgreSQL antes contenidos en backend, y
`cybersecurity-loadtest`, para el script y sus evidencias.

Por tanto, no debe declararse «tres repositorios anteriores reutilizados y solo
uno nuevo». La corrección mínima es documentar esta correspondencia y confirmar
con el maestro si acepta la extracción de la infraestructura del backend. Si el
repositorio LDAP anterior existe en otra ubicación, hace falta su URL para revisar
y actualizar ese repositorio preservando su historial, en vez de dar por equivalente
el repo nuevo. No se ha creado un quinto repositorio ni se ha reorganizado de
nuevo la infraestructura del dashboard para esta subsanación.

## Documentación y mediciones existentes

El README de loadtest distingue cambios respecto al original, ejemplos de uso,
comandos realmente utilizados, campaña del adaptado del día 20 y subsanación
del día 21. Conserva la tabla de 19 RPS por 10 s con sus límites y añade el resultado
del original y la comprobación breve posterior. No se han cambiado los JSON,
fechas, cifras ni el protocolo de la campaña histórica del día 20.
