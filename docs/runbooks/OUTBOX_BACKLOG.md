# Backlog del outbox

## Síntomas
`platform_operational_check` reporta `outbox_lag_elevated` o aumenta `lms_outbox_deliveries_total{outcome="failed"}`.

## Impacto
El cambio de negocio persiste, pero búsqueda, avisos o correo pueden quedar retrasados.

## Diagnóstico
Ejecuta `pnpm events:dead`, revisa el estado del worker `events` y consulta sólo IDs, consumer, intentos y códigos seguros.

## Comandos seguros
`pnpm async:status`; `pnpm events:dispatch`; `pnpm events:operational-check`.

## Mitigación
Recupera Redis/worker y agenda únicamente deliveries vencidos.

## Recuperación
Confirma que pending/failed descienden y que completed no se reejecuta.

## Verificación
`pnpm events:smoke` y `pnpm events:operational-check` deben pasar.

## Escalamiento
Escala si la antigüedad supera 15 minutos o el mismo consumer falla cinco veces.

## Qué no hacer
No edites eventos, no borres filas y no ejecutes replay global automático.
