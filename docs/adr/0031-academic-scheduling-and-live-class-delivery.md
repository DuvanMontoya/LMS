# ADR 0031: Academic scheduling and live class delivery

- Estado: aceptada
- Fecha: 2026-07-31
- Responsables: plataforma académica
- Nota: ADR 0032 modifica la decisión de despliegue, audiencia y progreso.

## Contexto

La plataforma ya posee cursos, releases, cohortes, matrículas release-pinned,
roles institucionales y autenticación browser session. No posee, sin embargo,
una fuente de verdad para calendario académico, ocurrencias de clase, sesiones
sincrónicas ni asistencia. `domain.integrations` administra conexiones y
credenciales institucionales, pero no debe convertirse en propietario de
hechos académicos. Tampoco corresponde que `learning` mezcle progreso de
contenido asincrónico con infraestructura audiovisual.

La consulta oficial del 2026-07-31 confirmó que LiveKit firma tokens con el
API secret, expresa permisos mínimos mediante grants, firma webhooks con un
JWT que incluye el SHA-256 del cuerpo crudo y ofrece Room Service asíncrono.
FullCalendar 7 soporta React 19 y SSR, mueve los plugins estándar a subrutas de
`@fullcalendar/react`, exige `temporal-polyfill` y ya no incluye CSS implícito.
RFC 5545 define `DTSTART`, `RRULE`, `RECURRENCE-ID`, `COUNT`/`UNTIL` y el
alcance `THISANDFUTURE` que se aplica a las ediciones recurrentes.

## Decisión

### Ownership y dependencias

- `domain.scheduling` posee series académicas, ocurrencias materializadas de
  forma acotada, excepciones, sesiones en vivo, segmentos de asistencia y el
  ledger idempotente de webhooks LiveKit.
- PostgreSQL/Django son la única autoridad de fechas, estados, acceso y
  asistencia. LiveKit es el adaptador audiovisual y FullCalendar la vista
  interactiva; ninguno crea autoridad académica alternativa.
- Scheduling puede referenciar `organizations.Membership`, `courses.Course` y
  consultar el contrato público de matrícula efectiva de `learning`.
  `organizations`, `courses`, `publishing`, `content`, `learning` y
  `assessments` no importan scheduling.
- Los roles siguen exclusivamente en `domain.organizations`. Scheduling añade
  capacidades institucionales y aplica además reglas por objeto: host de la
  ocurrencia, curso, cohorte y matrícula efectiva.

### Recurrencia y ocurrencias

Una `AcademicEventSeries` guarda `DTSTART`, duración, zona IANA y una RRULE
RFC 5545 opcional. Toda recurrencia debe estar acotada por `COUNT` o `UNTIL` y
no puede superar 366 ocurrencias. El servicio valida la regla y materializa
solamente ese conjunto controlado dentro de una transacción. Cada
`AcademicEventOccurrence` conserva el inicio original como identidad estable,
el horario efectivo, estado y versión optimista.

Las operaciones declaran `occurrence`, `following` o `series`. Una excepción
no reescribe el identificador original. Mover una ocurrencia conserva su sala;
cancelarla impide nuevos tokens. El feed consulta únicamente el intervalo
visible con final exclusivo y nunca genera salas o tokens.

### Sesiones LiveKit y asistencia

Cada ocurrencia de clase en vivo tiene exactamente una `LiveSession`, creada
con un nombre de sala aleatorio, inmutable y no derivado del título. La sala
remota se crea al iniciar, de forma idempotente, mientras el servicio bloquea
la sesión local. La identidad del participante es `user:<uuid>` y los tokens
son de corta vida, limitados a una sala y con grants distintos para host,
administrador y estudiante.

El SDK queda encapsulado en un gateway. Django adapta sus operaciones
asíncronas sin `asyncio.run()` y cierra el cliente HTTP en cada operación. La
ausencia de configuración falla de forma explícita; no se inventan
credenciales. Egress queda deshabilitado por defecto y no produce controles ni
solicitudes hasta que configuración, almacenamiento y política estén
habilitados.

Los webhooks reciben el cuerpo crudo, validan firma y hash mediante
`WebhookReceiver`, y guardan el UUID de evento con unicidad. Los eventos de
participante abren y cierran segmentos append-only; reconectar crea otro
segmento. `room_finished` cierra segmentos abiertos y el estado local de forma
idempotente. Eventos desconocidos se registran sin alterar el dominio.

### Web y seguridad

Next.js conserva páginas como Server Components y aísla FullCalendar, lobby y
aula en Client Components específicos. El token se solicita solamente al
entrar y permanece en memoria. El aula usa una instancia estable de `Room`,
limpia tracks/listeners al desmontar y renderiza audio remoto. Los permisos de
cámara, micrófono, pantalla y `connect-src` WebSocket se habilitan sólo en la
ruta de aula; las demás rutas continúan denegándolos.

## Alternativas rechazadas

- Modelar horarios en `courses`, progreso en `learning` o secretos/hechos
  académicos en `integrations`.
- Crear otro proyecto Django/Next, un microservicio, otra base, autenticación o
  cliente HTTP.
- Usar LiveKit/FullCalendar como fuente de verdad, aceptar eventos del
  navegador como asistencia o persistir tokens.
- Expandir recurrencias ilimitadas, generar ocurrencias en FullCalendar o
  instalar `@fullcalendar/rrule`/`rrule` en el navegador.
- Instalar paquetes FullCalendar v6 separados, Scheduler/Premium, SDK RTC de
  Python, Agents, IA, transcripción o infraestructura móvil.
- Ejecutar `asyncio.run()` por request o desactivar CSRF fuera del webhook.

## Consecuencias

- Aparece `domain.scheduling` con migración propia, API `/api/v1/.../scheduling`
  y webhook global autenticado criptográficamente.
- Se añaden pins exactos de LiveKit, FullCalendar, temporal-polyfill y
  python-dateutil, con licencias permisivas y owners explícitos.
- Desarrollo dispone de LiveKit OSS local real; producción self-hosted,
  sesiones independientes y requisitos de progreso se definen en ADR 0032.
- Cambiar proveedor audiovisual afecta el gateway y el aula, no los eventos,
  permisos, asistencia ni contratos académicos persistidos.
