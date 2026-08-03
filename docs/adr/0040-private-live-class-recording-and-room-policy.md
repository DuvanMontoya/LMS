# ADR 0040: Private live-class recording and room policy

- Estado: aceptada
- Fecha: 2026-08-02; ampliada 2026-08-03
- Responsables: plataforma académica
- Modifica: ADR 0032 en grabación y configuración de salas

## Contexto

La actividad curricular `live_class` sólo conservaba asistencia mínima. Audio,
video, chat, cupo y ventana de acceso dependían de valores globales, por lo que
la interfaz de autoría no describía la experiencia real de la sala. Además,
ADR 0032 aplazó grabación hasta definir consentimiento, retención,
almacenamiento y acceso.

El 2026-08-02 se consultaron la documentación y los repositorios oficiales de
LiveKit sobre Room Service, permisos de participantes, text streams, Room
Composite Egress, salidas y operación self-hosted de Egress. El chat de LiveKit
es tiempo real y no ofrece persistencia histórica. La grabación exige un
servicio Egress separado que comparte Redis con LiveKit Server.

## Decisión

- `LiveClassActivityBinding` es la política de sala reutilizable de una
  actividad: modo interactivo/seminario, audio, video, pantalla, chat, cupo,
  cierres, ventana de entrada, asistencia y grabación.
- La política se incorpora al snapshot inmutable de publicación. La
  programación concreta sigue perteneciendo a `AcademicEventSeries` y enlaza
  grupo, release, docente, fecha y recurrencia; no se introduce un calendario
  paralelo en cursos.
- El backend aplica la política al crear la sala y emitir cada token. La UI no
  puede elevar permisos concedidos por Django.
- Grabación queda desactivada por defecto. Sus modos son manual o automática;
  sus composiciones son sólo pantalla compartida, docente activo o cuadrícula.
  Para una política nueva, sólo pantalla es la composición recomendada y
  `1080p` la resolución predeterminada; el moderador puede escoger `720p` antes
  de iniciar una grabación manual.
- La composición sólo pantalla usa una plantilla Room Composite propia que
  suscribe exclusivamente pistas `ScreenShare` y usa `RoomAudioRenderer` para
  conservar el audio remoto. Así excluye cámaras sin perder las voces de la
  sala; un Track Egress crudo no satisface ese contrato porque exporta una sola
  pista.
- La resolución y composición realmente solicitadas se copian a `LiveSession`
  al iniciar Egress. No se infieren posteriormente desde la política, que puede
  cambiar para futuras publicaciones.
- Toda persona debe reconocer el aviso antes de recibir un token de una sala
  grabable. `LiveRecordingAcknowledgement` conserva ese reconocimiento por
  usuario y sesión, sin borrado físico.
- Desarrollo ejecuta `livekit/egress:v1.12.0`, fijado por digest, conectado al
  mismo Redis autenticado y a LiveKit Server. Los MP4 se escriben en un volumen
  privado `livekit_recordings`; no se exponen mediante URL pública.
- En Compose, LiveKit recopila el candidato loopback y su interfaz interna. El
  primero mantiene la conexión del navegador mediante puertos publicados; el
  segundo permite al Chrome headless de Egress establecer WebRTC con el SFU.
  No se fija `node_ip` a loopback porque ese valor cambia de significado dentro
  del contenedor grabador.
- PostgreSQL conserva estado e identificadores de Egress, pero no rutas de
  objetos, credenciales ni enlaces firmados. Los webhooks firmados actualizan
  el estado de la grabación.
- El chat se marca explícitamente como efímero. Persistirlo requeriría otra
  decisión de privacidad y un modelo académico propio; no se simula historial.
- Para producción, la salida debe migrar a almacenamiento privado cifrado con
  política institucional de retención y entrega autorizada. El volumen local
  no es una estrategia de producción.
- `/livekit/egress` es una superficie técnica pública para el Chrome headless
  de Egress, no una página del LMS. Niega cámara, micrófono y captura, usa
  `no-store` y `no-referrer`, elimina de la barra la consulta con token una vez
  leída y restringe `connect-src` al origen LiveKit configurado. El token
  efímero de grabador no se persiste ni se registra desde la aplicación.

## Consecuencias

- Configurar una clase en vivo ya no es un campo de título: la autoría produce
  una política verificable que llega a tokens, Room Service y Egress.
- La grabación no puede comenzar si el entorno no tiene Egress habilitado, si
  la actividad la deshabilita o si el actor no modera la sesión.
- Finalizar una sala intenta detener primero una grabación activa y conserva el
  resultado operativo aunque Egress falle.
- No se incluyen transcripción, subtítulos automáticos ni almacenamiento de
  chat: requieren proveedores, privacidad y contratos no presentes.

## Fuentes oficiales consultadas

- LiveKit, Rooms, participants, and tracks, 2026-08-02:
  https://docs.livekit.io/intro/basics/rooms-participants-tracks/rooms/
- LiveKit, Room service API, 2026-08-02:
  https://docs.livekit.io/reference/other/roomservice-api/
- LiveKit, Participant management, 2026-08-02:
  https://docs.livekit.io/intro/basics/rooms-participants-tracks/participants/
- LiveKit, Text streams, 2026-08-02:
  https://docs.livekit.io/transport/data/text-streams/
- LiveKit, Room composite Egress, 2026-08-02:
  https://docs.livekit.io/home/egress/web/
- LiveKit, Egress outputs, 2026-08-02:
  https://docs.livekit.io/transport/media/ingress-egress/egress/outputs/
- LiveKit Egress, configuración self-hosted, 2026-08-02:
  https://github.com/livekit/egress
- LiveKit, Custom recording templates, 2026-08-03:
  https://docs.livekit.io/transport/media/ingress-egress/egress/custom-template/
- LiveKit, Egress API encoding presets, 2026-08-03:
  https://docs.livekit.io/reference/other/egress/api/
- LiveKit, RoomAudioRenderer, 2026-08-03:
  https://docs.livekit.io/reference/components/react/component/roomaudiorenderer/
