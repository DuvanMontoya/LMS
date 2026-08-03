# Assessments

Documento normativo de `domain.assessments`, conforme a ADR 0023, ADR 0024 y
ADR 0041.

## Propiedad y dependencias

El módulo posee bancos, preguntas, evaluaciones, versiones, entregas,
asignaciones, intentos, respuestas, scoring inicial, decisiones manuales y
eventos. Puede leer políticas de organizations, objetivos de catalog, releases
de publishing y assignments efectivos de learning. Ninguno de esos módulos
importa assessments. También lee versiones READY de assets para fijar recursos
privados; assets obtiene usos por registro y no importa assessments.

## Capacidades y experiencia por rol

| Rol | Autoría | Entrega y resultados | Experiencia learner |
|---|---|---|---|
| Owner | Ninguna | Ninguna; gobierno no implica autoridad académica | No |
| Administrator | Ninguna | Administra entregas y consulta resultados/gradebooks; no califica ni recalifica | No |
| Author | Administra/versiona bancos; crea y envía preguntas y evaluaciones | Ninguna | No |
| Reviewer | Consulta, revisa y aprueba preguntas/evaluaciones; no crea como author | Ninguna | No |
| Instructor | Ninguna | Administra entregas y califica sólo grupos asignados | No |
| Learner | Ninguna | Sólo sus entregas y resultados permitidos | Inicia, responde y envía intentos propios |

La API valida la capacidad específica en cada lectura, escritura y transición.
La interfaz usa el mismo contexto para retirar secciones, rutas y acciones que
no corresponden al rol; ocultar un control nunca sustituye la política del
servidor. Learner tiene navegación reducida a “Mi aprendizaje” y “Mis
evaluaciones”, y una organización única lo redirige directamente a ese espacio.

## Autoría y snapshots

Pregunta y evaluación separan identidad, revisión y versión. Sólo draft y
changes_requested son editables. Toda escritura exige `expected_version`.
Aprobar una pregunta produce payloads `public`, `grading` y `feedback`
separados; aprobar una evaluación fija versiones de preguntas, puntos,
objetivos, settings, máximo exacto y dos snapshots. Los digests usan JSON
canónico y SHA-256. Las versiones no admiten update/delete.

## Entrega e intento

Una entrega activa fija `AssessmentVersion`; si se vincula a curso, fija también
el release. Un assignment es válido sólo para el
`EnrollmentReleaseAssignment` actual, íntegro y accesible. El inicio bloquea la
asignación, respeta ventana y límite, es idempotente y materializa orden,
payload público y grading secreto en filas distintas del mismo item.

El enunciado acepta el documento semántico v2 y una opción puede fijar una
imagen informativa. La aprobación crea `AssessmentAssetReference` append-only.
Los snapshots guardan sólo UUID; los descriptores temporales se emiten al dueño
del intento y pueden renovarse únicamente si la versión aparece en ese intento.

La respuesta guarda `{schema_version,type,value}` con validación de schema,
tipo esperado y lock optimista del intento. No hay autosave. Después del
vencimiento no se guarda; el submit final sí cierra y califica lo ausente como
cero. El navegador envía automáticamente al vencer y un nuevo inicio reconcilia
bajo lock cualquier intento vencido. Un intento enviado no vuelve a editarse.

## Scoring

Los nueve tipos son single choice, multiple choice, true/false, numeric, short
text, long text, ordering, matching y mathematical expression. Scoring v2
calcula crédito parcial determinista en basis points; numeric analiza texto a
`Decimal`, nunca float. Short text usa NFC, trim, colapso de whitespace y
casefold configurable. Long text no vacío requiere decisión manual. MathJSON se
traduce a un AST SymPy acotado sin evaluar strings arbitrarios.

## Seguridad

La organización y el usuario se acotan antes de resolver cada UUID. Una
referencia ajena devuelve 404. Serializers de learner no tienen campos de
grading. Los cuerpos de escritura son allowlists y rechazan mass assignment.
Sesión HttpOnly/CSRF siguen siendo la única autenticación browser; no hay JWT,
browser storage, ejecución de código ni logs de respuestas secretas.

## Interfaz

La plataforma usa un sistema claro de escala de grises, sin gamificación ni
fondos oscuros de contenido. El encabezado de página es compacto: conserva un
único `h1` y acciones sin repetir breadcrumbs, kicker o descripción visibles.
La autoría de preguntas usa secciones editoriales, vista previa learner y
control de calidad. Selección única/múltiple usa opciones visuales; ordering
usa reordenamiento por botones y matching mediante grupos visuales accesibles,
sin exponer códigos técnicos al autor. Enunciado y opciones pueden seleccionar
versiones privadas procesadas; las opciones exigen texto alternativo y ofrecen
descripción extensa. Errores de mutación se presentan dentro del formulario y
nunca mediante un overlay de Runtime Error.

## Verificación real

El recorrido manual integrado comprobó owner, author, reviewer, instructor y
learner, creación de banco/pregunta/evaluación, entrega, intento, resultado y
calificación. En 390 px no existe overflow horizontal y no hay superficies
oscuras grandes. El E2E aislado repite creación real, ocho respuestas, submit,
conflicto optimista 409, correcciones manuales append-only, máximo de intentos,
anti-IDOR, axe y limpieza de PostgreSQL/correo.

## QTI

El mapa de ADR 0023 es preparación futura. No existe import/export ni
declaración de conformidad con QTI 3.

## Fuentes oficiales consultadas

Consultas: 2026-07-30 y 2026-08-03.

- Django 6.0 QuerySet API, `select_for_update()` y `of=("self",)`:
  https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update
- JSON Schema Draft 2020-12:
  https://json-schema.org/draft/2020-12
- PostgreSQL 18, constraints y locking:
  https://www.postgresql.org/docs/18/
- 1EdTech Question and Test Interoperability:
  https://www.1edtech.org/standards/qti
- Ajv, soporte JSON Schema Draft 2020-12:
  https://ajv.js.org/json-schema.html
- Zod: https://zod.dev/
- TanStack Query:
  https://tanstack.com/query/latest/docs/framework/react/overview
- React Hook Form: https://react-hook-form.com/docs
- Next.js 16 App Router: https://nextjs.org/docs/app
- Playwright: https://playwright.dev/docs/intro
- 1EdTech QTI 3 Beginner's Guide:
  https://www.imsglobal.org/spec/qti/v3p0/guide/
- W3C WAI Images Tutorial: https://www.w3.org/WAI/tutorials/images/
- W3C WAI Complex Images:
  https://www.w3.org/WAI/tutorials/images/complex/
