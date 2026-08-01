# Deliveries terminales de eventos

## Síntomas
`pnpm events:dead` lista deliveries en `dead`.

## Impacto
Un consumidor no materializó su efecto, sin revertir el cambio de negocio.

## Diagnóstico
Correlaciona event ID, consumer, request/trace ID y `last_error_code`; no extraigas payload a tickets.

## Comandos seguros
`pnpm events:dead`; `pnpm observability:traces`; `pnpm observability:logs`.

## Mitigación
Corrige primero la causa y limita el rango por organización, tipo y consumer.

## Recuperación
Solicita replay con operador UUID, razón explícita y consumer registrado.

## Verificación
El replay termina y deja un solo efecto idempotente.

## Escalamiento
Escala si hay filtración, corrupción o más de 100 000 eventos candidatos.

## Qué no hacer
No cambies `dead` a mano, no alteres payload y no omitas la razón.
