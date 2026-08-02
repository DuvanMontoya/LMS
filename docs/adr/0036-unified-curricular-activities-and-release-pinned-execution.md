# ADR 0036: Unified curricular activities and release-pinned execution

- Estado: aceptada
- Fecha: 2026-08-01
- Responsables: plataforma academica
- Amplia: ADR 0019, ADR 0021, ADR 0022, ADR 0023, ADR 0024 y ADR 0031

## Contexto

La revision de un curso ordena solamente `CourseUnit`. Las clases en vivo y las
evaluaciones se enlazan despues a un curso o a un `unit_id`, por lo que no
ocupan una posicion curricular verificable. `ExternalLearningRequirement`
agrega requisitos al curso completo y puede alterar el denominador de grupos,
releases o matriculas que nunca recibieron la actividad. El gradebook se crea
por release, no por ejecucion academica.

La consulta del 2026-08-01 a Moodle 5.2 confirmo que la finalizacion se define
por tipo de actividad y que la disponibilidad puede depender de actividad
previa, fecha, calificacion o grupo. Se toma como referencia funcional, sin
replicar su modelo ni declarar compatibilidad. Fuentes:
https://docs.moodle.org/502/en/Activity_completion_settings y
https://docs.moodle.org/502/en/Restrict_access_settings.

## Decision

- `domain.courses` incorpora `CourseActivity` como elemento ordenado de un
  modulo. Los tipos iniciales son cerrados: `lesson`, `live_class` y
  `assessment`. Cada actividad conserva UUID, posicion, obligatoriedad,
  objetivos, politica de finalizacion y reglas tipadas de disponibilidad.
- `CourseUnit` se conserva como contrato de contenido y se vincula uno a uno a
  una actividad `lesson`. Sus rutas y campos v1 continuan como adaptadores; las
  nuevas escrituras mantienen ambos lados mediante servicios de `courses`.
- `courses` no importa scheduling ni assessments. Esos dominios registran
  providers de readiness, snapshot y clonacion y poseen bindings con FK hacia
  la actividad. Una actividad obligatoria no puede publicarse sin binding
  valido.
- `scheduling` expone un registro estable de providers de calendario. Los
  dominios operativos, inicialmente `assessments`, proyectan ventanas y enlaces
  profundos sin que scheduling importe sus modelos ni duplique estado.
- `publishing` emite `course-release-v3`: conserva `modules[].units[]` para
  lectura compatible e incorpora `modules[].activities[]`, politicas,
  objetivos, conceptos y aristas curriculares utilizadas. Los releases v1/v2
  siguen validandose con sus schemas originales.
- `domain.learning` materializa `CourseGroupActivity` al crear o migrar un grupo
  de curso. La instancia copia solamente datos del snapshot asignado y queda
  fijada a grupo, periodo y release. Lecciones, sesiones y entregas operativas
  se enlazan a esa instancia, no a un ID libre ni a autoría mutable.
- `ActivityProgress` conserva el estado proyectado por matricula y actividad;
  cada transicion registra evidencia, fuente, version de politica, actor y
  fecha en eventos append-only. `CourseProgress` se recalcula desde esas
  instancias. `UnitProgress` y `ExternalLearningRequirement` quedan como
  adaptadores de lectura durante la migracion y no reciben escritores nuevos.
- El estado de actividad usa `locked`, `available`, `in_progress`, `completed`,
  `passed`, `failed`, `missed` o `waived`. Avance, dominio, calificacion y
  asistencia permanecen dimensiones separadas. La finalizacion del curso usa
  una politica compuesta versionada en el release.
- Una sesion docente posterior puede ser opcional y contextual al grupo, pero
  no modifica avance, desbloqueo o nota. Volverla obligatoria exige una nueva
  revision/release y una migracion explicita del grupo.

## Invariantes y migracion

- La migracion crea una actividad `lesson` por unidad existente, conservando
  modulo, posicion y UUID compatible. Entregas verificables se vinculan; los
  casos ambiguos quedan `migration_review_required` y no cuentan para progreso.
- Toda instancia operativa coincide en organizacion, curso, release y grupo con
  su snapshot. PostgreSQL impone unicidad y evita reasignar identidad historica.
- El release contiene IDs y politicas academicas, nunca URLs firmadas, secretos,
  tokens LiveKit, respuestas de grading ni estado mutable.
- Readiness rechaza ciclos de reglas, objetivos ajenos, orden no contiguo,
  bindings faltantes y politicas incompletas antes de aprobar o publicar.
- Los contratos v1 permanecen temporalmente como adaptadores de lectura. Ningun
  endpoint v1 puede crear requisitos globales que carezcan de grupo/release.

## Consecuencias

El aula puede recorrer leccion, clase y evaluacion en un solo orden, y el
calendario puede enlazar el mismo contexto. La complejidad operativa se mueve a
instancias explicitas y proyecciones recalculables, sin invertir dependencias
entre dominios. El retiro de `units[]`, `UnitProgress` o requisitos externos
requiere otra ADR y evidencia de que no quedan consumidores.

No se agrega una dependencia. Django/PostgreSQL siguen siendo autoridad;
FullCalendar y LiveKit son adaptadores de presentacion y transporte.

## Alternativas rechazadas

- Guardar `type` y un ID generico en JSON: no ofrece integridad referencial ni
  ownership verificable.
- Ordenar clases y evaluaciones solo en React: crea una secuencia paralela no
  reproducible desde el release.
- Reutilizar requisitos externos por curso: conserva la corrupcion del
  denominador entre grupos y releases.
- Hacer que `courses` importe assessments o scheduling: rompe el monolito
  modular y dificulta clonacion/readiness extensibles.
