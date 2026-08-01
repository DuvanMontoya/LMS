# LiveKit deployment and incidents

## Recomendación de despliegue

Para el primer despliegue se recomienda LiveKit Cloud: el repositorio no posee
todavía operación WebRTC multi-región, TURN, certificados, firewall UDP,
capacidad ni on-call audiovisual. El adaptador conserva la opción self-hosted
sin migrar datos. Elegir self-hosting exige otro ADR con región/residencia,
SLO, capacidad, TLS público, TURN/TLS, puertos UDP/TCP, observabilidad, upgrades
y recuperación ensayada.

## Configuración

Backend (secretos sólo en el gestor del entorno):

```text
LIVEKIT_ENABLED=true
LIVEKIT_URL=wss://<project>.livekit.cloud
LIVEKIT_API_KEY=<secret reference>
LIVEKIT_API_SECRET=<secret reference>
LIVEKIT_TOKEN_TTL_SECONDS=300
LIVEKIT_JOIN_BEFORE_START_SECONDS=900
LIVEKIT_JOIN_AFTER_END_SECONDS=300
LIVEKIT_EGRESS_ENABLED=false
```

Frontend: `NEXT_PUBLIC_LIVEKIT_URL` debe contener el mismo origen WSS, sin
credenciales. Sólo sirve para el `connect-src` de la ruta de aula. Publicar el
webhook HTTPS `POST /api/v1/livekit/webhook/` en la consola LiveKit con la misma
API key firmante. El endpoint exige `application/webhook+json`, cuerpo crudo y
`Authorization` válido.

## Preflight y smoke

1. Ejecutar `pnpm scheduling:check`, `pnpm scheduling:migrations`,
   `pnpm scheduling:test`, `pnpm web:build` y `pnpm scheduling:e2e`.
2. En staging crear una clase próxima, iniciar con profesor y entrar con un
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
- Webhook 401: comprobar API key firmante, proxy que preserve cuerpo crudo y
  `Authorization`. Webhook 500 deja el ledger `failed` para reintento seguro.
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
