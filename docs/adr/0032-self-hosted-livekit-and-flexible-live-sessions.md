# ADR 0032: Self-hosted LiveKit and flexible live sessions

- Estado: aceptada
- Fecha: 2026-08-01
- Responsables: plataforma académica
- Modifica: ADR 0031 en despliegue, audiencia y progreso

## Contexto

La decisión de producto es operar LiveKit OSS en infraestructura propia, sin
contratar LiveKit Cloud. Además, una sesión sincrónica puede ser parte de un
curso o una tutoría/clase independiente. Algunas clases de curso son requisitos
de avance; otras son informativas. Una mera conexión WebSocket no demuestra
asistencia académica.

El 2026-08-01 se consultó la documentación oficial de LiveKit sobre
self-hosting, despliegue en VM, puertos/firewall, webhooks y Egress. LiveKit OSS
soporta audio, video, datos y webhooks; Egress requiere un servicio separado.
Producción necesita TLS público de una CA confiable, TURN, DNS y puertos de
medios. El generador oficial produce Caddy, Compose, configuración LiveKit,
Redis e inicialización de VM.

El despliegue remoto no forma parte de esta decisión de implementación local.
El usuario lo realizará en una fase posterior; este ADR no autoriza cambios en
VPS, DNS, SSH, firewall ni servicios públicos.

## Decisión

### Operación LiveKit

- Desarrollo usa `livekit/livekit-server:v1.13.1`, fijado por digest, en el
  perfil Compose `live`. Escucha sólo en loopback: signal/API 7880, RTC/TCP
  7881 y RTC/UDP mux 7882. Las claves se generan en el `.env` ignorado.
- Una futura producción usará una instalación LiveKit OSS independiente con
  TLS público, TURN y Redis. La topología exacta, nombres DNS, capacidad y
  ejecución quedan aplazados hasta la fase de despliegue del usuario.
- PostgreSQL continúa siendo autoridad académica. Redis de LiveKit coordina el
  transporte; no almacena progreso, asistencia ni permisos del LMS.
- Egress, Ingress, Agents, transcripción y grabación quedan deshabilitados. Una
  futura grabación exige ADR de consentimiento, retención, cifrado,
  almacenamiento y acceso.
- LiveKit OSS no cobra licencia ni minutos, pero el VPS, ancho de banda,
  respaldos y operación no son costo cero.

### Tipos de sesión y audiencia

- `AcademicEventSeries.course` es opcional.
- Una sesión de curso deriva audiencia learner exclusivamente de matrículas
  efectivas; no acepta una lista paralela de invitados.
- Una sesión independiente exige al menos una membresía activa invitada y sólo
  es visible/usable por host, administradores y participantes explícitos.
- Ambas variantes conservan salas aleatorias, tokens por sala, webhooks
  firmados y aislamiento por organización.

### Progreso verificable

- Una clase de curso puede declarar `counts_toward_progress` y un umbral de
  asistencia en minutos no mayor que su duración. Una sesión independiente no
  puede contar para un curso.
- `learning` conserva ownership del progreso mediante requisitos externos
  genéricos y sus completitudes. Scheduling sólo usa el contrato público
  `register/complete/deactivate_live_session_requirement`; learning no importa
  scheduling.
- Cada ocurrencia requerida suma una actividad al denominador del progreso.
  Sólo segmentos de asistencia cerrados, firmados por webhook y agregados por
  usuario pueden completar el requisito. Reconexiones suman duración sin
  duplicar la completitud.
- Cancelar una ocurrencia desactiva su requisito y recalcula el avance. No se
  borra asistencia ni historial.

## Consecuencias

- Migraciones `learning.0004`, `scheduling.0002` y `scheduling.0003` amplían
  los contratos sin cambiar identidad, releases, matrículas ni snapshots. La
  última conserva como texto limitado el identificador opaco firmado `EV_…`.
- El calendario permite elegir curso o sesión independiente, invitados y
  progreso/umbral. El progreso combina unidades y clases requeridas.
- El despliegue remoto permanece fuera de alcance. Desarrollo prueba Room
  Service, WebRTC, webhooks, asistencia y progreso contra el servidor local
  real antes de abrir cualquier fase de producción.

## Fuentes oficiales consultadas

- LiveKit, Self-hosting overview, 2026-08-01:
  https://docs.livekit.io/transport/self-hosting/
- LiveKit, Deploying LiveKit, 2026-08-01:
  https://docs.livekit.io/transport/self-hosting/deployment/
- LiveKit, Virtual machines, 2026-08-01:
  https://docs.livekit.io/transport/self-hosting/vm/
- LiveKit, Ports and firewall, 2026-08-01:
  https://docs.livekit.io/transport/self-hosting/ports-firewall/
- LiveKit, Webhooks and events, 2026-08-01:
  https://docs.livekit.io/intro/basics/rooms-participants-tracks/webhooks-events/
- LiveKit, Egress service, 2026-08-01:
  https://docs.livekit.io/transport/self-hosting/egress/
