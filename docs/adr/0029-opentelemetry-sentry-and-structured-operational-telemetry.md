# ADR 0029: OpenTelemetry, Sentry and structured operational telemetry

- Estado: aceptada
- Fecha: 2026-07-31
- Responsables: plataforma académica

## Contexto

Requests, servicios, eventos y workers necesitan correlación operativa sin
convertir telemetría en una copia de datos académicos o personales.

## Decisión

Sentry captura errores scrubbed con `send_default_pii=false`, sin bodies,
cookies, email, query de búsqueda, grading payload, Session Replay ni profiling.
OpenTelemetry estable 1.44.0 produce traces y metrics por OTLP; Python logs OTel
se rechaza porque sigue development. `structlog` emite JSON Lines con un
procesador central recursivo de redacción.

Las auto-instrumentaciones Django/Celery/Redis/Psycopg/Botocore publicadas como
`0.65b0` se rechazan por prerelease. Middleware y Task base manuales propagan
W3C Trace Context y contextvars. Route, task, queue, consumer, source type,
category y outcome usan allowlists; IDs y queries nunca son labels.

El profile local ejecuta Collector Contrib, Prometheus, Jaeger v2, Loki y
Grafana fijados por tag y digest, con puertos host loopback, anonymous Grafana
deshabilitado y datos locales limitados. No representa la topología productiva.

## Alternativas rechazadas

OTel Python logs, auto-instrumentations beta, `django-prometheus`, logging de
bodies, métricas por usuario/organización/query/URL, captura amplia de consola,
source-map upload local, request/response capture y Sentry Session Replay.

## Consecuencias

La instrumentación manual exige más pruebas, pero evita prereleases y controla
cardinalidad y privacidad. Sentry y OTel se muestrean separadamente para evitar
doble captura.
