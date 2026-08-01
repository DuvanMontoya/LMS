# Retraso del índice académico

## Síntomas
Contenido aprobado/autorizado no aparece o el job permanece pending/processing.

## Impacto
La búsqueda puede estar desactualizada; las lecturas académicas canónicas siguen disponibles.

## Diagnóstico
Revisa `/api/v1/platform/search-index/jobs/`, worker `discovery` y generación active.

## Comandos seguros
`pnpm discovery:status`; `pnpm async:status`; `pnpm discovery:smoke`.

## Mitigación
Recupera el worker y procesa el job; conserva la generación active.

## Recuperación
Si es necesario, ejecuta un rebuild shadow acotado por organización.

## Verificación
La nueva generación queda active y el learner sólo ve releases asignados.

## Escalamiento
Escala ante resultados cross-org, grading indexado o fallo repetido.

## Qué no hacer
No actives una generación incompleta ni consultes grading/respuestas.
