# Operación

## Salud y servicios locales

```powershell
pnpm infra:status
pnpm api:health
pnpm async:status
pnpm media:status
pnpm observability:status
```

La liveness de Django no depende de servicios externos; readiness confirma PostgreSQL y la caché configurada. No exponga los detalles de una dependencia fallida en la respuesta de salud.

## Colas y trabajo duradero

Redis es broker, pero los jobs de calificación, recálculo, media, eventos, búsqueda, correo e integraciones conservan su estado durable en PostgreSQL. Reiniciar un worker no autoriza a reescribir el historial: use el servicio o comando específico y consulte registros antes de repetir un trabajo.

| Situación | Runbook |
| --- | --- |
| Fallos de Celery | `docs/runbooks/CELERY_TASK_FAILURES.md` |
| Eventos pendientes o fallidos | `docs/runbooks/OUTBOX_BACKLOG.md` y `DEAD_EVENT_DELIVERIES.md` |
| Correo | `docs/runbooks/EMAIL_DELIVERY_FAILURES.md` y `RESEND_SMTP.md` |
| Observabilidad | `docs/runbooks/OTEL_COLLECTOR_DOWN.md`, `PROMETHEUS_ALERTS.md`, `SENTRY_TRIAGE.md` |
| Búsqueda | `docs/runbooks/SEARCH_INDEX_LAG.md` y `SEARCH_REBUILD_FAILURE.md` |
| Clases LiveKit | `docs/runbooks/LIVEKIT_DEPLOYMENT_AND_INCIDENTS.md` |

## Datos y recuperación

Revise backups, restauración y cadena de releases antes de operar datos. No use comandos de reset local en producción: `pnpm storage:reset-local` está limitado a buckets locales y el resto de la operación conserva los hechos académicos históricos.
