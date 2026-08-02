# ADR 0035: Roster-synced course groups and historical enrollments

- Estado: aceptada
- Fecha: 2026-08-01
- Responsables: plataforma académica

## Contexto

La institución ya cuenta con una única pertenencia institucional (`Membership`),
roles institucionales históricos y un padrón reutilizable (`AcademicGroup`). Sin
embargo, enlazar este padrón con `LearningCohort` no produce matrículas, mientras
que `CourseEnrollment.cohort` mezcla la oferta actual con una asociación que
debería conservar traslados. También se copiaron ventanas de acceso por
matrícula, por lo que una corrección de la política del grupo no alcanza a las
personas que la heredan.

Esto contradice la expectativa operativa escolar: un grupo académico es un
padrón institucional y un grupo de curso es la oferta concreta de un curso y
release para una sección. La consulta del 2026-08-01 a OneRoster 1.2 confirmó la
distinción entre datos de personas, clases, matrículas y calificaciones, y que
los roster de clase se manejan como hechos propios. Se toma como modelo de
interoperabilidad, sin declarar conformidad ni implementar un proveedor
OneRoster. Fuente: https://standards.1edtech.org/oneroster/specifications/standards/v1p2
(consultada el 2026-08-01).

## Decisión

- `Membership` y `MembershipRoleAssignment` continúan siendo las únicas fuentes
  de pertenencia y permisos institucionales. Un perfil, `member_type`,
  `django.auth.Group`, una sesión o el navegador no concede roles, roster ni
  matrícula.
- `AcademicGroup` conserva el padrón reutilizable por año, nivel y sección. Sólo
  sus filas activas con `role=learner` son candidatas a sincronización; docentes
  y acompañantes no se matriculan por esa vía.
- `LearningCohort` se conserva como identidad y ruta API v1 por compatibilidad,
  pero el producto lo presenta como **Grupo de curso**. Fija organización,
  curso, release, política de ventana, padrón académico opcional y docentes
  asignados.
- La asociación vigente entre matrícula y grupo de curso deja de ser la FK
  autoritativa de `CourseEnrollment`. `EnrollmentCohortAssignment` conserva
  inicio, fin, actor, motivo y procedencia; PostgreSQL permite a lo sumo una
  asignación activa por matrícula. La FK `CourseEnrollment.cohort` queda como
  espejo temporal de lectura y migración v1, y ningún consumidor nuevo la usa
  para autorizar ni decidir el roster.
- `CohortStaffAssignment` asigna una membresía activa como
  `lead_instructor`, `instructor` o `assistant`. Owner y administrador conservan
  alcance institucional. Los docentes sólo pueden leer roster, progreso,
  evaluación, agenda o clases de grupos de curso con asignación activa. Author y
  reviewer no adquieren datos personales o de aprendizaje por su rol de autoría.
- La ventana del grupo de curso es una política compartida. Cada matrícula marca
  explícitamente si hereda la política o si tiene una excepción individual. Una
  modificación de la política afecta sólo las heredadas; nunca reescribe una
  excepción ni hechos de aprendizaje.
- Crear un grupo de curso con padrón y `roster_mode=synced` dirige a un preview
  explícito antes de cualquier efecto de roster. La confirmación, con versiones
  esperadas, crea o vincula
  matrículas de estudiantes, asigna el grupo y registra eventos append-only. Al
  retirar un estudiante, cierra su asignación y, si el acceso nació de la
  sincronización, la suspende sin borrar progreso. Una matrícula convertida
  explícitamente en individual mantiene acceso.
- Un traslado entre grupos del mismo curso y release cierra y crea asignaciones,
  preservando la matrícula, release y progreso. Con otro release exige el flujo
  explícito de upgrade y preview: nunca migra progreso silenciosamente.
- Las cohortes existentes no adoptan sincronización automáticamente. El
  backfill conserva el acceso, registra `legacy_migration`, traduce ventanas
  iguales a herencia y distintas a excepción. La adopción de un padrón histórico
  requiere revisión, motivo y confirmación administrativa.

## Invariantes y seguridad

- Todas las referencias de roster, staff, matrícula y grupo de curso pertenecen
  a la misma organización; la asignación de grupo además coincide en curso y
  release efectivo.
- Las filas históricas no se eliminan físicamente. Triggers PostgreSQL rechazan
  `DELETE` y mutaciones de identidad/hechos ya cerrados; las correcciones se
  expresan mediante cierre y una nueva fila.
- Toda mutación de roster, staff, política o sincronización bloquea las filas
  pertinentes, exige `expected_version` y responde `409` ante concurrencia. Un
  preview nunca escribe.
- Las APIs de staff, roster y matrículas son paginadas y buscables del lado del
  servidor. No usan un selector limitado a 100 personas ni filtran una lista
  incompleta en el cliente.
- Assessments conserva el grupo de curso efectivo como snapshot de asignación.
  Scheduling/LiveKit verifican matrícula efectiva y asignación al grupo de curso
  para las series nuevas; la audiencia histórica sólo-curso permanece explícita
  como compatibilidad v1.

## Consecuencias

La lectura de compatibilidad v1 puede seguir exponiendo `cohort_id` durante la
migración, pero el nuevo contrato publica `course_group`, procedencia y modo de
ventana. Se actualizan policies, selectores, OpenAPI, cliente TypeScript y UI
para usar el historial. La eliminación final del espejo requiere una ADR de
retiro, inventario de consumidores y una migración posterior, no esta entrega.

No se añade una dependencia ni otro sistema de identidad. PostgreSQL sigue como
autoridad, y Redis/Celery no participan en decisiones de roster.

## Alternativas rechazadas

- Matricular implícitamente al enlazar cualquier grupo sin preview, versión ni
  auditoría: puede cambiar accesos históricos de forma silenciosa.
- Mantener `CourseEnrollment.cohort` como único estado: no representa traslados
  ni la procedencia de una baja.
- Copiar nuevamente fechas del grupo en cada matrícula: hace que las políticas
  compartidas sean imposibles de corregir de forma visible.
- Conceder al docente el alcance institucional de su rol: expone PII, progreso,
  calificaciones y clases de estudiantes no asignados.
- Crear grupos de curso, roles o enrolments en el navegador: duplica la fuente
  de verdad y evade las garantías transaccionales.
