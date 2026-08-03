# Scheduling and live classes

## Propiedad y flujo

`domain.scheduling` es el único propietario de series, ocurrencias,
`LiveSession`, asistencia y eventos de webhook. `Course` aporta identidad
académica; el contrato público `domain.learning.contracts` aporta matrícula
efectiva. Ningún módulo previo importa scheduling y ningún estado audiovisual
se copia a cursos, releases, intentos, `User`, browser storage o Redis.

```mermaid
flowchart LR
  O["organizations: roles y capacidades"] --> S["scheduling: series y ocurrencias"]
  C["courses: identidad del curso"] --> S
  L["learning: matrícula efectiva"] --> S
  S --> P[("PostgreSQL: autoridad")]
  S --> G["LiveKitGateway"]
  G --> K["LiveKit: transporte audiovisual"]
  K --> W["Webhook firmado"]
  W --> S
  S --> A["API OpenAPI"]
  A --> F["FullCalendar 7"]
  A --> R["Aula React + RoomContext"]
```

## Invariantes

- La recurrencia acepta sólo `DAILY`, `WEEKLY`, `MONTHLY` y `YEARLY`, exige
  exactamente `COUNT` o `UNTIL` y materializa máximo 366 ocurrencias UTC desde
  una zona IANA.
- `original_starts_at` conserva la identidad de la ocurrencia. Reprogramar no
  cambia la sala; cada escritura usa `lock_version` y alcance `occurrence`,
  `following` o `series`.
- La sala es aleatoria, inmutable y se crea remotamente sólo cuando un host
  autorizado inicia. El feed jamás incluye nombre de sala ni token.
- El token tiene identidad seudónima `user:<uuid>`, TTL de cinco minutos por
  defecto, una sola sala y grants mínimos. Estudiantes no comparten pantalla;
  hosts y administradores pueden moderar.
- El webhook es el único origen de asistencia: valida JWT y hash del cuerpo
  crudo, deduplica por UUID y conserva segmentos múltiples por reconexión.
- Los errores del proveedor retornan códigos explícitos `502/503`; no hay
  fallback, credenciales ficticias ni estado optimista que suplante LiveKit.

## Contratos web

- `/organizaciones/<slug>/calendario` carga el intervalo visible, aborta la
  solicitud anterior al navegar y usa CSS/tema explícito de FullCalendar 7.
- `/organizaciones/<slug>/clases/<sessionId>` y la actividad inmersiva
  `/organizaciones/<slug>/aprender/<curso>/actividades/<activityId>` reciben
  permisos de cámara, micrófono y captura de pantalla. El token se pide al
  confirmar entrada y vive sólo en memoria.
- `Room` se instancia una vez por conexión, se desconecta al desmontar y
  LiveKit maneja reconexión de transporte. La pantalla programada refresca su
  estado sin convertir el navegador en autoridad.

## Grabación privada

- ADR 0040 gobierna Egress. La composición `screen_share` usa una plantilla
  técnica pública, sin sesión del LMS, que sólo renderiza la pantalla
  compartida y el audio de la sala.
- La política publicada define modo, composición y resolución predeterminada;
  `LiveSession` conserva la composición y resolución realmente ejecutadas.
- Los archivos locales permanecen en el volumen privado de desarrollo. No hay
  URL pública ni contrato de entrega hasta definir almacenamiento cifrado,
  retención y autorización institucional para producción.

## Límites deliberados

No se instalaron FullCalendar Premium/Scheduler, RRULE en el navegador, SDK RTC
Python, Agents, IA, transcripción, aplicación móvil ni otro proveedor. Egress
está habilitado únicamente en desarrollo local con salida privada; no se
considera listo para producción hasta implementar almacenamiento, retención,
privacidad y acceso autorizados.
