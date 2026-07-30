# 0019 — Course identity, authoring revisions and ordered structure

Fecha: 2026-07-29. Estado: aceptado.

`domain.courses` es la aplicación propietaria de la identidad lógica del curso y
de su estructura de autoría. `Course` conserva la identidad estable,
organización, slug inmutable y estado activo/archivado; `CourseRevision`
concentra metadata editable, estado de autoría, referencia a una revisión
aprobada anterior y `lock_version`. Una revisión aprobada sigue siendo una
estructura de autoría: no es una publicación, no entrega contenido a estudiantes
y no crea un snapshot inmutable de contenido semántico.

El flujo explícito usa `draft`, `in_review`, `changes_requested` y `approved`.
Sólo `draft` y `changes_requested` admiten escritura. Las transiciones pasan por
servicios transaccionales y dejan un `CourseRevisionTransition` append-only. No
hay bypass por `is_staff`; el superuser conserva el bypass deliberado de la
política institucional. El envío exige integridad curricular y estructural; el
revisor puede solicitar cambios, pero sólo owner o administrator pueden aprobar.

`CourseModule` y `CourseUnit` forman listas jerárquicas con posiciones activas
contiguas desde 1. PostgreSQL garantiza unicidad por contenedor mediante
constraints `DEFERRABLE INITIALLY DEFERRED`, lo que permite reordenar en una sola
transacción sin posiciones temporales. Archivar asigna posición nula y compacta;
restaurar añade al final. No existe borrado físico, biblioteca de ordering,
máquina de estados externa ni drag and drop. Los botones visibles de subir/bajar
preservan semántica de lista y operación por teclado.

Cada mutación recibe `expected_version`, bloquea la revisión con
`select_for_update()` y compara contra `lock_version`. Un valor obsoleto produce
`revision_conflict` con HTTP 409; no se hace last-write-wins. Las escrituras de
módulos, unidades, orden, alineaciones y estados incrementan una sola versión
estructural compartida. Las vistas PATCH validan serializers explícitos sin
`partial=True`; `COMPONENT_SPLIT_PATCH=False` conserva por ello
`expected_version` como requerido también en OpenAPI y el cliente generado.

Las alineaciones referencian `Subject`, `LearningObjective` y `Topic` de
`domain.catalog`, siempre dentro de la organización de la URL y con estado
activo. La asignatura principal es única; los objetivos del curso pertenecen a
asignaturas alineadas y los objetivos de unidad son subconjunto de los del curso.
`catalog` no adquiere lógica de cursos ni recibe escrituras desde `courses`.

La URL `/organizaciones/{slug}/cursos/{courseSlug}` mantiene el contexto
institucional. Next.js valida sesión, organización y visibilidad en Server
Components con `no-store`; el navegador usa el cliente OpenAPI generado,
credenciales same-origin y CSRF de Django. No se guardan organización, curso,
capacidades ni tokens en almacenamiento del navegador.

Quedan aplazados el movimiento de unidades entre módulos, contenido semántico,
editor rico, publicación, snapshots de entrega, inscripciones y evaluaciones.
La siguiente transición arquitectónica añadirá documentos académicos validados
sin convertir la revisión estructural aprobada en publicación.
