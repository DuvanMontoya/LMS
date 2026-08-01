# Triage de Sentry

## Síntomas
Evento de error nuevo o incremento de fallos no esperados.

## Impacto
Puede existir regresión de usuario; Sentry no es fuente de estado de dominio.

## Diagnóstico
Usa release, entorno, route template, trace/request ID y user UUID permitido.

## Comandos seguros
`pnpm api:test`; `pnpm web:test`; reproduce con transport de prueba.

## Mitigación
Desactiva el DSN si detectas PII y conserva evidencia mínima.

## Recuperación
Corrige, valida scrubbing y verifica que 404/validation no se reporten.

## Verificación
No hay body, cookies, email, query, signed URL ni duplicados.

## Escalamiento
Escala inmediatamente una filtración o evento de seguridad.

## Qué no hacer
No habilites `send_default_pii`, Session Replay ni captura de cuerpos.
