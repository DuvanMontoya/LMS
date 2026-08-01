# Fallo de reconstrucción de búsqueda

## Síntomas
La generación nueva queda failed y el job registra `rebuild_failed`.

## Impacto
La generación previa sigue sirviendo; las novedades no entran aún.

## Diagnóstico
Comprueba DB, `pg_trgm`, espacio, worker y código de fallo sin registrar queries.

## Comandos seguros
`pnpm api:database:check`; `pnpm discovery:test`; `pnpm discovery:status`.

## Mitigación
Mantén active la generación anterior y corrige la fuente o infraestructura.

## Recuperación
Inicia un único rebuild shadow y espera a su switch atómico.

## Verificación
Conteo, búsquedas es/en, typo y aislamiento A/B pasan.

## Escalamiento
Escala ante fallo de índice, extensión ausente o exposición no autorizada.

## Qué no hacer
No borres la generación active ni cambies status manualmente.
