# ADR 0023: Versioned assessments, deterministic attempts and initial grading

- Estado: aceptada
- Fecha: 2026-07-30
- Responsables: plataforma académica

## Contexto

Los releases de cursos y las matrículas ya son inmutables y están fijados entre
sí. La plataforma necesita bancos reutilizables, composición editorial,
entregas asociadas al release efectivo, intentos temporizados, respuestas
versionadas y calificación inicial reproducible. El mapa histórico separaba
`attempts` y `grading` como módulos futuros, mientras ADR 0010 agrupó este primer
corte dentro de `domain.assessments`.

## Decisión

`domain.assessments` es propietario del banco, preguntas y evaluaciones
versionadas, deliveries, assignments, attempts, responses, decisiones manuales
y eventos de esta fase. La agrupación es deliberada para mantener una única
transacción y una única autoridad mientras no exista gradebook, regrading ni
analítica. Esos problemas se reevaluarán en un ADR futuro; no justifican ahora
aplicaciones Django adicionales.

Autoría usa identidad estable más revisión editable con `expected_version`.
Aprobar materializa versiones inmutables. `QuestionVersion` separa `public`,
`grading` y `feedback`; `AssessmentVersion` separa snapshots público y secreto.
Los endpoints learner serializan exclusivamente la parte pública y nunca la
seed, las claves, rúbricas ni tolerancias.

Una entrega fija `AssessmentVersion` y opcionalmente `CourseRelease`. Su
assignment referencia exactamente el `EnrollmentReleaseAssignment` efectivo.
Iniciar bloquea el assignment, es idempotente si ya existe un intento en curso,
aplica el máximo de intentos y genera una seed criptográfica. El orden
materializado se almacena en `AttemptItem`; la seed no sale del servidor.

Cada guardado es explícito y usa la versión del intento. Un intento vencido
rechaza nuevos guardados, pero admite el envío final para calificar ausencias
como cero. El envío es definitivo. El scoring usa sólo `Decimal`, reglas
all-or-none y basis points por floor; no existe partial credit. Long text queda
pendiente y cada corrección manual agrega una `ManualGradeDecision` append-only
antes de recalcular el resultado.

PostgreSQL protege versiones, items materializados, decisiones y eventos con
triggers `BEFORE UPDATE OR DELETE`. Los schemas JSON son Draft 2020-12 sin
referencias remotas de red y generan los tipos del navegador con drift check.

## Preparación QTI

QTI 3 se considera exclusivamente un formato futuro de intercambio:

| Concepto local | Mapeo futuro orientativo |
|---|---|
| `QuestionVersion.public` | `qti-assessment-item` y presentación |
| `QuestionVersion.grading` | `qti-response-declaration` y response processing |
| `AssessmentVersion` | `qti-assessment-test` |
| `AssessmentSection` | `qti-assessment-section` |
| `AssessmentItem` | `qti-assessment-item-ref` |

No se implementa importación, exportación, XML, perfiles de interoperabilidad
ni suite de conformidad. La plataforma no afirma conformidad QTI.

## Alternativas rechazadas

- LMS, motor de exámenes o QTI externo: duplicaría identidad, autorización,
  publicación y matrícula.
- SymPy: el symbolic grading pertenece a una fase posterior.
- Celery: todo el cierre inicial debe ser transaccional y síncrono.
- `float`, partial credit o scripts de scoring: reducen reproducibilidad o
  introducen ejecución no confiable.
- Claves en el snapshot público o navegador: crea filtración estructural.
- JWT, `localStorage`, autosave o una máquina de estados externa: duplican
  contratos ya cubiertos por sesión, formulario explícito y servicios.

## Consecuencias

El módulo es más amplio que el corte futuro ideal, pero sus límites internos son
explícitos y reversibles mediante servicios/snapshots. La retención de versiones
y hechos es irreversible por diseño. Gradebook, regrading, pools, partial
credit, expresiones matemáticas e indicadores de ítems quedan fuera del alcance.

## Autorización institucional

Las capacidades se resuelven en `domain.organizations`; no se copian a usuario,
grupo, navegador ni intento. Owner y administrator poseen todas las capacidades
administrativas de assessments. Author administra y versiona bancos, administra
y envía preguntas/evaluaciones, y consulta entregas/resultados, pero no aprueba
ni califica. Reviewer consulta y revisa sin modificar ni aprobar. Instructor
consulta la autoría, administra entregas y califica. Learner no posee capacidades
administrativas y sólo opera intentos propios. `is_staff` no omite políticas y
el bypass de superuser no habilita las APIs learner.

## Evidencia

Migraciones `assessments.0001`–`0005` desde PostgreSQL vacío, triggers,
JSON Schema Draft 2020-12, OpenAPI sin warnings, tipos sin drift, pruebas de
concurrencia `TransactionTestCase`, demo idempotente y Playwright Chromium con
creación real de banco/pregunta/evaluación, axe y 390 px.
