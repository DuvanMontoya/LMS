# LMS

Plataforma académica propia con Django, Next.js, PostgreSQL y Redis. La
autenticación usa sesiones Django y CSRF; la autorización institucional se
resuelve por organización, membresía y capacidades. No hay JWT, roles globales
en el usuario ni almacenamiento de permisos en el navegador.

## Requisitos locales

- Windows PowerShell 7+, Docker Desktop, Node 24.18.0, pnpm 10.33.2,
  Python 3.13.13 y `uv`.
- Los puertos `5433`, `6379`, `8000` y `3000` deben estar disponibles. PostgreSQL
  local de LMS está en `5433` para no interferir con instalaciones externas.

## Arranque desde una copia limpia

Abre PowerShell en la raíz del repositorio y ejecuta, en este orden:

```powershell
pnpm install --frozen-lockfile
uv sync --locked --directory apps/api
pnpm infra:init
pnpm infra:up
pnpm infra:smoke
pnpm api:migrate
pnpm platform:client:check
```

`infra:init` crea `infrastructure/local/.env` con secretos locales aleatorios
e ignorados por Git. No copies ese archivo a otro entorno ni lo publiques.

Para el uso diario, inicia ambos procesos en segundo plano con:

```powershell
pnpm dev:start
```

Los procesos permanecen activos aunque finalice una tarea de Codex. Puedes
comprobarlos, ver sus registros, reiniciarlos o detenerlos de forma explícita:

```powershell
pnpm dev:status
pnpm dev:logs
pnpm dev:restart
pnpm dev:stop
```

Abre [http://127.0.0.1:3000](http://127.0.0.1:3000). Next reescribe solamente
`/_allauth`, `/api/v1` y `/health` al Django local; `/admin` no se reescribe.
Si prefieres procesos visibles, `pnpm api:dev` y `pnpm web:dev` siguen
disponibles en terminales separadas.

## Acceso personal local

La base local actual contiene la cuenta `rmontoyac@local.test` y su espacio
`espacio-academico-rmontoyac`. La cuenta usa la contraseña entregada directamente
por el propietario; esa contraseña no se documenta, imprime ni guarda en Git.
No es necesario cargar la organización de demostración para entrar.

Para reproducir el acceso en otra base de desarrollo, entrega la contraseña sólo
mediante una variable temporal y retírala inmediatamente:

```powershell
$env:LMS_LOCAL_ACCESS_PASSWORD = '<contraseña entregada fuera de Git>'
uv run --directory apps/api python manage.py bootstrap_local_access `
  --email rmontoyac@local.test `
  --organization-name 'Espacio académico de rmontoyac' `
  --exclusive
Remove-Item Env:LMS_LOCAL_ACCESS_PASSWORD
```

El comando falla fuera de `DEBUG=True`, es idempotente, no imprime la
contraseña y no crea datos académicos ficticios. `--exclusive` revoca otras
membresías activas mediante el servicio de organizaciones; no elimina
organizaciones ni historial.

## Datos de demostración locales

Con los servicios activos, crea las cuentas de demostración exclusivamente en
la base de desarrollo local:

```powershell
pnpm organizations:demo -- -DemoPassword 'DemoLms!2026Organization'
pnpm catalog:demo
pnpm courses:demo
```

El comando se niega a ejecutarse fuera de `DEBUG=True`, marca los correos como
verificados y nunca debe usarse en producción. Puedes iniciar sesión con:

| Rol | Correo | Contraseña |
| --- | --- | --- |
| Propietario | `owner@demo.local` | `DemoLms!2026Organization` |
| Administrador | `administrator@demo.local` | `DemoLms!2026Organization` |
| Estudiante | `learner@demo.local` | `DemoLms!2026Organization` |
| Autor | `author@demo.local` | `DemoLms!2026Organization` |
| Revisor | `reviewer@demo.local` | `DemoLms!2026Organization` |
| Instructor | `instructor@demo.local` | `DemoLms!2026Organization` |
| Owner externo | `external@demo.local` | `DemoLms!2026Organization` |

La organización principal es `Organización de demostración` y se abre en
`/organizaciones/organizacion-demo`. El owner puede administrar miembros; el
administrador puede añadir personas pero no gestionar owners; el estudiante
solamente ve su contexto. La organización externa sirve para comprobar que una
URL ajena devuelve 404.

`pnpm catalog:demo` no recibe ni imprime contraseñas: crea de forma idempotente
la estructura Matemáticas, sus temas, conceptos, objetivos y prerrequisitos. El
workspace se abre en `/organizaciones/organizacion-demo/curriculo`; también hay
rutas de asignatura, conceptos, objetivos y prerrequisitos bajo ese prefijo.
En las páginas de asignaturas y objetivos, quien tenga gestión curricular puede
asociar conceptos, quitarlos y cambiar su orden desde controles visibles. Los
prerrequisitos de asignaturas y de conceptos se validan como grafos acíclicos:
la API devuelve un error claro si una relación forma un ciclo.
Cada nivel del catálogo se gestiona desde el explorador curricular y diálogos
en contexto: área, disciplina, asignatura, tema, concepto y objetivo. También
se archiva/restaura desde la interfaz; los identificadores estructurales (slug,
código, asignación y ruta interna de Treebeard) permanecen inmutables.
La asignatura permite crear un tema raíz o un hijo. Cada tema expone controles
visibles para subir, bajar, reducir su nivel, moverlo como hijo de otro tema y
archivar/restaurar su subárbol. El servidor aplica la misma validación
transaccional aunque se intente llamar la API sin usar esos controles.

`pnpm courses:demo` crea de forma idempotente el curso borrador
`introduccion-calculo-diferencial`, con tres módulos, ocho unidades y
alineaciones reales al currículo demo. No cambia una revisión existente ni
publica contenido. El workspace se abre en
`/organizaciones/organizacion-demo/cursos/introduccion-calculo-diferencial`.

## Revisión manual en navegador real

Después de completar el arranque anterior, deja estas dos terminales abiertas:

```powershell
# Terminal 1
pnpm api:dev

# Terminal 2
pnpm web:dev
```

En una tercera terminal, si aún no cargaste los datos locales, ejecuta una vez:

```powershell
pnpm catalog:demo
pnpm courses:demo
```

Abre [el inicio de sesión local](http://127.0.0.1:3000/auth/iniciar-sesion) e
ingresa con `owner@demo.local` y `DemoLms!2026Organization`. La redirección
lleva a la organización demo; desde allí abre **Currículo**. Para comprobar los
permisos visualmente, cierra sesión y usa `reviewer@demo.local` o
`learner@demo.local` con la misma contraseña: verán sólo contenido activo y no
aparecerán controles de escritura. Estas credenciales son únicamente datos demo
locales, reproducibles con `DEBUG=True`; no existen en producción.

La portada de Currículo muestra los conteos de áreas, disciplinas y asignaturas,
además de búsqueda por nombre y filtro de estado. El espacio de cada asignatura
muestra su descripción, conceptos asociados, objetivos y prerrequisitos directos
o dependientes. Para evitar una petición por fila, las asociaciones tema–concepto
y objetivo–concepto se consultan en lotes organizacionales mediante
`/catalog/topic-concepts/` y `/catalog/objective-concepts/`.

La sección de prerrequisitos muestra listas de **Requiere** y **Es requisito de**
para asignaturas y conceptos. Permite seleccionar varias aristas, su tipo
obligatorio/recomendado y una justificación. Las entidades archivadas no se
ofrecen como candidatos y el mensaje de ciclo no revela detalles internos.

El workspace de Cursos separa identidad estable, revisión de autoría y
estructura ordenada. Owner y administrator pueden administrar cursos; author
puede editarlos y enviarlos; reviewer puede solicitar cambios; sólo owner y
administrator pueden aprobar. Instructor ve únicamente revisiones aprobadas y
learner no tiene acceso a este workspace. Cada mutación exige
`expected_version`; una edición concurrente devuelve `409 revision_conflict` sin
descartar los valores del formulario. La aprobación exige título, resumen,
resultado de aprendizaje, al menos un módulo activo y al menos una unidad
activa por módulo. Esta fase no crea documentos semánticos ni publica contenido
académico.

Para crear una organización real de desarrollo con una cuenta ya verificada:

```powershell
pnpm organizations:bootstrap -- -Name 'Mi institución' -Slug 'mi-institucion' -OwnerEmail 'owner@example.test'
```

No crea usuarios ni solicita contraseñas.

## Operación y validación

| Objetivo | Comando |
| --- | --- |
| Estado de infraestructura | `pnpm infra:status` |
| Detener infraestructura | `pnpm infra:down` |
| Eliminar volúmenes locales, explícitamente | `pnpm infra:reset` |
| Validar organizaciones, schema y drift | `pnpm organizations:check` |
| Ver migración y SQL institucional | `pnpm organizations:migrations` |
| Pruebas institucionales PostgreSQL | `pnpm organizations:test` |
| Matriz de políticas | `pnpm organizations:test:policies` |
| Carrera del último owner | `pnpm organizations:test:concurrency` |
| Comprobación de currículo, filtros, migraciones y cliente | `pnpm catalog:check` |
| Pruebas de dominio y API de currículo | `pnpm catalog:test` |
| Integridad Treebeard | `pnpm catalog:test:tree` |
| Grafos de prerrequisitos | `pnpm catalog:test:graphs` |
| Carrera PostgreSQL de prerrequisitos | `pnpm catalog:test:concurrency` |
| Esquema y cliente OpenAPI del currículo | `pnpm catalog:schema` y `pnpm catalog:client:check` |
| Chromium del currículo (jerarquía, formularios y asociaciones) | `pnpm catalog:e2e` o `pnpm catalog:visual` |
| Validar Courses, migraciones, schema y drift | `pnpm courses:check` |
| Pruebas de modelos, orden, workflow, concurrencia y API | `pnpm courses:test` |
| Esquema y cliente OpenAPI de Courses | `pnpm courses:schema` y `pnpm courses:client:check` |
| Datos demo idempotentes de Courses | `pnpm courses:demo` |
| Smoke HTTP autenticado de Courses | `pnpm courses:smoke` |
| Chromium aislado de Courses | `pnpm courses:e2e` o `pnpm courses:visual` |
| Generar cliente OpenAPI | `pnpm platform:client:generate` |
| Comprobar drift OpenAPI | `pnpm platform:client:check` |
| E2E Chromium aislado | `pnpm organizations:e2e` |
| Compilación de producción de Next con el entorno local | `pnpm web:build` |
| Suite completa de calidad | `pnpm check` y `pnpm test` |

El E2E usa una base PostgreSQL temporal, prefijo Redis temporal y correo
aislado; crea sus contraseñas aleatoriamente para el proceso y elimina los
recursos al terminar. No reutiliza las cuentas demo locales.

El E2E de Courses crea sus cursos sólo en esa base aislada. Recorre creación,
estructura, alineaciones, concurrencia optimista, envío, solicitud de cambios,
reenvío y aprobación; valida author/reviewer/instructor/learner, aislamiento
organizacional, 390 px y axe. El runner elimina base, prefijo Redis, correo y
resultados locales incluso cuando una aserción falla.

La comprobación visual del currículo abre Chromium contra esa infraestructura
aislada, inicia sesión, verifica el árbol de Precálculo, crea disciplina,
asignatura, tema, objetivo y concepto desde formularios visibles, prueba el
ciclo de prerrequisitos y asocia conceptos ordenados a un tema y un objetivo.
También exige retirar asociaciones y aristas antes de archivar un concepto,
edita los seis niveles, verifica que el estudiante no ve contenido archivado y
confirma que revisor e instructor no pueden mutar (incluido un `403` directo
del revisor con su sesión real). Ejecuta axe WCAG 2.2 A/AA. Para revisar
manualmente en un navegador real, deja `pnpm api:dev` y `pnpm web:dev`
ejecutándose y usa las cuentas demo descritas arriba.

## Rutas para la revisión manual

Con Django, Next.js y las cuentas demo levantadas, estas son las rutas de uso
cotidiano. Inicia en la primera y deja que la aplicación complete la sesión;
no pegues contraseñas en la URL ni uses la API para sustituir la revisión
visual.

| Pantalla | URL local |
| --- | --- |
| Inicio de sesión | `http://127.0.0.1:3000/auth/iniciar-sesion` |
| Organizaciones | `http://127.0.0.1:3000/organizaciones` |
| Cursos demo | `http://127.0.0.1:3000/organizaciones/organizacion-demo/cursos` |
| Introducción al cálculo diferencial | `http://127.0.0.1:3000/organizaciones/organizacion-demo/cursos/introduccion-calculo-diferencial` |
| Estructura del curso demo | `http://127.0.0.1:3000/organizaciones/organizacion-demo/cursos/introduccion-calculo-diferencial/estructura` |
| Revisión del curso demo | `http://127.0.0.1:3000/organizaciones/organizacion-demo/cursos/introduccion-calculo-diferencial/revision` |
| Currículo demo | `http://127.0.0.1:3000/organizaciones/organizacion-demo/curriculo` |
| Precálculo y árbol de temas | `http://127.0.0.1:3000/organizaciones/organizacion-demo/curriculo/asignaturas/<id>` (abre la asignatura desde Currículo) |
| Conceptos | `http://127.0.0.1:3000/organizaciones/organizacion-demo/curriculo/conceptos` |
| Objetivos | `http://127.0.0.1:3000/organizaciones/organizacion-demo/curriculo/objetivos` |
| Prerrequisitos | `http://127.0.0.1:3000/organizaciones/organizacion-demo/curriculo/prerrequisitos` |

## Problemas locales frecuentes

- **Un puerto está ocupado:** identifica el proceso antes de detenerlo; LMS usa
  `5433` para PostgreSQL, `6379` para Redis, `8000` para Django y `3000` para
  Next. Después vuelve a ejecutar `pnpm infra:status`.
- **La página abre pero no hay cuentas demo:** con infraestructura y migraciones
  al día, ejecuta de nuevo `pnpm organizations:demo -- -DemoPassword
  'DemoLms!2026Organization'` y `pnpm catalog:demo`. Ambos comandos son
  idempotentes y sólo funcionan con `DEBUG=True`.
- **Se añadió una migración:** ejecuta `pnpm api:migrate`, después
  `pnpm platform:client:check`. Si éste informa drift de contrato, genera el
  cliente con `pnpm platform:client:generate` y revisa el cambio antes de
  continuar.
- **Una edición devuelve `409 revision_conflict`:** la revisión cambió en otra
  sesión. Conserva el formulario abierto, recarga la versión vigente y vuelve a
  aplicar el cambio deliberadamente; no sobrescribas el `expected_version`.
- **No se puede aprobar:** abre la tarjeta de preparación en Revisión. La API
  devuelve los requisitos faltantes como datos estructurados; completa título,
  resumen, resultado de aprendizaje, módulos y unidades activas.
- **Quieres reiniciar los datos locales:** `pnpm infra:reset` borra los
  volúmenes de LMS y pide una confirmación explícita. Después debes repetir el
  bloque de arranque, migraciones y datos demo. No afecta a instalaciones de
  PostgreSQL ajenas porque el proyecto usa un puerto y volúmenes propios.

## Arquitectura y contratos

- Backend institucional: `apps/api/domain/organizations/`.
- Backend de Courses: `apps/api/domain/courses/`.
- OpenAPI de plataforma generado: `apps/web/openapi/platform.openapi.json`.
- Tipos derivados: `apps/web/src/lib/api/generated/platform.ts`.
- Rutas protegidas: `/organizaciones`, `/organizaciones/[slug]`,
  `/organizaciones/[slug]/miembros` y
  `/organizaciones/[slug]/cursos/**`.
- Decisión RBAC: [ADR 0017](docs/adr/0017-organization-scoped-role-based-access-control.md).
- Decisión de identidad, revisiones y orden de Courses:
  [ADR 0019](docs/adr/0019-course-identity-authoring-revisions-and-ordered-structure.md).

Consulta [docs/project/STATUS.md](docs/project/STATUS.md) para el estado real,
[AGENTS.md](AGENTS.md) para reglas de contribución y `docs/` para arquitectura,
seguridad, fuentes oficiales y roadmap.

## Contenido semántico y editor académico

El contenido de cada unidad es JSON semántico validado por
`schemas/content/unit-document-v1.schema.json` (Draft 2020-12), no HTML. Django
usa `jsonschema==4.26.0`; el navegador usa `ajv==8.20.0` y tipos generados con
`json-schema-to-typescript==15.0.4`. El editor usa Tiptap 3.29.2, MathLive
0.110.0, MathJax local 4.1.3 y CodeMirror 6 con versiones exactas en
`apps/web/package.json`. La decisión completa está en
[ADR 0020](docs/adr/0020-semantic-unit-documents-and-schema-versioned-academic-editor.md).

### Preparación, migración y arranque

Desde una copia limpia, con Docker Desktop disponible:

```powershell
corepack enable
pnpm install --frozen-lockfile
uv sync --directory apps/api --locked
pnpm infra:init
pnpm infra:up
pnpm infra:status
pnpm api:migrate
pnpm content:demo
pnpm api:dev
# En otra terminal:
pnpm web:dev
```

`content:demo` ejecuta primero los bootstrap institucional, curricular y de
Courses, y después crea contenido en las ocho unidades. Es idempotente, preserva
IDs y versiones sin cambios y rechaza configuración no development. La ruta se
abre desde Estructura o directamente como:

```text
http://127.0.0.1:3000/organizaciones/organizacion-demo/cursos/introduccion-calculo-diferencial/unidades/<unitId>/contenido
```

La migración `content.0001` crea `UnitContentDocument` (UUID y relación
`OneToOne` con la unidad) y `UnitContentVersion` (UUID, JSONB, texto, métricas,
digest y número único). Las versiones no se actualizan ni eliminan.

### Contrato y capacidades

Los nodos admitidos son párrafo, heading, listas ordenadas/no ordenadas, item,
blockquote, hard break, bloque pedagógico, matemática inline/display, bloque de
código, tabla, fila, celda de encabezado y celda de datos. Los marks admitidos
son bold, italic, strike, inline code y link seguro. Los bloques pedagógicos son
`definition`, `theorem`, `proof`, `example`, `note`, `warning` y `exercise`.
Cada bloque tiene UUID estable y el backend impide IDs duplicados.

MathLive edita sólo el atributo LaTeX; MathJax sirve sus assets desde
`/vendor/mathjax`, activa `ui/safe` y no carga `texhtml` ni `require`
arbitrario. CodeMirror edita texto para los lenguajes enumerados; nada compila
ni ejecuta código. Las tablas exigen caption y encabezados y se representan con
semántica accesible. Los links se normalizan y restringen a destinos seguros.

El guardado es explícito mediante el botón o `Ctrl/Cmd+S`; no existe autosave,
`localStorage`, `sessionStorage` ni IndexedDB. Cada PUT exige
`expected_document_version`. Un cambio crea una versión append-only; un digest
idéntico es no-op. Un 409 conserva íntegro el JSON local y permite comparar con
el servidor. Restaurar una versión histórica crea otra versión actual, nunca
reescribe la anterior. Cambios dirty activan aviso de salida.

Preview y lectura usan el mismo renderer estático tipado. No almacenan HTML,
SVG o MathML y el código propio no usa `dangerouslySetInnerHTML`. En `draft` y
`changes_requested` un owner/author autorizado puede editar; `in_review` y
`approved` son sólo lectura. Reviewer e instructor leen según su rol; learner
no accede al workspace. Readiness impide enviar una revisión si una unidad
activa carece de contenido válido y significativo.

### Límites y seguridad

Se rechazan documentos mayores de 1 MiB, más de 5.000 nodos, profundidad mayor
de 32, más de 300.000 caracteres o 1.000 bloques superiores. El código se
limita a 50.000 caracteres, las tablas a 100 filas × 20 columnas, matemática
inline a 2.048 caracteres, display a 12.000 y URLs a 2.048. El backend hace
pre-scan antes del JSON Schema, valida semántica, UUID, links y comandos LaTeX,
deriva texto/métricas/digest y sólo entonces persiste. La política devuelve 404
ante referencias de otra organización y serializers cerrados evitan mass
assignment.

### Generación, pruebas y revisión visual

```powershell
pnpm content:check
pnpm content:migrations
pnpm content:schema
pnpm content:types:generate     # actualización deliberada
pnpm content:types:check        # drift, sin escribir
pnpm content:test
pnpm content:test:versioning
pnpm content:test:readiness
pnpm content:test:security
pnpm content:test:math
pnpm content:test:editor
pnpm content:schema:api
pnpm content:client:check
pnpm content:smoke
pnpm content:e2e
pnpm content:visual
```

`content:e2e` crea una base PostgreSQL UUID, un prefijo Redis y correo
temporales; migra desde cero y prueba editor, schema, matemática/código/tabla,
persistencia, preview, dos contextos en conflicto, historial/restauración,
readiness, autor/reviewer/instructor/learner, IDOR, payloads maliciosos, teclado,
axe WCAG 2.2 A/AA y ausencia de requests externas. Su `finally` elimina sólo
esos recursos. `content:visual` exige libres los puertos 3000/8000, prepara el
demo y levanta procesos visibles para inspección real; `Ctrl+C` detiene sólo
los procesos que inició el script.

Para una revisión manual, comprueba escritorio y 390 px: estructura, editor,
toolbar con teclado, matemática inline/display, código, tabla, preview,
historial, dirty, conflicto y modo read-only. No sustituyas esta inspección por
una captura estática.

### Problemas frecuentes y limpieza

- Si faltan fuentes o bundles matemáticos, ejecuta
  `pnpm --dir apps/web content:assets:prepare`; el build usa
  `content:assets:check` y falla ante drift.
- Si cambió el schema, genera tipos, revisa el diff y ejecuta
  `pnpm content:schema`; no edites el archivo generado.
- Un `409 content_version_conflict` no autoriza reintento ciego: conserva el
  editor local, revisa la versión del servidor y reaplica deliberadamente.
- Un submit bloqueado expone issues `unit_content_missing` o
  `unit_content_empty`; completa cada unidad activa.
- Para detener desarrollo usa `Ctrl+C` en cada terminal. Antes de matar otro
  proceso, identifica el PID que escucha 3000 u 8000. `pnpm infra:down` detiene
  los contenedores conservando volúmenes; `pnpm infra:reset` es destructivo y
  requiere confirmación.
- No borres versiones para “limpiar”: el historial es evidencia inmutable. Los
  runners E2E ya limpian base, Redis, correo y procesos efímeros en `finally`.

## Publicación inmutable y biblioteca

Una revisión `approved` no está publicada. `publishing` crea un `CourseRelease`
inmutable con snapshot completo, lo valida con Draft 2020-12, canonicaliza,
calcula SHA-256 y enlaza al digest anterior. `CoursePublication` puede estar
`active` o `withdrawn`; retirar exige nota y nunca modifica/restaura releases.
Un draft nuevo clona estructura con UUID nuevos y contenido v1 conservando
digests. Publicarlo después crea el release siguiente.

La biblioteca autenticada lee exclusivamente el snapshot. Owner/administrator
publican, retiran, ven historial y clonan; learner lee; author, reviewer e
instructor no publican. Las respuestas son `private, no-store`. No hay acceso
anónimo, JWT, browser storage, matrícula, progreso ni evaluación.

- `/organizaciones/[slug]/cursos/[courseSlug]/publicacion`
- `/organizaciones/[slug]/cursos/[courseSlug]/publicaciones/[releaseNumber]`
- `/organizaciones/[slug]/biblioteca`
- `/organizaciones/[slug]/biblioteca/[courseSlug]`
- `/organizaciones/[slug]/biblioteca/[courseSlug]/unidades/[unitId]`

```powershell
pnpm publishing:check
pnpm publishing:migrations
pnpm publishing:schema
pnpm publishing:types:generate
pnpm publishing:types:check
pnpm publishing:test
pnpm publishing:test:concurrency
pnpm publishing:test:api
pnpm publishing:schema:api
pnpm publishing:client:check
pnpm publishing:verify
pnpm publishing:demo
pnpm publishing:smoke
pnpm publishing:e2e
pnpm publishing:visual
```

`publishing:demo` sólo funciona en development, usa servicios reales, asegura
aprobación y publica idempotentemente `introduccion-calculo-diferencial`;
production se rechaza. La URL demo es
`/organizaciones/organizacion-demo/biblioteca`. `publishing:verify` recalcula
schema, digest y cadena sin escribir.

Si cambia el schema, genera tipos deliberadamente y ejecuta drift, OpenAPI,
cliente, tests y build. Un 409 exige refrescar `lock_version`, no reintento
ciego. Un release corrupto no se reescribe: se detiene la promoción. Para
navegador manual, libera 3000/8000 y usa `publishing:visual`; `Ctrl+C` detiene
sólo sus procesos. E2E elimina recursos efímeros. El snapshot excluye HTML,
secretos, usuarios y estado del alumno; el lector reutiliza renderer semántico,
MathJax local, código inert, tablas y bloques pedagógicos del Prompt 10.

## Matrículas y entrega del aprendizaje

Publicar un curso no matricula estudiantes. `domain.learning` concede acceso
mediante una matrícula vinculada a una membresía activa y fija un release
inmutable. Un release posterior no mueve matrículas existentes; el upgrade de
una matrícula individual es explícito, conserva la asignación previa y empieza
otro progreso. Las cohortes fijan curso, release y ventana y se archivan sin
borrar historial.

El estudiante usa **Mi aprendizaje** en
`/organizaciones/{slug}/aprendizaje`; sólo una matrícula efectiva abre
`/aprender/{courseSlug}` y sus unidades. Suspensión, revocación, ventana
futura/finalizada, publicación retirada o release inválido niegan contenido. El
avance, la última unidad y el nodo semántico pertenecen al release asignado; no
se guardan JWT, progreso ni permisos en Web Storage.

Para preparar la demostración local, después de publicación ejecuta:

```powershell
pnpm learning:demo
```

El comando es idempotente, sólo funciona con `DEBUG=True`, no crea contraseñas
y conserva progresos/release existentes. Owner y administrator gestionan
`/aprendizaje/cohortes` y `/aprendizaje/matriculas`; author/reviewer/instructor
son sólo lectura según capacidades y learner sólo ve sus matrículas.

| Objetivo learning | Comando |
| --- | --- |
| Checks, migraciones, OpenAPI y drift | `pnpm learning:check` |
| Suite PostgreSQL del dominio | `pnpm learning:test` |
| Carreras reales | `pnpm learning:test:concurrency` |
| Seguridad/API | `pnpm learning:test:security` |
| Demo development | `pnpm learning:demo` |
| Chromium aislado, axe y 390 px | `pnpm learning:e2e` |

El criterio de completitud actual es provisional para cursos sin evaluaciones:
todas las unidades del release deben estar completas. No se implementan
evaluaciones, certificados, enrollment approval ni publicación automática.

## Banco de preguntas y evaluaciones

`domain.assessments` posee bancos, nueve tipos de pregunta, revisiones y
versiones inmutables, composición de evaluaciones, deliveries fijadas a
releases, assignments, intentos, respuestas, scoring determinista y decisiones
manuales append-only. El learner recibe sólo snapshots públicos; claves,
tolerancias, rúbricas y seed permanecen en servidor.

Rutas locales principales:

- `/organizaciones/organizacion-demo/evaluaciones`
- `/organizaciones/organizacion-demo/evaluaciones/bancos`
- `/organizaciones/organizacion-demo/evaluaciones/entregas`
- `/organizaciones/organizacion-demo/evaluaciones/asignadas`
- `/organizaciones/organizacion-demo/evaluaciones/resultados`
- `/organizaciones/organizacion-demo/evaluaciones/calificacion-manual`
- `/organizaciones/organizacion-demo/evaluaciones/regrading`
- `/organizaciones/organizacion-demo/evaluaciones/gradebooks`
- `/organizaciones/organizacion-demo/evaluaciones/analitica`

Después de los demos anteriores:

```powershell
pnpm assessments:demo
pnpm assessments:check
pnpm assessments:migrations
pnpm assessments:test
pnpm assessments:test:concurrency
pnpm assessments:test:security
pnpm assessments:types:check
pnpm assessments:client:check
pnpm assessments:e2e
pnpm assessments:visual
```

El demo es idempotente y sólo funciona con `DEBUG=True`: conserva el banco
`fundamentos-calculo`, nueve preguntas base, diez candidatos de pool, el
diagnóstico, la entrega y el assignment existentes. Numeric usa `Decimal`, no
float, y long text espera decisión manual. No hay autosave, JWT,
`localStorage`, ejecución de código ni import/export QTI. QTI 3 permanece como
mapa futuro sin declaración de conformidad.

La interfaz y la API aplican una matriz institucional estricta: author crea y
envía pero no aprueba ni califica; reviewer revisa sin modificar; instructor
entrega y califica sin editar bancos/evaluaciones; learner sólo ve “Mi
aprendizaje”, “Mis evaluaciones” y sus propios intentos/resultados permitidos.
Los editores de claves son visuales y no requieren códigos internos. El E2E
crea banco, pregunta y evaluación en Chromium, valida axe y 390 px, y limpia
todos sus datos aislados.

## Calificación avanzada, worker y analítica

Scoring engine v2 calcula primero crédito por ítem en basis points
(`0..10000`) y después puntos con `Decimal`; nunca produce crédito negativo ni
superior al máximo. Selección múltiple proporcional con penalización,
ordenamiento por posición, matching por parejas y numeric por bandas usan
fórmulas deterministas declaradas en `scoring-policy-v2.schema.json`. Cada
`AssessmentVersion` tiene una política y revisiones append-only; una corrección
requiere justificación y no cambia el payload público.

`mathematical_expression` usa MathLive para LaTeX y Cortex Compute Engine para
crear MathJSON en el navegador. El backend acepta únicamente un AST allowlisted,
con símbolos/funciones/supuestos declarados, máximo 200 nodos, profundidad 24,
enteros acotados y exponentes enteros entre -20 y 20. Nunca usa `eval`,
`parse_expr`, `parse_latex` ni `sympify` sobre texto no confiable. Constructores
explícitos crean SymPy; equivalencia estructural y simbólica se ejecutan fuera
del proceso HTTP. Un timeout o resultado no concluyente queda pendiente de
revisión, no incorrecto.

Celery 5.6.3 corre en el contenedor Linux no root `assessment-worker`, pool
prefork, concurrencia 2 y colas `grading`, `regrading` y `analytics`. Redis DB 2
es sólo broker JSON, separado de cache auth; no hay result backend ni pickle.
Los jobs, estados y resultados durables viven en PostgreSQL. Para operar:

```powershell
pnpm async:build
pnpm async:up
pnpm async:status
pnpm async:smoke
pnpm async:logs
pnpm async:down
```

Los pools seleccionan sin reemplazo y persisten la selección junto con la seed
del intento; leer nunca recalcula. `AttemptGradeVersion` e item grades son
append-only y `current_grade` señala la vigente. Regrading crea versiones
nuevas, conserva decisiones manuales, actualiza el gradebook y permite reintento
de fallidos sin duplicar resultados. El gradebook pertenece a un release, exige
pesos activos que sumen 10000 y agrega `highest` o `latest`; su resumen no es
course completion ni “nota definitiva”.

Analytics crea snapshots append-only por versión/revisión, calcula muestra,
media, percentiles, aprobación, facilidad, omisiones, opciones y discriminación
con agregados PostgreSQL. Muestras pequeñas y varianza cero se suprimen; los
datos son descriptivos, no públicos ni recomendaciones automáticas.

Demo y validación completa:

```powershell
pnpm assessments:advanced-demo
pnpm assessments:test:partial-credit
pnpm assessments:test:math
pnpm assessments:test:pools
pnpm assessments:test:grade-versions
pnpm assessments:test:regrading
pnpm assessments:test:gradebook
pnpm assessments:test:analytics
pnpm assessments:test:worker
pnpm assessments:advanced-e2e
pnpm assessments:advanced-visual
```

Si un resultado permanece “en proceso”, verifica `pnpm async:status` y revisa
`pnpm async:logs`; nunca reescribas un grade histórico. `async:down` detiene el
worker sin eliminar PostgreSQL. El E2E avanzado usa base, prefijo Redis y worker
efímeros y los limpia siempre.

## Assets académicos y multimedia

La plataforma usa AWS S3 como contrato productivo y LocalStack sólo en
desarrollo/CI. Dos buckets privados separan `quarantine` de objetos listos:
quarantine expira y aborta multipart incompletos; private tiene versioning.
Encryption, block-public-access y CORS de origen exacto se aplican con
`pnpm storage:init`. Los endpoints internos, credenciales y keys generadas con
UUID quedan exclusivamente en backend.

El navegador calcula SHA-256 e inicializa una carga directa. Archivos pequeños
usan presigned POST y los grandes multipart con máximo tres partes concurrentes,
checksum por parte, progreso y cancelación. Django sólo recibe metadata; al
completar verifica `HeadObject`, tamaño y checksum. ETag no sustituye SHA-256.
Después se crea un job durable y el objeto continúa inaccesible en cuarentena.

ClamAV 1.5.3 analiza primero y falla cerrado. El media worker Linux no root usa
FFmpeg/ffprobe 8.1.2 compilado desde source firmado, Pillow 12.3.0 y pypdf
6.14.2. Procesa JPEG/PNG/WebP, PDF, audio, video, VTT y datasets CSV/JSON/text;
rechaza SVG, HTML, archives, executables, spoofing, animación, bombas, PDF
cifrado, UTF-8 inválido y límites excedidos. Produce variantes append-only,
elimina metadata y limpia temporales. FFmpeg incluye GPL/libx264; Boto3 es
Apache-2.0, Pillow MIT-CMU y pypdf BSD-3-Clause.

`Asset` es la identidad archivables; `AssetVersion` fija bytes y
`AssetVariant` fija derivados. Upload no significa READY y READY no significa
published. Content v2 guarda `assetVersionId`, alt/transcript/captions;
publication v2 incluye un manifest fijado en el digest; learning entrega sólo
descriptores temporales de variantes autorizadas por matrícula/release. Un
`current_version` nuevo no altera releases históricos.

Superficies locales:

- `/organizaciones/organizacion-demo/recursos`
- `/organizaciones/organizacion-demo/recursos/nuevo`
- `/organizaciones/organizacion-demo/recursos/<asset-id>`

Operación reproducible:

```powershell
pnpm storage:validate
pnpm storage:init
pnpm storage:status
pnpm media:build
pnpm media:up
pnpm media:status
pnpm demo:organizations
pnpm assets:demo
pnpm assets:smoke
pnpm assets:check
pnpm assets:test
pnpm assets:e2e
```

`assets:demo` es development-only e idempotente; genera imagen, PDF, audio,
video, VTT, CSV y JSON propios y espera el pipeline real. `assets:smoke`
comprueba storage, worker, ClamAV/FFmpeg, reconciliación y rechazo EICAR creado
en runtime. Logs: `pnpm media:logs`. Para detener: `pnpm media:down`. Para
limpiar sólo buckets locales: `pnpm storage:reset-local`; nunca se usa en
producción.

Errores frecuentes: un worker sin la cola `media` deja jobs pendientes; ClamAV
no healthy impide procesar; CORS/origen distinto bloquea el navegador; un
checksum distinto rechaza complete; una URL expirada exige refresh, no
persistencia. Revisa `media:status`, `media:logs` y el detalle del job. HLS,
CDN, OCR y transcripción automática están deliberadamente fuera de Phase 15.
La arquitectura, límites y threat model viven en
`docs/architecture/ASSETS_AND_MEDIA.md` y ADR 0025.
