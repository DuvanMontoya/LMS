# LiveKit deployment and incidents

## Alcance actual

LiveKit OSS se ejecuta autohospedado en desarrollo local. Este runbook no
autoriza desplegar ni modificar VPS, DNS, SSH o firewall. La futura operación
pública se abre como una fase separada por decisión del usuario.

## Inicio y smoke local

```powershell
pnpm infra:init
pnpm livekit:up
pnpm dev:start
pnpm livekit:smoke
pnpm livekit:status
```

La web queda en `http://localhost:3000`, Django en `127.0.0.1:8010` y LiveKit
en `ws://127.0.0.1:7880`. El backend escucha `0.0.0.0:8010` sólo para que el
contenedor entregue el webhook mediante `host.docker.internal`; el puerto
público del navegador continúa siendo 3000. Las claves aleatorias viven sólo
en `infrastructure/local/.env`, ignorado por Git.

## Configuración

Backend (secretos sólo en el gestor del entorno):

```text
LIVEKIT_ENABLED=true
LIVEKIT_URL=wss://<livekit-public-host>
LIVEKIT_API_KEY=<secret reference>
LIVEKIT_API_SECRET=<secret reference>
LIVEKIT_TOKEN_TTL_SECONDS=300
LIVEKIT_JOIN_BEFORE_START_SECONDS=900
LIVEKIT_JOIN_AFTER_END_SECONDS=300
LIVEKIT_EGRESS_ENABLED=false
```

En una fase pública futura, `NEXT_PUBLIC_LIVEKIT_URL` debe contener el mismo origen WSS, sin
credenciales. Sólo sirve para el `connect-src` de la ruta de aula. Publicar el
webhook HTTPS `POST /api/v1/livekit/webhook/` en LiveKit con la misma
API key firmante. El endpoint exige `application/webhook+json`, cuerpo crudo y
`Authorization` válido.

## Preflight y smoke

1. Ejecutar `pnpm scheduling:check`, `pnpm scheduling:migrations`,
   `pnpm scheduling:test`, `pnpm web:build` y `pnpm scheduling:e2e`.
2. Primero en localhost, y después en un staging autorizado, crear una clase próxima, iniciar con profesor y entrar con un
   estudiante matriculado desde dos navegadores reales HTTPS.
3. Probar cámara, micrófono, pantalla sólo para host, audio remoto, salida,
   reconexión y expulsión. Confirmar que el estudiante no obtiene pantalla ni
   moderación.
4. En LiveKit enviar un webhook de prueba; confirmar HTTP 200, ledger procesado
   y que un evento duplicado no crea otro segmento.
5. Finalizar la sala y comprobar duración agregada sin borrar segmentos.

## Diagnóstico

- `503 livekit_unavailable`: feature flag apagado o configuración ausente.
- `502 livekit_rejected`: revisar salud/cuota del proyecto, DNS/WSS y logs por
  request ID; nunca registrar token, secret o cuerpo completo.
- Webhook 401: comprobar API key firmante, proxy que preserve cuerpo crudo,
  `Authorization` y que el ID opaco `EV_…` cabe en `event_id`. Webhook 500 deja
  el ledger `failed` para reintento seguro.
- Sin cámara/micrófono: confirmar que la URL es exactamente `/clases/<uuid>`,
  HTTPS, `Permissions-Policy` de esa respuesta y permiso del navegador.
- Agenda vacía: validar rango menor de 93 días, organización, curso y matrícula
  efectiva; no crear fixtures en producción.

## Rollback

1. Poner `LIVEKIT_ENABLED=false`: impide nuevos tokens y salas sin borrar agenda
   ni asistencia.
2. Retirar temporalmente el enlace de navegación si la degradación es visual;
   mantener API y tablas para auditoría.
3. No revertir la migración después de recibir webhooks/asistencia. Una retirada
   posterior requiere migración de datos y ADR.
4. Cerrar salas activas desde LiveKit sólo con autorización operativa. El
   estado se reconcilia por webhook; si el proveedor no entrega el evento,
   documentar la intervención y ejecutar una reparación de dominio aprobada.
