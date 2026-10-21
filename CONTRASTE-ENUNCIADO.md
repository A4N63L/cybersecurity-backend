# Contraste documental de dos requisitos del maestro

Revisión del 20 de octubre de 2026 UTC. No se reconstruyeron imágenes ni se ejecutó
el script original ni se repitieron benchmarks durante esta revisión.

## 1. Ejecutar primero el original y después modificarlo

**Estado: PENDIENTE de acreditar. No se encontró evidencia verificable de una
ejecución del original anterior a la adaptación.**

El origen inspeccionado es `attacker/flood.py` de `fail2ban-ddos.zip`, conservado
localmente junto a los proyectos. Su SHA-256, calculado leyendo ese miembro del
ZIP sin ejecutarlo, es:

```text
48189b9442150d04c1771d83df3cf57eed3048536e2f44dba7fe17cca9d35434
```

Ese hash demuestra la identidad del archivo inspeccionado, **no su ejecución**.
No se localizó un registro con comando, fecha y salida del original. Las evidencias
publicadas en `cybersecurity-loadtest/results/20261020T040045Z/` identifican destinos
`frontend`, `backend` y `keycloak`, parámetros CLI y métricas de la versión adaptada.
La campaña va de 04:00:45 a 04:06:10 UTC del 20 de octubre de 2026. Tampoco las
pruebas del generador adaptado acreditan la ejecución del original.

El original tiene destinos fijos `victim-protected` y `victim-unprotected` en
HTTP/80; no puede dirigirse al laboratorio actual pasando host y puerto por CLI.
El `run_demo.sh` del ZIP construye imágenes y su Compose configura 150 RPS,
150 workers y 45 s por destino: no se ejecutó como parte de esta revisión.

**Corrección mínima pendiente:** preparar los dos destinos fijos en un entorno
aislado cuya red no colisione con la actual y ejecutar el archivo original intacto
con sus variables de entorno acotadas, por ejemplo 10 s/destino, 1 worker y 2 RPS.
Conservar hash, comando exacto, fecha, stdout y condiciones del entorno.
No se presentan cifras hasta realizar esa ejecución.

Una ejecución futura será una **subsanación posterior**, no prueba retroactiva
del orden original → modificación. Si el maestro exige demostrar ese orden, se
necesita una nueva secuencia documentada que comience por el original y continúe
con la adaptación, sin atribuirle una fecha anterior a los resultados existentes.

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
el repo nuevo. No se crea un quinto repositorio ni se altera infraestructura en
esta revisión documental.

## Documentación y mediciones existentes

El README de loadtest ahora distingue los cambios respecto al original, ejemplos
de uso frente a comandos efectivamente utilizados y ejecución adaptada frente a
la previa pendiente. Incluye la repetición de 19 RPS solicitados por 10 s y sus
RPS alcanzados/percentiles, junto con sus límites y el presupuesto reservado a B.
No se han cambiado los JSON, fechas, cifras ni el protocolo histórico.
