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

En una terminal inicia Django:

```powershell
pnpm api:dev
```

En otra terminal inicia Next.js:

```powershell
pnpm web:dev
```

Abre [http://127.0.0.1:3000](http://127.0.0.1:3000). Next reescribe solamente
`/_allauth`, `/api/v1` y `/health` al Django local; `/admin` no se reescribe.

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
Cada nivel del catálogo se edita desde su propia tarjeta: área, disciplina,
asignatura, tema, concepto y objetivo. También se archiva/restaura desde la
interfaz; los identificadores estructurales (slug, código, asignación y ruta
interna de Treebeard) permanecen inmutables.
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
