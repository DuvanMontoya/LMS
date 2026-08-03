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

LiveKit anuncia en local tanto la interfaz interna del contenedor como el
candidato loopback. El navegador usa los puertos publicados en `127.0.0.1` y
Egress usa la red de Compose. No fijar `rtc.node_ip: 127.0.0.1`: dentro del
contenedor de Egress ese candidato apunta al propio grabador, no al SFU.

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
LIVEKIT_EGRESS_TEMPLATE_URL=https://<web-public-host>/livekit/egress
LIVEKIT_EGRESS_CONNECT_URL=wss://<livekit-public-host>
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
6. Para grabación, probar `720p` y `1080p`; con composición `screen_share`,
   verificar con `ffprobe` las dimensiones reales y comprobar visualmente que
   el archivo contiene la pantalla y el audio de la sala, pero ninguna cámara.
   Extraer además un fotograma posterior al arranque: no aceptar como evidencia
   un MP4 que sólo muestre «Esperando una pantalla compartida». La señal
   `START_RECORDING` debe ocurrir después de que el vídeo remoto esté en
   reproducción.
   Confirmar primero que entrar a la sala no inicia Egress. Iniciar y detener
   manualmente dos segmentos con composiciones distintas; el estado actual debe
   coincidir en `LiveSession` y ambos registros deben permanecer separados en
   `LiveSessionRecording`.
7. Verificar que `screen_share` se rechaza sin pantalla y que cuadrícula/enfoque
   se rechazan sin cámara ni pantalla. El indicador `Grabando` debe aparecer a
   moderadores y participantes mientras LiveKit reporte la sala grabándose.
8. Abrir participantes como moderador y comprobar que el panel se superpone
   sólo bajo demanda. Silenciar debe mutear únicamente la pista de micrófono;
   restringir/restaurar medios debe respetar rol, política y chat; expulsar debe
   exigir confirmación. Un usuario ajeno a la sesión debe recibir rechazo sin
   que se invoque Room Service.
9. En desarrollo, comprobar `http://localhost:3000` y
   `http://127.0.0.1:3000`: Next debe escuchar en `0.0.0.0` para que ambos
   nombres lleguen al mismo proceso. Las cookies siguen siendo propias de cada
   hostname y nunca se copian para simular una sesión.

## Diagnóstico

- `503 livekit_unavailable`: feature flag apagado o configuración ausente.
- `502 livekit_rejected`: revisar salud/cuota del proyecto, DNS/WSS y logs por
  request ID; nunca registrar token, secret o cuerpo completo.
- Webhook 401: comprobar API key firmante, proxy que preserve cuerpo crudo,
  `Authorization` y que el ID opaco `EV_…` cabe en `event_id`. Webhook 500 deja
  el ledger `failed` para reintento seguro.
- Sin cámara/micrófono/pantalla: confirmar si la sesión se abrió desde
  `/clases/<uuid>` o desde la actividad inmersiva
  `/organizaciones/<slug>/aprender/<curso>/actividades/<uuid>`, HTTPS,
  `Permissions-Policy` de esa respuesta y permiso del navegador. Ambas rutas
  deben declarar `camera=(self)`, `microphone=(self)` y
  `display-capture=(self)`; un grant LiveKit correcto no sustituye la política
  HTTP del documento que invoca `getUserMedia` o `getDisplayMedia`.
- Agenda vacía: validar rango menor de 93 días, organización, curso y matrícula
  efectiva; no crear fixtures en producción.
- Grabación `screen_share` rechazada: confirmar que Egress puede resolver
  `LIVEKIT_EGRESS_TEMPLATE_URL`, que esa URL responde sin redirigir a login y
  que `LIVEKIT_EGRESS_CONNECT_URL` coincide con el origen WSS/WS accesible desde
  el contenedor. No cambiar a cuadrícula para ocultar el error.
- Grabación sin fuente visual: publicar primero la cámara o la pantalla según
  la composición. No eliminar la validación ni contar placeholders como pistas.
- MP4 con pantalla de espera pese a existir una pantalla publicada: confirmar
  que la plantilla espera `playing` antes de `START_RECORDING`; conectarse a la
  sala no prueba que el vídeo ya esté adjunto y decodificándose.
- Volumen de salida no escribible: comprobar que `livekit-egress-init` terminó
  correctamente y que `/out` pertenece a UID `1001`, GID `0`, modo `770`. Egress
  permanece sin privilegios; no ejecutarlo como root para ocultar permisos.
- Egress queda en `STARTING` sin señal: revisar el log del grabador y los
  candidatos ICE de LiveKit. El servidor local debe anunciar interfaz interna
  y loopback; un único candidato `127.0.0.1` permite el navegador del host pero
  impide que el contenedor Egress establezca el PeerConnection.

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
