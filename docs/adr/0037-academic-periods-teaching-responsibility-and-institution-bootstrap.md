# ADR 0037: Academic periods, teaching responsibility and institution bootstrap

- Estado: aceptada
- Fecha: 2026-08-01
- Responsables: plataforma academica
- Amplia: ADR 0017, ADR 0018, ADR 0034 y ADR 0035; matizada por ADR 0038

## Contexto

Los grupos de curso carecen de periodo academico explicito. Un rol institucional
`instructor`, `author` o `reviewer` expresa elegibilidad, pero no responsabilidad
sobre una asignatura ni acceso operativo a un grupo. Ademas, el alta global
actual exige una cuenta owner ya verificada y crea su membresia dentro de la
transaccion, por lo que la institucion no tiene un estado `pending_activation`
ni un bootstrap basado en invitacion revocable.

La consulta del 2026-08-01 a OneRoster 1.2 confirmo la separacion entre
`AcademicSession`, `Course`, `Class`, `Enrollment`, `LineItem` y `Result`, y que
un roster de clase corresponde a personas y un periodo concreto. Se adopta esa
separacion como compatibilidad arquitectonica, sin implementar endpoints ni
declarar conformidad OneRoster. Fuente:
https://standards.1edtech.org/oneroster/specifications/standards/v1p2.

La consulta del mismo dia a CASE 1.1 confirmo que marcos, competencias y sus
asociaciones son referencias estructuradas. El LMS conserva sus propios
contratos y no declara conformidad CASE. Fuente:
https://standards.1edtech.org/case/.

## Decision

- `domain.learning` posee `AcademicPeriod`, jerarquico, fechado y acotado a una
  organizacion. Sus tipos iniciales son `school_year`, `term`, `semester`,
  `trimester`, `quarter` y `grading_period`. Un periodo hijo debe quedar dentro
  de su padre y no puede formar ciclos.
- Todo grupo de curso nuevo requiere periodo. Agenda curricular, instancias de
  actividad y gradebook operativo citan ese mismo periodo. Registros heredados
  que no puedan mapearse de forma demostrable permanecen
  `migration_review_required`; no se inventan fechas ni periodos historicos.
- `Membership` y sus roles siguen siendo la unica elegibilidad institucional.
  `domain.catalog` posee responsabilidades fechadas de docentes sobre
  asignaturas; `domain.courses` posee excepciones fechadas sobre cursos. Ninguna
  concede roster, progreso, asistencia o calificaciones.
- El acceso efectivo a datos operativos exige membresia activa, capability,
  asignacion activa al grupo de curso y vigencia academica. `administrator`
  conserva alcance operativo institucional; `owner` queda limitado a gobierno
  por ADR 0038. Los docentes solo ven sus grupos y autor/reviewer no heredan
  acceso a personas por trabajar contenido.
- `Organization` incorpora `pending_activation`, `active`, `suspended` y
  `closed`. El operador global crea nombre/slug y una invitacion obligatoria de
  owner, mas invitaciones opcionales de administradores. Nunca recibe
  `Membership`, rol ni enlace institucional.
- La invitacion inicial de owner es un tipo explicito, one-time, hasheado,
  revocable y auditable. Aceptarla crea la primera membresia owner y activa la
  institucion en la misma transaccion. Las invitaciones owner ordinarias siguen
  requiriendo la politica sensible del owner vigente.
- El plano de plataforma puede listar, reenviar y revocar exclusivamente las
  invitaciones iniciales de una organizacion pendiente. Reenviar rota el token
  hasheado y revoca el anterior; al activarse la organizacion, este listado
  devuelve vacio y cualquier incorporacion posterior vuelve al gobierno del
  tenant. Una invitacion inicial de administrador nunca activa la organizacion.
- Una matricula por sincronizacion de grupo es la via normal. Una matricula
  individual conserva origen, motivo, actor y fecha y se presenta como
  excepcion. Ningun cambio reescribe intentos, notas, asistencia o progreso.

## Invariantes y seguridad

- El superadministrador sin membresia recibe 404 en toda superficie
  institucional, incluso si creo la organizacion.
- Una organizacion pendiente no admite datos academicos operativos; solo permite
  consultar/revocar/reenviar sus invitaciones globales desde el plano de
  plataforma y aceptar la invitacion correspondiente.
- Periodo, grupo, release, actividad, matricula y gradebook pertenecen a la
  misma organizacion. Las restricciones se aplican en servicios y selectores,
  no en componentes ni almacenamiento del navegador.
- Los roles no se copian a `User`, `Group`, intentos, perfiles, sesiones o
  payloads de grading. Las responsabilidades y asignaciones conservan historia
  con cierre, nunca borrado fisico.

## Consecuencias

El plano global puede aprovisionar sin convertirse en tenant y la institucion
se activa mediante una persona responsable real. Los reportes, calendarios y
gradebooks pueden acotarse por ejecucion academica, mientras la autoría conserva
un alcance distinto al de datos personales.

Los contratos antiguos aceptan temporalmente `period=null` solo para filas
heredadas marcadas para revision. Las nuevas escrituras son fail-closed.

## Alternativas rechazadas

- Crear al operador como owner y retirarlo despues: abre una ventana de acceso
  contraria a ADR 0034 y dificulta auditar el bootstrap.
- Copiar asignaturas o grupos al rol institucional: mezcla elegibilidad y
  asignacion operativa.
- Inferir periodos por fecha de creacion: inventa historia academica.
- Un gradebook por release para todos los grupos: combina docentes, rosters y
  periodos que deben permanecer separados.
