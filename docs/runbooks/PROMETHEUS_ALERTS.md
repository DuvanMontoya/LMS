# Alertas Prometheus

## Síntomas
Una regla queda pending/firing en el stack local o CI.

## Impacto
Indica degradación potencial; confirma la fuente antes de actuar.

## Diagnóstico
Consulta reglas, targets y labels allowlisted, nunca IDs ni queries.

## Comandos seguros
`pnpm observability:metrics`; `pnpm events:operational-check`.

## Mitigación
Atiende el runbook específico de outbox, search, email o worker.

## Recuperación
Corrige la causa y espera la ventana de la regla sin silenciarla globalmente.

## Verificación
Target up, regla loaded y métrica de outcome vuelve al rango observado.

## Escalamiento
Escala alertas simultáneas o pérdida de todas las señales.

## Qué no hacer
No añadas labels de usuario/organización/query ni inventes SLA productivo.
