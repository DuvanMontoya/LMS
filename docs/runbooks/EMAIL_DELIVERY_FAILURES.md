# Fallos de entrega de correo

## Síntomas
EmailDelivery queda failed/dead o crece la métrica de fallos.

## Impacto
El aviso interno permanece; el canal correo puede retrasarse o no entregarse.

## Diagnóstico
Revisa ID, template, intentos y código seguro; no imprimas email ni cuerpo.

## Comandos seguros
`pnpm notifications:email-smoke`; `pnpm notifications:retry`; `pnpm async:status`.

## Mitigación
Recupera SMTP y permite backoff; un destinatario no verificado es terminal.

## Recuperación
Reintenta sólo failed/dead desde la API operacional autorizada.

## Verificación
Un único message ID queda sent y la bandeja no se duplica.

## Escalamiento
Escala ante rebotes masivos, credenciales comprometidas o PII en telemetría.

## Qué no hacer
No cambies destinatario, no reenvíes a otra cuenta y no registres el cuerpo.
