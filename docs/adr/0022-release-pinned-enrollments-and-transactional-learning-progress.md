# ADR 0022: Release-pinned enrollments and transactional learning progress

- Estado: aceptada
- Fecha: 2026-07-30
- Responsables: plataforma académica

## Contexto

`domain.publishing` ya produce releases completos, inmutables y verificables,
pero una publicación no expresa quién puede estudiar, durante qué ventana ni
qué versión debe continuar usando. La entrega necesita preservar la identidad
estable de una matrícula, el historial de asignaciones, el progreso por release
y una posición de lectura segura sin volver a consultar autoría mutable.

## Decisión

`domain.learning` es propietario exclusivo de cohortes, matrículas, asignaciones
de release, progreso y eventos. Una `CourseEnrollment` representa la relación
estable entre una membresía y un curso. Su
`EnrollmentReleaseAssignment` activa fija el `CourseRelease`; publicar otro
release no cambia matrículas existentes.

Una cohorte fija curso, release y ventana. Después de su primera matrícula el
release queda protegido por servicio, validación de modelo y trigger
PostgreSQL. Una matrícula de cohorte no admite upgrade individual. Una
matrícula individual activa o suspendida puede avanzar sólo a un release
posterior mediante operación explícita y con `expected_enrollment_version`; el
progreso nuevo empieza vacío y el anterior queda histórico.

`CourseProgress` pertenece uno a uno a una asignación y usa basis points,
contadores derivados y `lock_version`. Completar/reabrir bloquea filas con
`select_for_update(of=("self",))`, compara `expected_progress_version`,
recalcula desde `UnitProgress` y emite eventos una sola vez. Un conflicto
devuelve `409 learning_progress_conflict`. Guardar posición valida unit/node
contra el snapshot, aplica last-write-wins y no incrementa la versión ni genera
un evento por scroll.

El acceso del estudiante exige simultáneamente usuario propio, membresía activa,
matrícula no revocada, estado activo, ventana vigente, publicación activa,
asignación corriente y release íntegro. `course.published.view` queda como
preview institucional y no concede delivery al learner. Staff y superuser no
simulan una matrícula; el bypass de superuser se limita a administración.

`LearningEvent` es append-only por modelo y triggers `BEFORE UPDATE OR DELETE`.
Los lectores de learning consumen únicamente snapshots de publishing. Courses,
content y publishing no importan learning.

## Alternativas rechazadas

- Guardar el release actual directamente en progreso: pierde historial de
  upgrades y mezcla métricas.
- Mover matrículas automáticamente al release más reciente: rompe continuidad
  y reproducibilidad.
- Copiar módulos, unidades o documentos a learning: duplica autoridades.
- Calcular autorización en React o almacenar permisos/progreso en browser
  storage: no es una frontera de seguridad.
- Eventos por cada posición de scroll: genera volumen sin valor institucional.
- Señales o tareas asíncronas para contadores: introducen orden no determinista
  en una operación que debe cerrar en la misma transacción.

## Consecuencias

La publicación y la entrega quedan desacopladas; el historial puede crecer, por
lo que los índices y la paginación son obligatorios. El criterio de curso
completado es provisional: todas las unidades del release están completas; una
fase futura de evaluaciones podrá añadir requisitos sin reescribir este
historial. Releases y eventos no se corrigen físicamente; los errores se
resuelven con una nueva asignación o un nuevo evento.

## Evidencia

Migraciones `learning.0001`–`0003`, pruebas `TransactionTestCase` sobre
PostgreSQL 18.4, OpenAPI sin warnings, cliente TypeScript sin drift y Playwright
aislado con axe y viewport de 390 px.
