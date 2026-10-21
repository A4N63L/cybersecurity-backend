# Análisis con Nuclei — Backend FastAPI / Nginx

Análisis no intrusivo de vulnerabilidades conocidas y configuraciones expuestas sobre el servicio indicado. Esta entrega solo **enumera** los hallazgos; no aplica correcciones.

- **Fecha (UTC):** 2026-10-21 05:13
- **Servicio:** Backend FastAPI / Nginx
- **Dirección analizada:** `http://172.29.0.4:8000` (resuelta en el contenedor como `http://backend:8000`)
- **Herramienta:** Nuclei v3.11.1, imagen oficial `projectdiscovery/nuclei` pinneada por digest
- **Plantillas:** snapshot oficial `projectdiscovery/nuclei-templates` en commit `b4826535d814f33522faae784678e62686d33b66`, filtradas a severidades `medium,high,critical`; sin tags `dos`, `fuzz` ni `bruteforce`
- **Finalización verificada:** código de salida `0`, `Scan completed` presente, duración 762.2 s
- **Resultado:** 0 hallazgo(s) — critical: 0, high: 0, medium: 0

### Comando ejecutado

```
docker exec nuclei-initial-assessment nuclei -u http://backend:8000 -severity medium,high,critical -t /work/backend.templates.txt -pt http -duc -dut -ni -nh -no-stdin -dr -nc -or -ot -rl 4 -c 1 -bs 1 -pc 1 -jsc 1 -tlc 1 -timeout 5 -retries 0 -mhe 10 -max-time 30m -stats -si 10 -vv -rsr 1048576 -jle /work/raw/backend.jsonl -tlog /work/raw/backend.trace.jsonl -elog /work/raw/backend.errors.txt
```

### Hallazgos

Sin hallazgos para las plantillas y severidades ejecutadas.

### Errores registrados

```
{"template":"/root/nuclei-templates/http/misconfiguration/microsoft/anonymous-distribution-point-sccm.yaml","type":"http","input":"http://backend:80/SMS_DP_SMSPKG$/Datalib","address":"backend:80","error":"port closed or filtered","kind":"network-permanent-error","attrs":{}}
{"template":"/root/nuclei-templates/http/misconfiguration/apachespark-ui-exposed.yaml","type":"http","input":"http://backend:4040/jobs/","address":"backend:4040","error":"port closed or filtered","kind":"network-permanent-error","attrs":{}}
```


### Notas de alcance y limitaciones

- Se ejecutaron únicamente plantillas oficiales de Nuclei, con severidades `medium`, `high` y `critical`.
- No se realizaron pruebas autenticadas, fuzzing, fuerza bruta ni pruebas de denegación de servicio.
- Se limitó la tasa a 4 peticiones por segundo y se mantuvieron las protecciones de Fail2Ban activas y sin cambios; no se produjeron bloqueos durante la ejecución.
- No se siguieron redirecciones HTTP ni se enviaron datos de explotación.
- Los resultados reflejan exclusivamente lo observable en la fecha indicada; no sustituyen una revisión manual ni un análisis autenticado.
- Los archivos JSONL contienen la evidencia cruda de Nuclei y no incluyen cuerpos de petición/respuesta ni credenciales.

### Evidencia de ejecución

El proceso terminó con código `0` y el log de la ejecución conserva la línea de finalización de Nuclei. El detalle operativo está en `backend-nuclei-execution.txt` y los resultados en `backend-nuclei.jsonl`.

