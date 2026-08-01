# Collector OpenTelemetry no disponible

## Síntomas
Faltan traces/métricas o el collector está unhealthy.

## Impacto
Se reduce visibilidad; PostgreSQL y operaciones de negocio continúan autoritativos.

## Diagnóstico
Revisa health de Compose y configuración OTLP sin imprimir headers.

## Comandos seguros
`pnpm observability:status`; `pnpm observability:validate`; `pnpm observability:smoke`.

## Mitigación
Reinicia sólo el collector local y conserva los servicios de aplicación.

## Recuperación
Confirma export a Prometheus/Jaeger y lectura de logs por Loki.

## Verificación
`pnpm observability:metrics`, `:traces` y `:logs` pasan.

## Escalamiento
Escala ante saturación, pérdida prolongada o configuración productiva afectada.

## Qué no hacer
No bloquees requests por telemetría ni registres payloads para compensar.
