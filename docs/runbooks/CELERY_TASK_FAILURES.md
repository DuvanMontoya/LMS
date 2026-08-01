# Fallos de tareas Celery

## Síntomas
Workers unhealthy, tareas repetidas o colas sin consumo.

## Impacto
Eventos, indexado, email, grading o media pueden retrasarse.

## Diagnóstico
Usa `pnpm async:status`, spans por task ID y métricas de outcome con baja cardinalidad.

## Comandos seguros
`pnpm async:smoke`; `pnpm observability:traces`; `pnpm events:operational-check`.

## Mitigación
Recupera broker/worker y respeta leases e idempotencia.

## Recuperación
Agenda sólo trabajo vencido mediante los comandos de dominio.

## Verificación
Colas consumen, spans cierran y estados durables convergen.

## Escalamiento
Escala si hay poison task, loop de retry o pérdida de conexión PostgreSQL.

## Qué no hacer
No purgues Redis, no borres jobs y no reinicies sin observar leases.
