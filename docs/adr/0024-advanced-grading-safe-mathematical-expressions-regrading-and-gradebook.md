# ADR 0024: Advanced grading, safe mathematical expressions, regrading and gradebook

- Estado: aceptada
- Fecha: 2026-07-30
- Responsables: plataforma académica

## Contexto

ADR 0023 estableció bancos, versiones inmutables de preguntas y evaluaciones,
deliveries fijados a release, intentos deterministas, respuestas explícitas y
una calificación inicial all-or-none. Esa base conserva correctamente claves y
seeds del lado servidor, pero no modela crédito parcial, correcciones posteriores
de reglas, expresiones simbólicas, trabajos durables, gradebook ni analítica.

La nueva capacidad debe conservar el historial de Prompt 13 y las fronteras del
monolito. En particular, una corrección de scoring no puede mutar
`QuestionVersion` ni `AssessmentVersion`; una entrega fallida del broker no puede
convertirse en una nota; y ninguna entrada matemática no confiable puede llegar a
un parser basado en evaluación de strings.

## Decisión

### Propiedad y dependencias

`domain.assessments` continúa como único propietario de:

- scoring y crédito parcial;
- expresiones matemáticas;
- pools de preguntas;
- revisions de scoring y grade versions;
- regrading;
- gradebook asociado a `CourseRelease`;
- snapshots de analítica de evaluaciones.

No se crean aplicaciones `grading`, `gradebook`, `analytics`, `regrading`,
`math_engine` ni `question_pools`. Celery ejecuta servicios del dominio, pero no
posee reglas ni estado autoritativo. Se mantienen las dependencias permitidas de
assessments hacia learning, publishing, catalog, organizations, contratos de
content e identidad mediante `AUTH_USER_MODEL`; las dependencias inversas
continúan prohibidas.

### Scoring engine version 2

`SCORING_ENGINE_VERSION = 2` identifica toda nueva grade version. El motor puro
recibe tipo, policy, grading payload, respuesta y puntaje máximo; devuelve
estado, crédito en basis points, puntajes Decimal, corrección, respuesta
normalizada, clave de feedback, razón de revisión manual y diagnósticos internos
seguros. No conoce HTTP, DRF ni persistencia y nunca devuelve objetos SymPy.

El crédito se representa entre 0 y 10000. El puntaje se calcula sin `float` como
`maximum_score * credit_basis_points / 10000` y sólo entonces se cuantiza a
0.001 con `ROUND_HALF_UP`. Nunca puede ser negativo ni superar el máximo.

Las policies son explícitas:

- single choice, true/false y short text: `all_or_nothing`;
- long text: `manual`;
- multiple choice: `exact_set` o `proportional_with_penalty`;
- ordering: `exact`, `position_fraction` o `adjacent_pair_fraction`;
- matching: `exact` o `per_pair`;
- numeric: `binary_tolerance` o `banded_tolerance`;
- mathematical expression: `structural` o `symbolic_common_domain`.

Las versiones históricas conservan exactamente su comportamiento mediante una
`AssessmentGradingRevision` original, sin reescribir su JSON.

### MathJSON, Compute Engine y SymPy

MathLive recoge LaTeX y Cortex Compute Engine 0.99.0 produce MathJSON para UX y
transporte. El navegador no decide la nota. Backend vuelve a validar el contrato
Draft 2020-12, el allowlist y todos los límites.

El subconjunto admite números acotados, racionales estructurados, símbolos
declarados, `Pi`, `ExponentialE`, operadores aritméticos expresos y sólo las
funciones trigonométricas, exponenciales o logarítmicas declaradas. Rechaza
metadata arbitraria, assignment, control de flujo, importación, cálculo,
derivación, integración, límites, sumas, productos, matrices, colecciones,
strings ejecutables y funciones especiales.

Antes de construir SymPy se hace un recorrido iterativo con estos límites:
200 nodos, profundidad 24, 10 símbolos distintos, 4096 caracteres de LaTeX,
100 dígitos por número, exponente entero absoluto 20 y 50 argumentos para
`Add`/`Multiply`.

El mapper usa exclusivamente constructores importados y una tabla inmutable:
`Integer`, `Rational`, `Symbol`, `Add`, `Mul`, `Pow`, `Abs`, `sin`, `cos`,
`tan`, `exp`, `log`, `pi` y `E`. Quedan prohibidos `eval`, `exec`, `compile`,
`sympify` sobre strings, `parse_expr`, `parse_latex`, imports dinámicos,
`getattr` dependiente del input y lambdify con módulos arbitrarios.

Las assumptions (`real`, `positive`, `nonnegative`, `integer`) provienen
exclusivamente de la versión de pregunta y se validan para evitar
contradicciones. La policy estructural compara el AST canónico sin
simplificación pesada. La policy simbólica sólo afirma igualdad sobre el dominio
común donde ambas expresiones están definidas bajo esas assumptions.

La equivalencia simbólica se ejecuta en worker Linux. Primero intenta igualdad
estructural y operaciones exactas acotadas con `cancel(together(lhs-rhs))` y
`simplify(lhs-rhs)`. Un cero exacto demuestra equivalencia y una constante no
cero la refuta. Si sigue inconcluso, hasta 32 puntos deterministas sólo pueden
encontrar un contraejemplo; nunca demuestran equivalencia. El timeout blando es
3 segundos y el duro 5. Un resultado inconcluso o timeout pasa a revisión manual,
nunca a incorrecto.

### Celery, Redis y jobs durables

Celery 5.6.3 usa la integración oficial con Django y Redis DB 2 como broker;
Redis DB 1 permanece reservada a caché. No hay result backend:
`result_backend = None` y `task_ignore_result = True`. Sólo se acepta JSON,
pickle está prohibido y todo corre en UTC.

El worker productivo usa Linux, `prefork`, concurrencia inicial 2, prefetch 1,
reciclaje por número de tareas y límites de tiempo. Consume colas explícitas
`grading`, `regrading` y `analytics`; no existe Celery Beat.

PostgreSQL es la única fuente de verdad. Cada tarea recibe únicamente IDs,
relee el estado, bloquea el job, reclama ejecución y registra un resultado
seguro dentro de transacciones breves. El despacho sucede después del commit.
Cuando se debe conservar `task_id`, se genera antes, se persiste junto al job y
se publica mediante `transaction.on_commit`. El diseño asume entrega
at-least-once y hace las tareas idempotentes; nunca confía en exactly-once ni en
el estado interno de Celery.

La imagen del worker usa la variante oficial
`python:3.13.13-slim-trixie` fijada para linux/amd64 al digest
`sha256:7ba5f5888fbe0014ab9edb2278922995c2201fc3752c46b0be24763eb46fa9f3`,
usuario no root y dependencias bloqueadas de producción. El servicio vive bajo
el profile Compose `async`, no publica puertos ni monta el socket Docker.

### Pools

Los pools son explícitos y pertenecen a una revision editable. Enumeran
`QuestionVersion` candidatas inmutables y seleccionan sin reemplazo con una RNG
local derivada de la seed del intento y el ID del pool. Cada elección se
materializa una sola vez en `AttemptItem`; los candidatos no seleccionados nunca
se exponen al learner. No hay filtros dinámicos, pesos variables ni selección por
dificultad.

### Scoring revisions y grade versions

Cada `AssessmentVersion` tiene una `AssessmentGradingPolicy` y una cadena
append-only de `AssessmentGradingRevision`. Una correction sólo puede cambiar
policy o grading payload, conserva tipo, puntos y superficie pública, exige
razón y control optimista, y no dispara regrading automáticamente.

`AttemptGradeVersion` y sus `AttemptItemGradeVersion` forman una cadena
append-only con digest. `Attempt.current_grade` es la autoridad. Los campos de
puntaje heredados se conservan temporalmente como cachés de compatibilidad y
sólo los actualiza el servicio central. Los estados distinguen
`grading_pending`, `pending_manual`, `graded` y `grading_failed`; una falla
operativa nunca se representa como respuesta incorrecta.

Las decisiones manuales existentes son append-only y prevalecen como corrección
humana efectiva. Initial grading, manual grade y regrade crean nuevas versiones;
ningún proceso borra feedback o puntajes manuales.

### Regrading

Un `RegradeJob` durable fija organización, assessment version, grading revision
y scope opcional de delivery. Materializa hasta 50000 intentos submitted y se
procesa en lotes de 100. Cada intento conserva su current grade anterior si
falla; el job continúa y puede terminar `completed_with_errors`. Los contadores
se recalculan desde filas protegidas, y sólo un servicio explícito reintenta
items fallidos.

### Gradebook

`CourseGradebook` pertenece a un `CourseRelease`, no al curso vivo. Sus columnas
referencian deliveries del mismo release, pesan en basis points y agregan el
intento `highest` o `latest`. La activación requiere columnas contiguas y suma
exacta de pesos 10000.

Entries y summaries son proyecciones derivadas no editables. Missing aporta
cero, pending mantiene incompleto y graded usa el current grade. El porcentaje
ponderado usa aritmética entera/Decimal y no determina aprobación ni modifica
`CourseProgress`. Un servicio explícito refresca las proyecciones tras initial
grade, manual grade o regrade; no hay signals ni Redis.

### Analítica y privacidad

Los snapshots de assessment, item y opción son append-only. `avg(numeric)`
calcula facilidad/crédito medio, `percentile_cont` produce p25, mediana y p75,
y PostgreSQL `corr` estima discriminación entre crédito del item y total
excluyendo el item. Las notas oficiales siguen en Decimal/basis points; una
conversión a double sólo puede ocurrir dentro de la consulta descriptiva.

No se incorporan SciPy ni pandas. Con menos de 10 intentos se suprimen
percentiles y breakdown de opciones; con menos de 20 o varianza nula la
discriminación es NULL y queda marcada como suprimida. La UI la nombra “Índice
de facilidad”, explica dirección y limitaciones, no infiere causalidad y nunca
expone analytics al learner.

## Versiones y compatibilidad

La consulta del 2026-07-30 confirmó SymPy 1.14.0 y Celery 5.6.3 para Python
3.13.13. `celery[redis]` resuelve Kombu 5.6.2, cuyo rango oficial exige
`redis-py < 6.5`; por eso el cliente Python se fija en 6.4.0. Esto no baja ni
cambia Redis Server 8.8.1. Compute Engine se actualiza desde la línea candidata
0.93.0 a la versión estable 0.99.0, compatible con Node 24; no declara peers de
React ni TypeScript.

Las licencias verificadas son BSD-3-Clause para SymPy, BSD-3-Clause para
Celery, MIT para redis-py y MIT para Compute Engine. Los owners son el equipo de
assessments para backend/worker y el equipo web para el adaptador MathJSON. La
alternativa de retiro es conservar las revisions, marcar expresiones simbólicas
para revisión manual y ejecutar los servicios desde management commands
durables sin cambiar el modelo de dominio.

## Alternativas rechazadas

- Mutar `QuestionVersion`, `AssessmentVersion` o grades previas: destruye
  auditabilidad.
- Ejecutar SymPy en HTTP: expone latencia y agotamiento del proceso web.
- Usar el Compute Engine del navegador como autoridad: el cliente no es
  confiable.
- Parser LaTeX/SymPy basado en strings o ejecución dinámica: amplía la
  superficie a código y complejidad no controlada.
- Result backend de Celery o Redis como fuente de verdad: pierde consistencia
  transaccional y durabilidad institucional.
- Exactly-once, locks Redis o signals: ocultan reintentos y ownership.
- Pools por query dinámica: hacen imposible reproducir el intento.
- Regrading implícito al corregir una policy: elimina aprobación humana del
  alcance.
- Reescribir manual grades: invalida decisiones institucionales.
- Gradebook ligado al curso vivo: rompe el anclaje histórico al release.
- SciPy/pandas en esta fase: agregan peso y superficie sin necesidad para los
  agregados descriptivos requeridos.

## Límites y riesgos

- La equivalencia simbólica es conservadora: puede devolver inconcluso aun para
  expresiones equivalentes.
- “Dominio común” no significa igualdad de dominios completos y debe mantenerse
  visible en autoría.
- Los límites reducen, pero no eliminan, el riesgo de expresiones patológicas;
  el aislamiento Linux y los timeouts son una segunda barrera.
- Redis y el worker son infraestructura necesaria para grading simbólico,
  regrading y refresh analítico; su indisponibilidad conserva jobs y grades
  anteriores, pero retrasa el resultado.
- La analítica clásica es descriptiva y sensible al tamaño/selección de muestra.
- Jobs superiores a 50000 intentos requieren particionado explícito futuro.

## Evolución futura

Se podrá incorporar particionado de jobs, nuevas policies matemáticas con ADR,
más estrategias de pool, moderación institucional de manual grades y métricas
psicométricas avanzadas. Cualquier evolución debe versionar motor y contratos,
mantener los historiales append-only y no ampliar el subconjunto matemático sin
amenazas, límites y evidencia de aislamiento proporcionales.

## Evidencia requerida

La aceptación exige migraciones desde PostgreSQL vacío y con datos de Prompt 13,
triggers de inmutabilidad, schemas/tipos/OpenAPI sin drift, pruebas de policies y
ataques MathJSON, redelivery y timeouts del worker, concurrencia, aislamiento
cross-org, demo idempotente, E2E aislado y revisión en Chromium real a desktop y
390 px. El estado verificable se registra en `docs/project/STATUS.md`.
