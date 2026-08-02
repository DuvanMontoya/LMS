# Project status

## Navegación institucional y secuencia de trabajo — en curso 2026-08-02

- **Creación de cursos protegida y rediseñada (2026-08-02):**
  `/organizaciones/{slug}/cursos/nuevo` usa ahora una composición empresarial
  en tres pasos —identidad, alineación curricular y objetivos— con resumen
  persistente en escritorio, lectura lineal en móvil, generación asistida del
  `slug`, estados vacíos accionables y mensajes que explican el siguiente paso.
  El formulario ya no recibe todo el catálogo: para autores, el API filtra las
  asignaturas activas por responsabilidad académica vigente; quienes gestionan
  esas responsabilidades conservan la vista completa. La validación del
  servicio de cursos permanece como segunda barrera frente a solicitudes
  manipuladas o responsabilidades revocadas durante la edición. El bootstrap
  demo asigna responsabilidades reales al autor y dejó de usar al owner como
  actor académico. La revisión visual real cubrió escritorio y 390 × 844 sin
  desbordamiento, incluido el estado sin asignaturas elegibles. Pasan TypeScript,
  ESLint, Prettier, Ruff, `courses:check`, la prueba PostgreSQL del filtro de
  responsabilidades y las 22/22 pruebas de cursos. En Chromium aislado pasaron
  `courses:e2e` pasó 4/4 en una sola corrida: curso incompleto con foco
  accesible, IDOR entre organizaciones, handoff del administrador y el
  escenario largo de extremo a extremo con creación, conflicto optimista,
  estructura, contenido semántico, política de finalización, revisión,
  aprobación, roles, axe y 390 px.

- **Currículo compacto y contextual (2026-08-02):** la ruta institucional de
  currículo conserva búsqueda, filtros, jerarquía, permisos y acciones, pero
  elimina el panel redundante de identidad técnica (`slug`, estado y conteo de
  dependencias). El inspector usa ahora el ancho disponible para relaciones
  navegables, reduce el árbol a una superficie desplazable y lleva la selección
  al detalle en pantallas menores de 1024 px. La comprobación real en Chrome
  cubrió escritorio y 390 × 844 sin desbordamiento; TypeScript y ESLint pasan.
  `web:format:check` continúa bloqueado únicamente por el `tsconfig.json`
  previamente modificado y fuera del alcance de este cambio; los tres archivos
  editados del currículo sí fueron formateados con Prettier.

- **Auditoría de roles y retorno autenticado (2026-08-02):** se detectó que un
  `next` válido pero fuera de las capacidades del rol permitía iniciar sesión y
  terminaba en una 404 (por ejemplo, owner → currículo). La continuación de
  login ahora compara la familia de ruta con las capacidades efectivas y envía
  al workspace principal autorizado sin sustituir la autorización de Server
  Components/API. README diferencia explícitamente asignatura, curso, sección,
  grupo y matrícula, y documenta facultades y límites de cada rol. La prueba
  unitaria del destino posterior al login, el sanitizador de retorno, los
  formularios de autenticación y el sidebar pasan 25/25; TypeScript, ESLint y
  Prettier también pasan. Las 8 pruebas PostgreSQL de la matriz de políticas
  pasan. Chrome verificó propietario, administrador, autor, revisor, docente y
  estudiante con sus workspaces reales; a 390 px, Currículo no desborda. La
  matriz aislada `organizations:e2e` ya pasa: recorre, con sesión independiente
  por rol, cada enlace único expuesto en el sidebar de owner, administrator,
  author, reviewer, instructor y learner sin recibir 404. Se corrigió su
  cierre de sesión para abrir primero el menú de cuenta y se aumentó sólo el
  tiempo de esta matriz completa; la evidencia tomó 7.1 min de Playwright más
  preparación/limpieza de la base efímera.

- **Auditoría de rutas:** el sidebar global es estable: no revela ni reemplaza
  secciones al entrar en cursos o evaluaciones. Las pantallas de detalle y
  formularios se alcanzan desde su listado, breadcrumb o cabecera local, sin
  convertirse en navegación lateral dinámica. Buscar, notificaciones, perfil,
  preferencias, ayuda y configuración quedan deliberadamente en el header o
  menú de cuenta. Las rutas no autorizadas siguen protegidas por capacidad en
  servidor; el sidebar no se usa como barrera de acceso.
- **Cursos:** la ruta `/cursos/nuevo` y su acción existen, pero requieren
  `course.authoring.manage`. `administrator` sólo consulta cursos aprobados por
  ADR 0038 y por eso no recibía “Crear curso”. La lista ahora explica esa
  separación y enlaza a gestionar roles cuando la persona puede asignarlos; no
  se amplió de forma implícita la autoridad de autoría del administrador.
- **Navegación corregida:** `Configuración` queda sólo en el menú de cuenta;
  `Grupos académicos` se llama `Grupos`. Para administración la secuencia es
  `Institución` → `Diseño académico` (Currículo → Responsabilidades docentes →
  Cursos) → `Operación académica` → `Herramientas académicas` (Calendario,
  Clases en vivo, Recursos y Biblioteca). Se retiraron submenús que repetían
  acciones ya presentes en las cabeceras de página y las etiquetas de grupo se
  compactaron para conservar una sola línea. `Secciones` es el nombre de
  producto para el grupo concreto de un curso, release y período; queda
  separado de los `Grupos` institucionales.
- **Evaluaciones:** el sidebar es estable al entrar a cualquier ruta de este
  dominio. La sección muestra desde el inicio sólo las capacidades efectivas;
  ya no reemplaza la navegación por una lista dependiente de la URL. El acceso
  “Calificación manual” de Resultados ahora exige también
  `assessment.grading.manage`, de modo que quien sólo ve resultados no recibe
  un botón que acaba en 404. Se corrigió además la contradicción de analítica:
  `administrator` puede consultar y actualizar analítica, pero no recalificar;
  ahora el API le entrega únicamente los metadatos de revisión que la pantalla
  necesita, nunca el payload de calificación.
- **Evidencia actual:** Vitest de `PlatformShell` pasó **10/10**; TypeScript,
  ESLint, Prettier y `ruff` pasaron. La prueba PostgreSQL
  `test_administrator_can_read_revision_metadata_for_analytics` pasó y verifica
  la política que originaba el 404. En la sesión real de Chrome del
  administrador se recorrieron las 16 rutas expuestas por el sidebar y la
  configuración del menú de cuenta: todas cargaron contenido, incluida
  Analítica, sin 404. El sidebar conserva las mismas cinco secciones en Cursos
  y Entregas y, a 889 px de alto, `scrollHeight == clientHeight`. También se
  comprobó que el administrador no ve ni el enlace de crear curso ni el de
  calificación manual. La matriz Chromium aislada de todos los roles sigue
  pendiente: su preparación efímera agotó 240 s antes de Playwright, así que
  todavía falta la comprobación a 390 px y la matriz de los demás roles.

## Incorporación privada y superficies por rol — en curso 2026-08-02

- **Decisión:** ADR 0039 separa alta pública de activación por invitación. El
  registro puede permanecer cerrado mientras una sesión de invitación vigente
  autoriza exactamente el correo invitado; la organización sólo se activa
  después de verificarlo y aceptar la membresía owner.
- **Evidencia PostgreSQL:** las 5 pruebas de configuración/registro pasan. Se
  comprobó rechazo 403 del alta directa, rechazo 403 al sustituir el correo,
  contexto privado de invitación y activación posterior a la verificación.
- **Navegación:** Inicio, Mi perfil, Buscar y Resumen institucional se retiraron
  del sidebar. La institución y el rol ocupan la cabecera lateral; buscar está
  junto a notificaciones; `/estudiar` y la raíz institucional redirigen al
  espacio principal de owner, administrator, author, reviewer, instructor o
  learner. El plano global no enlaza al tenant. Para la operación institucional,
  el orden visible ahora es preparación → diseño académico → ejecución y se
  eliminaron hijos que repetían exactamente el enlace padre.
- **Ayuda contextual:** el menú de la cuenta ofrece `Ayuda y guía de uso` antes
  de cerrar sesión. La nueva superficie explica en ocho pasos currículo,
  periodos, personas, curso, revisión, release, grupo de curso y matrícula;
  distingue los conceptos con ejemplos y sólo enlaza acciones autorizadas por
  las capacidades vigentes.
- **Autoría de curso:** la estructura ya no representa una lección dos veces.
  Cada actividad canónica contiene tipo, política, estado de contenido,
  alineación, versión y acceso al contenido en una sola tarjeta. La edición
  avanzada permanece dentro de esa tarjeta y el orden mixto llama al endpoint
  unificado de actividades.
- **UI de operación:** el control de instituciones ahora muestra estado global,
  alta separada y un directorio control-plane con detalle de invitaciones. Los
  formularios de área, disciplina y asignatura derivan el identificador técnico
  del nombre y dejan de pedir dos veces la misma identidad.
- **Correo:** DNS público respondió con DKIM de `resend._domainkey`, SPF y MX en
  `send.papyros.pro`, y DMARC `p=none`. Los mensajes directos usan Message-ID
  alineado e idempotencia. Falta inspeccionar encabezados de un mensaje recibido
  y los diagnósticos de Resend; no se afirma que la colocación en bandeja esté
  resuelta.
- **Evidencia web actual:** Prettier, ESLint, TypeScript, las **76/76** pruebas
  Vitest y el build de Next.js 16.2.12 pasaron. La matriz de los seis roles pasó
  orden, rutas esperadas, rutas prohibidas, landing exacto y ausencia de overflow
  a 390 px. Chrome real verificó la sesión administrator, la estructura sin
  duplicados, el centro de ayuda, el menú de cuenta y 390 px con
  `scrollWidth == clientWidth`.
- **Evidencia API actual:** las suites combinadas de identidad e incorporación
  pasaron **18/18** sobre PostgreSQL y `organizations:check` confirmó Django,
  migraciones, schema, OpenAPI y cliente sincronizados.
- **Puertas abiertas:** falta inspeccionar `Authentication-Results` de un correo
  realmente recibido y los diagnósticos del proveedor. LiveKit real continúa
  bloqueado sin proveedor externo; no se infiere conectividad productiva desde
  el stub local.

## Separación de gobierno y autoridad académica — en curso 2026-08-02

- **Decisión:** ADR 0038 elimina el supuesto `owner = superadministrador
  académico`. Owner queda exclusivamente en gobierno institucional;
  administrator opera sin autoría ni calificación; author/reviewer aplican
  maker-checker; instructor califica únicamente dentro de alcance asignado.
- **Implementación verificada:** la matriz backend ya da cero capacidades de
  evaluación al owner y se retiraron bypasses directos owner/administrator de
  catalog, courses, learning y scheduling. La navegación Vitest verifica la
  separación de los seis roles. En Chrome, la URL owner directa de gradebooks
  devolvió 404. El menú de cuenta
  mostró nombre/avatar y el panel de notificaciones mostró el resumen y “Ver
  todas las notificaciones”.
- **Entorno local:** el supervisor reconoce los procesos hijo reales de Django
  y Next y reporta ambos servicios listos. El operador local se sincroniza por
  variables ignoradas, exige `DEBUG` y cero membresías; cambiar la contraseña
  local y reiniciar rota la credencial sin alterar datos de tenant.
- **Evidencia aún abierta:** falta repetir en Chrome la navegación simplificada
  y completar 390 px. No se declara cierre hasta completar esas puertas.
  LiveKit real continúa bloqueado sin proveedor real.

## Coherencia curricular y operativa unificada — en curso 2026-08-01

- **Decisiones:** ADR 0036 define `CourseActivity` como orden canónico de
  lecciones, clases en vivo y evaluaciones, con `CourseUnit` como adaptador
  compatible. ADR 0037 introduce `AcademicPeriod` y aprovisionamiento
  institucional pendiente de activación mediante invitación inicial; el
  operador global no recibe membresía ni acceso implícito al tenant.
- **Implementación local actual:** cursos conserva objetivos, dependencias,
  política de finalización confirmada y esquema de calificación en el snapshot
  v3. Aprendizaje materializa actividades release-pinned por grupo y periodo;
  scheduling y assessments aportan bindings por registros de extensión sin
  invertir dependencias. Las migraciones heredadas marcan relaciones ambiguas
  para revisión y no inventan periodos ni responsables.
- **Evidencia vigente:** `api:check`, Ruff, Pyright y drift de migraciones pasan;
  la cadena completa de migraciones pasó desde cero en PostgreSQL, incluidas
  `identity.0001` intacta, `courses.0002`, `learning.0007`,
  `assessments.0009/0010`, `scheduling.0005/0006` y `organizations.0007`. La
  suite de cursos pasó **17/17** y el contrato de schema de publicación **3/3**.
- **Correcciones abiertas detectadas por pruebas:** el primer pase de learning
  descubrió que el verificador de integridad aún limitaba releases a v2; ya
  acepta v3. El segundo pase encontró validación de lista JSON vacía y un
  `select_for_update` con outer join nullable durante clonación; ambos están
  corregidos y requieren revalidación. Aún no se declara cierre de learning,
  assessments, scheduling, OpenAPI/web ni aceptación Chromium/axe/390 px.
- **Límite operativo:** no se han creado ramas, commits, pushes ni cambios de
  producción. El worktree partió limpio en `main` y todo el trabajo permanece
  local y revisable.

## Refuerzo del borde de autenticación e invitaciones — 2026-08-01

- **Sesión revocada en una ruta protegida:** el proxy de Next sólo puede
  detectar la presencia de una cookie. La aceptación de invitaciones ahora
  comprueba la sesión contra Django en un layout de servidor y redirige al
  inicio de sesión preservando exactamente `next=/invitaciones/aceptar` cuando
  la cookie es falsa, vencida o revocada.
- **Fijación de sesión:** al intercambiar una invitación de un solo uso,
  `begin_invitation_activation` rota la clave de la sesión antes de asociar el
  identificador y el digest de la invitación. La prueba conserva estado no
  sensible y prueba que la clave anterior no se reutiliza.
- **Arnés de navegador:** se retiraron inclusiones temporales `e2e-next-*` de
  `tsconfig.json`; el script E2E las incorpora y restaura por ejecución. Esto
  evita que tipos de una corrida interrumpida se mezclen con rutas vigentes.
- **Perfil propio y roles:** la API ya permitía que una membresía activa leyera
  y actualizara sus propios datos personales, pero la ruta y la ficha web lo
  bloqueaban detrás de `membership.view`. La ficha ahora respeta ese contrato y
  el sidebar ofrece `Mi perfil`; los campos institucionales, notas internas y
  roles siguen siendo exclusivos de `membership.profile.manage`.
- **Control global sin escalamiento de tenant:** el formulario de
  aprovisionamiento ahora exige el correo de una persona propietaria activa y
  verificada. La membresía `owner`, su perfil y sus eventos quedan auditados a
  nombre de esa persona y de quien aprovisionó; el superadministrador no puede
  designarse a sí mismo ni abrir la institución recién creada sin un grant
  institucional explícito.
- **Evidencia local:** Django check, migraciones, Ruff, Pyright, ESLint,
  Prettier y TypeScript pasaron. La prueba Django específica pasó 1/1 sobre
  PostgreSQL. El E2E aislado de Chromium pasó 1/1: ruta protegida con cookie
  falsificada, redirección segura, CSRF y bloqueo efectivo de registro público.
  Una solicitud HTTP directa confirmó `307` a la pantalla de inicio de sesión
  para `/invitaciones/aceptar` con una `sessionid` falsificada. La prueba de
  perfil propio pasó 1/1 y confirmó que un estudiante no puede alterar su tipo
  institucional. Las 59 pruebas Vitest y la batería estática completa también
  pasaron tras estos cambios. Tres pruebas de aprovisionamiento sobre
  PostgreSQL y el E2E aislado de Chromium 1/1 confirmaron que el operador no
  hereda acceso a la institución que crea.
- **Límite de evidencia:** Chrome enumeró las pestañas autenticadas existentes,
  pero el canal expiró al reclamar una para inspección de DOM; no se declara
  verificación visual en Chrome por esta auditoría. No se modificaron datos,
  formularios ni la sesión del usuario.

## Academic scheduling and self-hosted live classes — complete locally

- **Fecha y alcance:** 2026-07-31–2026-08-01. ADR 0031 y ADR 0032 delimitan
  `domain.scheduling`; LiveKit OSS es el adaptador audiovisual autohospedado y
  PostgreSQL conserva agenda, permisos, asistencia y progreso como autoridad.
  El despliegue a VPS está expresamente aplazado y fuera de este cierre local.
- **Sesiones flexibles:** `AcademicEventSeries.course` puede ser nulo. Las
  clases de curso derivan audiencia de matrículas efectivas y opcionalmente
  cuentan para progreso con umbral de asistencia. Las sesiones independientes
  exigen participantes institucionales explícitos y no alteran un curso.
  `learning.0004` agrega requisitos externos y completitudes idempotentes;
  `scheduling.0002` agrega audiencia/progreso y `scheduling.0003` acepta los
  identificadores opacos `EV_…` que entrega LiveKit real.
- **Evolución en curso (2026-08-01):** `scheduling.0004` incorpora una referencia
  opcional y versionada al grupo de curso para que la audiencia de una clase se
  resuelva por sus matrículas efectivas. La validación de esta ampliación queda
  registrada con la reestructuración de roster; no reutiliza por sí sola el
  cierre anterior como evidencia de aceptación.
- **Operación local:** `livekit/livekit-server:v1.13.1` está fijado por digest
  en el perfil Compose `live`, con señalización/API 7880, RTC/TCP 7881,
  RTC/UDP 7882 y métricas 6789 sólo en loopback. `pnpm livekit:up|status|logs|
  smoke|down` administra el servicio. Django usa 8010 para no interferir con
  otro proyecto que ocupa 8000 y para recibir webhooks desde Docker; la web
  permanece en `http://localhost:3000`.
- **Implementación web:** calendario mes/semana/agenda, creación de sesiones de
  curso o independientes, invitados explícitos, progreso/umbral, lobby y aula
  con audio, video, pantalla y moderación. La CSP permite los requisitos de
  Next sólo en desarrollo y conserva el origen LiveKit local; producción
  mantiene la política estricta. Entrar sin permiso de cámara/micrófono deja la
  sala operativa y separa el error de medios del estado de conexión.
- **Evidencia real en navegador y datos:** en el Chrome autenticado del usuario
  se crearon, abrieron y finalizaron una sesión independiente y una clase de
  curso requerida. LiveKit confirmó transporte UDP y el aula mostró profesor y
  alumno simultáneos como `Participantes (2)`, con moderación disponible. El
  alumno permaneció 72 s en la conexión de aceptación; PostgreSQL agregó dos
  segmentos de 31 s y 72 s, registró 103 s de asistencia, creó una sola
  completitud y recalculó el progreso a 1/3 actividades (36,36 %). Dieciséis
  webhooks de esa sala quedaron `processed`, cero `failed`.
- **Validación automatizada:** las suites de scheduling y learning cubren
  aislamiento, invitación independiente, umbral, reconexiones e idempotencia;
  Vitest cubre la UI y la política CSP. Room Service create/list/delete se
  comprobó contra el servidor local real. Las cifras finales de comandos están
  registradas en el cierre de esta tarea.
- **Límite deliberado:** no se probó ni modificó VPS, DNS, SSH, firewall,
  HTTPS/WSS público, TURN público ni Egress. Egress, Ingress, grabación,
  transcripción y Agents permanecen deshabilitados. Ese despliegue será una
  actividad futura separada, ejecutada por el usuario.
- **Siguiente paso exacto:** conservar el entorno local para revisión funcional.
  Cuando el usuario abra una fase de despliegue distinta, ejecutar el preflight
  público de DNS/TLS/TURN y puertos sin reutilizar esta evidencia local como
  aceptación de producción. No se hizo commit ni push.

## Phase 16 — Identity, members, registration, configuration and integrations (in progress)

- **Fecha y alcance:** 2026-07-31; se inició el Prompt 16 correctivo después
  de auditar rutas, ADR, estados de fase, regresión histórica y navegador. El
  inventario acumulativo de brechas está en
  `docs/project/PRODUCT_COMPLETENESS_AUDIT.md`; no se califican como cerrados
  los apartados que aún no tienen evidencia integral.
- **Decisión y límites:** ADR 0030 delimita `identity` (registro global),
  `organizations` (lifecycle institucional) e `integrations` (secretos,
  OAuth y salud). `identity.0001` no fue alterada. No se añadieron roles a
  `User`, grupos, sesiones, navegador, intentos o formularios genéricos.
- **Implementación actual:** existen `PlatformRegistrationSettings`, ajustes
  de membresía por organización, invitaciones hash-only, solicitudes públicas,
  perfiles institucionales, eventos append-only con guardas PostgreSQL,
  activación de cuentas administradas, revocación de sesiones e importación
  CSV con preview efímero de servidor, límite de 500 filas y confirmación
  atómica. La gestión visible ya no se limita a un diálogo de invitación:
  `/miembros` expone `Registrar estudiante`, `Registrar persona`,
  `Invitaciones`, `Solicitudes` y ficha de cada miembro; ésta concentra perfil
  institucional, roles, lifecycle, cierre de sesiones, recuperación de
  contraseña y actividad. Una cuenta administrada se persiste explícitamente
  como `is_active=False` y sin contraseña utilizable hasta su activación. La nueva
  aplicación `domain.integrations` conserva conexiones, credential cipher
  text, OAuth request state/PKCE, health checks y eventos append-only.
- **Cifrado y proveedores:** `cryptography==49.0.0` usa AES-GCM con key ID,
  nonce y AAD institucional. `rotate_integration_credentials --dry-run`
  permite validar la rotación sin revelar valores; la operación normal
  re-cifra con la clave activa. Google usa authorization code, state y PKCE;
  OpenAI, Gemini y DeepSeek consultan solamente listados de modelos para
  validar claves. No hay credenciales reales ni generación de IA.
- **Contrato e interfaz:** OpenAPI y `platform.ts` se regeneraron desde Django.
  `/organizaciones/<slug>/miembros/nuevo`, `/invitaciones`, `/solicitudes` y
  `/miembros/<membershipId>` son rutas dedicadas, no estados escondidos dentro
  de la lista. `/configuracion/integraciones` es una superficie propia y la
  sección de configuración reutiliza exactamente ese centro: separa OpenAI,
  Gemini, DeepSeek y Google Workspace, muestra salud durable, prueba explícita,
  rotación y desconexión. Google declara los tres nombres de configuración de
  servidor necesarios sin mostrar secretos y diferencia OAuth de la clave
  Gemini. La pantalla pública de registro consulta el estado de registro en el
  servidor; `/administracion/configuracion/registro` queda protegido por proxy
  y permiso backend.
- **Evidencia disponible:** después de esta corrección, `pnpm check` pasó
  completo; `organizations:test` pasó 26/26, `domain/integrations/tests` pasó
  11/11 y `web:test` pasó 48/48. Chromium con la sesión de propietario verificó
  el directorio, el formulario de estudiante, la ficha de un estudiante, las
  invitaciones y el centro de integraciones. El intento posterior de `pnpm test`
  fue interrumpido por el límite de 124 s del ejecutor antes de devolver un
  resultado final; no se usa como evidencia nueva. PostgreSQL local tiene
  aplicadas `identity.0002`, `organizations.0002/.0003` e
  `integrations.0001/.0002`. Las pruebas contra cuentas externas no se hicieron
  porque no existen credenciales autorizadas. También quedan pendientes una
  matriz E2E Chromium específica de todos los flujos nuevos, axe de todas las
  rutas nuevas y la inspección documentada a 390 px; por ello la fase no se
  declara cerrada todavía.
- **Corrección posterior de incorporación:** la aceptación de una invitación
  existente es idempotente para la misma persona. Se corrigió la doble
  ejecución de efectos de React en desarrollo: el navegador sólo inicia una
  aceptación y el servicio devuelve la membresía ya creada si recibe el mismo
  intento concurrente autenticado. `pnpm organizations:test` pasó 29/29 y la
  regresión Django completa pasó 278/278 con 75,59 % de cobertura; la migración
  limpia aplicó y eliminó una base PostgreSQL temporal. `pnpm check` y
  `pnpm web:test` (48/48) pasaron. Chromium aislado comprobó el cambio de política de
  registro y recorrió creación, corrección de email, activación y aceptación
  hasta respuestas 201; la suite completa nueva sigue bloqueada por compilación
  en frío de Next antes de cerrar axe, 390 px y los stubs de proveedores. La
  matriz exacta está en `PRODUCT_COMPLETENESS_AUDIT.md`. La configuración
  incorpora además los accesos explícitos `Gestionar personas` y `Registrar
  estudiante`; los aliases `/configuracion/general` y
  `/configuracion/miembros` fueron navegados en Chromium y mantienen la misma
  superficie gobernada, sin crear una capa paralela.
- **Corrección de continuidad, perfiles y control global (2026-08-01):** la
  recuperación lleva desde la solicitud al formulario que recibe el código:
  explica tres pasos, muestra `Código recibido`, el vencimiento de tres minutos
  y el reenvío. La recuperación iniciada por un administrador no entrega un
  código que éste podría usar; entrega a la persona una instrucción para abrir
  su propio enlace e iniciar el flujo ligado a su propio navegador. La ficha de
  miembro y el alta comparten los mismos datos principales visibles (primer
  nombre, primer apellido y tipo de miembro); identificación, contexto
  académico, ubicación y notas quedan en secciones opcionales sin borrar ni
  enviar una representación distinta.
- **Control de plataforma y aislamiento:** el superadministrador activo tiene
  un contexto explícito de operador de plataforma, no una membresía ficticia.
  Puede ver instituciones y crear una escribiendo sólo el nombre; el código
  institucional se genera con un sufijo criptográfico y se crea una membresía
  real de propietario inicial para mantener trazabilidad. Las capacidades de
  plataforma se limitan a administración y no conceden `assessment.attempt` ni
  convierten al operador en estudiante. La barra lateral separa el control de
  plataforma de la administración institucional. La configuración de registro
  sigue siendo fail-closed: al cerrar el modo, desaparece el enlace, la ruta
  pública devuelve 404 y el adaptador rechaza la alta directa.
- **Evidencia de esta corrección:** `organizations:smoke` pasó 5/5,
  `organizations:test:policies` 6/6 y cuatro pruebas de identidad cubrieron
  código de recuperación, no enumeración y registro cerrado. `pnpm check`,
  `organizations:check` y `web:test` pasaron (57/57). En Chrome se validaron
  sesión real de operador, navegación y formulario de instituciones, ficha
  simplificada de un miembro, formulario de código y el cierre/restauración de
  registro; la política se devolvió a `Abierto`. El viewport temporal del
  conector no cambió el ancho CSS (continuó en 1920 px), por lo que no se usa
  como evidencia nueva de 390 px.
- **Regresión de secretos antes de la hidratación (2026-08-01):** se detectó
  que los formularios de identidad podían caer en el envío HTML por defecto
  antes de que React quedara listo. Todos los formularios que procesan
  contraseña o código usan ahora `POST` explícito y su acción de envío queda
  deshabilitada hasta la hidratación; una prueba de componentes protege esa
  regla. En Chrome se comprobó el estado “Preparando formulario seguro…” y el
  acceso posterior no dejó los datos en la URL. Una credencial utilizada antes
  de la corrección debe rotarse por precaución, pues el historial local pudo
  haberla registrado.
- **Autenticación E2E aislada actualizada:**
  `web-auth.ps1 -Action E2E -Grep 'browser session authentication'` pasó 4/4
  con PostgreSQL, Redis y correo temporales. Comprueba alta y verificación,
  inicio/cierre de sesión, recuperación con código, rechazo de la clave
  anterior, rutas protegidas, redirecciones abiertas, CSRF y axe A/AA. Se
  corrigieron aserciones E2E obsoletas para comprobar el espacio de trabajo,
  el estado `?sent=1` y los mensajes accesibles que la interfaz realmente
  presenta; no se alteró el contrato de seguridad para hacerlas pasar.
  `web:test` 57/57, `web:typecheck` y `web:build` terminaron correctamente.
- **Estado de avance:** **NO LISTO PARA AUDITORÍA DE PROFUNDIDAD II** hasta
  completar esa matriz E2E/a11y/móvil y los subflujos de gestión profesional
  que el registro de deuda conserva abiertos.
- **Git:** árbol de trabajo intencionalmente sin commit ni push por instrucción
  expresa. No se ejecutaron add, commit, push, reset, restore, clean, rebase,
  merge ni pull.

## Phase

**Phase 15 — Assets académicos y multimedia** está completada localmente el
2026-07-31. `domain.assets` posee el almacenamiento privado, cuarentena,
versiones inmutables, uploads y procesamiento; content, publishing y learning
lo consumen mediante contratos estables. La implementación fue verificada con
PostgreSQL, LocalStack S3, ClamAV, FFmpeg, Celery y Chromium reales.

## Phase 15 — Assets académicos y multimedia

- **Fecha y prompt:** 2026-07-31; Prompt 15 ejecutado de principio a fin sin
  iniciar el Prompt 16.
- **Git inicial y final:** `HEAD` y `origin/main` iniciales en
  `f87a1e0dafcadcb6879555268f8ec261c4116ff0`, rama `main`, remoto
  `https://github.com/DuvanMontoya/LMS.git`. Codex no ejecutó add, commit,
  push, reset, restore, clean, rebase, merge ni pull. El SHA final se registra
  al concluir la verificación y permanece igual porque no hubo commits.
- **Versiones:** Python 3.13.13, Django 6.0.7, Boto3 1.43.61, Pillow 12.3.0,
  pypdf 6.14.2, FFmpeg 8.1.2, ClamAV 1.5.3, LocalStack 4.14.0, Celery 5.6.3,
  Redis 8.8.1/redis-py 6.4.0, PostgreSQL 18.4, Node 24.18.0, pnpm 10.33.2,
  Next.js 16.2.12, React 19.2.8, TypeScript 6.0.2 y Playwright 1.62.0.
- **Dependencias y licencias:** Boto3 (Apache-2.0), Pillow (MIT-CMU) y pypdf
  (BSD-3-Clause) se fijaron de forma exacta. FFmpeg con libx264 es GPL,
  ClamAV es GPL-2.0 y LocalStack Community sólo se acepta para desarrollo/CI.
  No se añadieron MinIO, django-storages, python-magic, Uppy, tus, Axios,
  HLS, OCR ni transcripción. `pip-audit` y `pnpm audit --prod` no reportaron
  vulnerabilidades conocidas.
- **ADR y límites:** ADR 0025 decide AWS S3 como contrato productivo,
  LocalStack sólo local, cuarentena fail-closed y `AssetVersion` inmutable.
  Assets no importa content, publishing ni learning; éstos registran
  integraciones mediante contratos y providers.
- **App y capacidades:** `domain.assets` añade `asset.library.view`,
  `asset.library.manage`, `asset.upload`, `asset.original.download`,
  `asset.security.view` y `asset.reprocess`. Owner/Admin gestiona; Instructor
  carga y usa; Reviewer consulta; Learner no ve la biblioteca. Staff y
  superuser no eluden policies ni antivirus.
- **Modelos:** `Asset`, `AssetVersion`, `AssetVariant`,
  `AssetUploadSession`, `AssetUploadPart`, `AssetProcessingJob` y
  `AssetEvent` usan UUID, locks, unicidad, estados terminales y triggers
  PostgreSQL append-only. No existe DELETE público.
- **Buckets y LocalStack:** cuarentena y privado separados, sin public-read,
  AES256, CORS con origen exacto, versioning en privado, lifecycle de
  cuarentena y abort multipart. LocalStack 4.14.0 está fijado por tag y digest,
  sólo habilita S3, no monta Docker socket y valida firmas.
- **Boto3 y uploads:** gateway explícito Boto3 con SigV4, path-style sólo
  local, keys UUID server-generated, presigned POST simple y presigned PUT
  multipart. El backend nunca recibe bytes; valida tamaño, metadata,
  `HeadObject`, checksum SHA-256, partes, expiración, complete y abort
  idempotentes.
- **Cuarentena y malware:** ningún objeto se firma desde cuarentena. ClamAV
  valida antes de promover; error de scanner falla cerrado. El smoke EICAR real
  terminó `rejected`, guardó `malware_detected` y firma, y eliminó el objeto.
- **Procesamiento:** Pillow corrige EXIF, elimina metadata y produce thumbnail,
  medium y large WebP; pypdf rechaza cifrado y limita páginas; FFprobe valida
  audio/video, FFmpeg produce audio normalizado, H.264/AAC y poster. WebVTT se
  normaliza; CSV, JSON y text validan UTF-8 y generan perfilado/preview seguro.
- **Jobs y workers:** PostgreSQL conserva jobs durables y eventos; dispatch
  ocurre `on_commit`, leases/locks evitan duplicados y los temporales se
  limpian. El media worker Linux no root usa Celery/Redis DB 2, FFmpeg firmado
  y ClamAV, no publica puertos y separa la cola `media`.
- **Variants y versiones:** source original, variantes y SHA-256 quedan
  inmutables; la promoción usa optimistic lock y reprocesar crea un pipeline
  nuevo sin alterar el source.
- **Content v2:** `imageAsset`, `audioAsset`, `videoAsset`,
  `documentAsset` y `datasetAsset` fijan `AssetVersion`; alt/decorative,
  transcript y captions se validan. `ContentAssetReference` es append-only,
  organization-safe y rechaza versiones no listas o de kind incorrecto. V1
  continúa aceptado y existe migración v1→v2.
- **Publication v2:** el manifest no expone bucket/key, participa en el digest
  y bloquea publicación por referencias inválidas, alt o captions faltantes.
  El release conserva pinning aunque cambie la current version o se archive el
  asset; crear draft desde release conserva la versión exacta. V1 sigue
  verificándose.
- **Delivery:** learning entrega sólo con matrícula efectiva y snapshot de
  release asignado. Los descriptors omiten keys, usan URLs temporales y
  variantes autorizadas; imágenes learner no exponen original. Existe refresh
  batch validado por unidad para image, audio, video, captions, document y
  dataset.
- **API, OpenAPI y tipos:** endpoints `/api/v1/organizations/...` cubren
  biblioteca, detalle, versiones, uploads/parts, jobs, acceso y usages.
  Serializers cerrados, 404 anti-IDOR y capabilities protegen cada recurso.
  OpenAPI, cliente generado y schemas/tipos content/publication v2 pasan
  validación y drift checks.
- **Frontend:** biblioteca, filtro, upload simple/multipart con progreso y
  cancelación, detalle, estados, versiones, usages y picker accesible están
  integrados en la navegación. El editor inserta la versión inmutable y exige
  metadata accesible antes de guardar.
- **Renderer y accesibilidad:** image responsive, audio con transcript, video
  con `<track>`, PDF/dataset como descarga y preview de dataset seguro. File
  input etiquetado, progreso anunciado, teclado, axe y 390 px pasan sin
  overflow horizontal.
- **Demo y README:** `pnpm assets:demo` crea siete assets reales (image, PDF,
  audio, video, VTT, CSV y JSON), es development-only e idempotente; segunda
  ejecución creó 0 y omitió 7. README documenta setup, storage, workers,
  rutas, seguridad, troubleshooting y limpieza.
- **Navegador real:** Chromium integrado validó biblioteca, carga directa
  browser→LocalStack→worker→ready, detalle, descriptor, imagen 960 px,
  playback audio/video, poster, dataset preview y picker a 390 px. Durante la
  inspección se corrigieron capabilities frontend, `asset_id` opcional,
  verificación de releases v1 históricos y preview de dataset.
- **Verificación correctiva (2026-07-31):** se comprobó desde Chromium la
  carga directa de los 16 formatos declarados (`png`, `jpg`, `jpeg`, `webp`,
  `pdf`, `wav`, `mp3`, `m4a`, `ogg`, `mp4`, `mov`, `webm`, `vtt`, `csv`,
  `json` y `txt`), todos en estado `ready` en PostgreSQL. Se aceptan alias MIME
  de contenedor (`audio/x-m4a` y `video/quicktime`) y el formulario infiere
  un MIME seguro por extensión cuando el navegador no lo declara. Se fijó el
  socket local de ClamAV requerido por la imagen oficial, se permitió CORS
  sólo para `localhost` y `127.0.0.1`, y se desactivó el preload inicial de
  Geist para eliminar advertencias de fuentes no utilizadas. Las máscaras de
  scroll quedaron estáticas para no activar posicionamiento ligado al scroll
  en Firefox. La biblioteca usa tarjetas compactas por tipo; no presenta
  overflow a 390 px (343×300,
  una por fila) ni en escritorio (tres columnas de 403×316), y las vistas de
  imagen, audio, video, dataset, PDF y WebVTT fueron abiertas en sus rutas de
  detalle sin errores de consola.
- **Pruebas y cobertura:** 232/232 backend con 75,78 %, 46/46 Vitest,
  E2E assets 1/1 y visual/axe 1/1. Se añadieron pruebas de gateway S3,
  administración, comandos, API, services, procesamiento limpio/infectado,
  checksum y concurrencia. Auth, organizations, catalog, courses, content v1,
  publishing v1, learning, assessments y advanced grading no presentan
  regresiones.
- **Migraciones:** assets 0001/0002 y content 0002/0003 aplican desde una base
  PostgreSQL vacía, incluidos triggers; no hay migraciones pendientes.
- **CI:** levanta PostgreSQL, Redis, LocalStack, ClamAV y media worker; crea
  buckets, ejecuta smoke EICAR, migraciones, contratos, checks, pruebas,
  cobertura, build y Chromium, con cleanup `always()`.
- **Riesgos, deuda y trabajo no realizado:** AWS real, IAM/KMS, CDN y operación
  productiva permanecen para infraestructura autorizada; Redis conserva el
  riesgo de licencia ya documentado. FFmpeg/libx264 requiere aceptación GPL.
  No se implementaron HLS, CDN, OCR, transcripción ni upload por URL. No hay
  bloqueo esencial local.
- **Aceptación:** los 240 criterios están clasificados `PASS` en
  `docs/project/PHASE_15_ACCEPTANCE.md`.
- **Siguiente paso:** **Prompt 16 — Búsqueda, notificaciones y observabilidad: búsqueda académica, eventos de dominio, notificaciones internas, correo asíncrono, Sentry, OpenTelemetry, métricas, logs y operación.**

## Phase 14 — Motor avanzado de calificación y analítica

- **Fecha y prompt:** 2026-07-30; Prompt 14 ejecutado de principio a fin sin
  iniciar el Prompt 15.
- **Git:** `HEAD` y `origin/main` iniciales en
  `1bd5afde0726c64a0189589932df8066175cbd50`, rama `main`, remoto
  `https://github.com/DuvanMontoya/LMS.git`. Codex no ejecutó add, commit,
  push, reset, restore, clean, rebase, merge ni pull; los cambios locales
  heredados y nuevos permanecen sin publicar.
- **Versiones:** Python 3.13.13, Django 6.0.7, PostgreSQL 18.4, Redis 8.8.1,
  SymPy 1.14.0, Celery 5.6.3, redis-py 6.4.0, Node 24.18.0, pnpm 10.33.2,
  Next.js 16.2.12, React 19.2.8, TypeScript 6.0.2, Compute Engine 0.99.0,
  MathLive 0.110.0 y Playwright 1.62.0.
- **Dependencias:** SymPy, `celery[redis]` y Compute Engine se añadieron con
  versiones exactas. No se instalaron NumPy, SciPy, pandas, ANTLR, Lark,
  parsers LaTeX backend, Celery Beat, result backend ni serialización pickle.
  Redis 8 conserva el riesgo legal/operativo ya registrado para producción.
- **Arquitectura:** ADR 0024 mantiene todo el dominio en
  `domain.assessments`; Celery invoca servicios, Redis sólo transporta y
  PostgreSQL conserva jobs, grades, revisiones, gradebooks y snapshots.
  Learning, publishing, courses, content e identity no importan assessments.
- **Scoring v2:** cada ítem produce `credit_basis_points` entero entre 0 y
  10.000. Multiple choice, ordering, matching y numeric banded aplican partial
  credit determinista y cuantizado; Decimal sigue siendo la representación de
  puntajes.
- **Matemática:** MathLive y Compute Engine generan MathJSON; el backend valida
  shape, nodos, símbolos, funciones, tamaño, profundidad, enteros, exponentes y
  assumptions antes de reconstruir SymPy con constructores explícitos. No usa
  `eval`, `exec`, `sympify` sobre strings, `parse_expr` ni `parse_latex`.
  Equivalencia estructural/algebraica y contraejemplos deterministas distinguen
  correcto, incorrecto e inconcluso; timeout o inconcluso van a revisión.
- **Worker:** imagen Python 3.13.13 slim-trixie fijada por digest, usuario no
  root, `prefork`, concurrencia 2, prefetch 1, límites soft/hard, JSON y colas
  separadas para grading, regrading y analytics. Redis DB 2 es broker y DB 1
  continúa reservada a cache; no hay puertos ni result backend.
- **Pools:** candidatos aprobados y `selection_count` quedan versionados; el
  intento materializa una selección sin reemplazo, reproducible por seed y
  nunca la recalcula durante lecturas.
- **Policies y grades:** la política original se backfilló; las correcciones
  exigen razón y crean revisiones append-only. `AttemptGradeVersion` y sus
  ítems son inmutables, conservan historial y un puntero explícito identifica
  el grade vigente.
- **Grading y regrading:** jobs durables despachados tras commit, idempotencia,
  retries controlados, locks y contadores coherentes. Regrading agrega una
  versión sin borrar las anteriores y preserva decisiones manuales.
- **Gradebook:** libros por `CourseRelease`, columnas ponderadas en basis points
  con activación exacta a 10.000, agregaciones `highest`/`latest`, entries
  materializadas, summaries y vista learner propia. No modifica
  `CourseProgress` ni finalización.
- **Analítica:** snapshots append-only calculan facilidad mediante crédito
  promedio, discriminación contra score sin el ítem, distribución de opciones,
  omisiones y percentiles con agregados PostgreSQL. Muestras pequeñas se
  suprimen y varianza cero produce `NULL`.
- **API y seguridad:** endpoints v1 para policies, jobs, pools, grades,
  gradebooks y analytics; jobs devuelven 202, serializers cerrados impiden mass
  assignment y las políticas devuelven 404 anti-IDOR. Learner no recibe seeds,
  expected MathJSON, grading payloads, claves ni analítica institucional.
- **OpenAPI y contratos:** schemas Draft 2020-12, tipos TypeScript y cliente
  OpenAPI están generados y protegidos por drift checks. La paginación de
  bancos y versiones aprobadas está documentada y el frontend consume hasta
  100 filas sin la truncación que afectaba la autoría extensa.
- **Frontend:** editor y respuesta matemática presentan validación explícita;
  “Validando expresión” bloquea el guardado y “Expresión lista para guardar”
  confirma que MathJSON ya está sincronizado. El compositor de pools, consola
  de jobs, gradebook y analítica comparten jerarquía, estados, tablas y lenguaje
  académico coherentes.
- **Accesibilidad y navegador:** labels, navegación por teclado, tablas,
  equivalentes textuales, axe y responsive están cubiertos. En Chromium
  integrado se creó desde el PDF `Ejercicios_06.pdf` un banco real de 57
  preguntas aprobadas y una evaluación premium de 4 secciones, 18 preguntas,
  180 puntos y versión aprobada v1; a 390 × 844 no hubo overflow horizontal.
- **Entrega real:** se creó `Aplicación integral · Taller 06` como delivery
  draft fijada a v1. No se activó ni asignó porque el usuario no especificó
  cohorte, learners ni ventana; no se inventaron identidades o fechas.
- **E2E:** `pnpm assessments:advanced-e2e` pasa 1/1 en Chromium con base
  PostgreSQL UUID, namespace Redis y worker Linux aislados. Cubre pregunta
  matemática, aprobación, pool 5/20, 10 ítems distintos, partial credit
  2.833/10, gradebook 28,33 %, scoring correction, regrading, analítica, axe,
  390 px y cleanup de base, Redis, worker y correo.
- **Pruebas y CI:** scoring, seguridad matemática, timeouts, jobs, pools,
  versiones, regrading, gradebook, analítica, concurrencia, API y frontend
  tienen suites específicas. CI construye el worker, migra desde cero, ejecuta
  PostgreSQL/Redis/Celery, contratos, Ruff, Pyright, pytest, frontend, build y
  Chromium, y limpia con `always()`.
- **Demo y README:** el bootstrap avanzado reutiliza los servicios reales, es
  development-only e idempotente. README documenta scoring, fórmulas, MathJSON,
  límites, worker, colas, jobs, grade history, gradebook, analítica, comandos,
  rutas, seguridad, troubleshooting y limpieza.
- **Migraciones:** `0006_advanced_grading_models`,
  `0007_backfill_advanced_grading` y
  `0008_enforce_advanced_grading_immutability` crean/backfillean el modelo y
  activan triggers de inmutabilidad desde una base PostgreSQL vacía.
- **Riesgos y deuda:** Redis 8 requiere decisión legal antes de producción; la
  equivalencia simbólica permanece deliberadamente acotada y puede producir
  revisión manual; catálogos institucionales mayores a 100 registros requieren
  búsqueda remota paginada/virtualizada. Ninguno bloquea el alcance aprobado.
- **Trabajo no realizado:** no se implementaron ejecución de código, QTI, IRT,
  integrales abiertas, matrices/tensores, completion derivado del gradebook,
  certificados, notificaciones, S3 ni recursos multimedia.
- **Criterios:** los 189 criterios están clasificados individualmente en
  `docs/project/PHASE_14_ACCEPTANCE.md`.
- **Siguiente paso:** **Prompt 15 — Recursos multimedia y archivos académicos: almacenamiento S3, imágenes, documentos, audio, video, datasets, procesamiento y seguridad.**

## Remediación UX del recorrido estudiantil — 2026-07-30

- La Biblioteca incorpora una página individual de curso publicada con resumen,
  objetivos, currículo real, duración, módulos, lecciones y acción de inicio.
  La matrícula incorpora una portada propia con pestañas separadas para
  resumen, contenido, evaluaciones y calificaciones, sin duplicar servicios,
  estado o rutas de negocio.
- El aula de cada unidad usa un player dedicado con barra superior, outline
  lateral propio, navegación anterior/siguiente, continuidad y control de
  progreso. El shell institucional se oculta sólo en esta ruta. Se redujo el
  encabezado editorial y el documento semántico pasó a ser el protagonista;
  objetivos y metadatos académicos quedan en un bloque secundario desplegable.
- Las cuadrículas de cursos y evaluaciones usan cuatro columnas desde escritorio
  ancho y dos en tablet. Las tarjetas redujeron padding, altura, tipografía y
  bloques de datos sin perder estado, intentos, cierre, progreso o acción.
  En el navegador integrado a 1546 × 912 la Biblioteca produjo cuatro tracks
  reales de 297,5 px, tarjeta de 298 px y cero overflow horizontal.
- `/evaluaciones/asignadas` obtiene y muestra exclusivamente entregas.
  `/evaluaciones/calificaciones` obtiene exclusivamente gradebooks y presenta
  resumen personal, promedio consolidado sólo de libros completos, actividades
  calificadas/pendientes y detalle ponderado por curso. Ambas rutas comparten
  navegación explícita y `aria-current`; el sidebar enlaza la nueva pantalla.
- El análisis visual se apoyó en la documentación oficial de Tutor LMS sobre
  course design, frontend dashboard, sticky sidebar y gradebook, y en la de
  MasterStudy sobre course pages y course player; fuentes consultadas el
  2026-07-30. Se adoptaron patrones de jerarquía y navegación, no código,
  contenido ficticio ni contratos externos.
- Verificación final: Prettier, ESLint, TypeScript y `next build` 16.2.12
  pasaron. `pnpm learning:e2e` pasó 1/1 en 5,0 min con matrícula, tabs, player,
  dos unidades, 100 %, ciclo de vida, concurrencia, publicación, retiro,
  responsive 390 px y axe. `pnpm assessments:advanced-e2e` pasó 1/1 con grid de
  cuatro columnas a 1440 px, evaluación real, nota 28,33 %, nueva ruta de
  calificaciones, retorno sin mezcla, responsive, axe y cleanup.
- No se añadieron dependencias, migraciones, endpoints, persistencia paralela ni
  datos ficticios. Codex no ejecutó add, commit, push ni operaciones destructivas
  de Git.

## Phase 13 — Banco de preguntas y evaluaciones

- **Fecha y prompt:** 2026-07-30; Prompt 13 ejecutado de principio a fin.
- **Git:** `HEAD` inicial y final previsto
  `f4ee3250fbbf9903f3ea4f77f33fd910a1ecb014`; `origin/main` permanece en el
  mismo commit, rama `main` y remoto
  `https://github.com/DuvanMontoya/LMS.git`. Codex no ejecutó commit, push,
  reset, rebase, merge, clean ni creó ramas.
- **Arquitectura:** ADR 0023 asigna a `domain.assessments` bancos, preguntas,
  evaluaciones, deliveries, assignments, attempts, responses y grading inicial.
  Learning, publishing, courses y content no importan assessments.
- **Dependencias:** no se añadió ninguna. Se reutilizaron Django/DRF,
  PostgreSQL, JSON Schema/Ajv, Zod, TanStack Query, React Hook Form, Playwright
  y axe en sus versiones bloqueadas; no se instaló LMS, SymPy ni Celery.
- **Capacidades:** owner/administrator administran; author crea/versiona/envía
  sin aprobar ni calificar; reviewer revisa sin modificar ni aprobar;
  instructor entrega/califica sin editar autoría; learner sólo opera sus
  intentos. `is_staff` no omite políticas.
- **Persistencia:** UUID institucionales, slugs/códigos estables, lock optimista,
  constraints diferibles y cinco migraciones. PostgreSQL impide update/delete
  de versiones, transiciones, attempt items, decisiones y eventos.
- **Schemas:** cuatro schemas Draft 2020-12 sin refs remotos, tipos TypeScript
  generados con drift check y snapshots público/grading separados.
- **Preguntas:** ocho tipos funcionales; Decimal y all-or-none, normalización de
  texto corto, long text manual, ordering/matching accesibles y sin claves
  técnicas visibles en el editor.
- **Evaluaciones:** workflow editorial, secciones/ítems ordenados, objetivos,
  readiness, puntos exactos y `AssessmentVersion` inmutable sin claves públicas.
- **Entrega e intentos:** release assignment efectivo, ventanas/retiro,
  asignación atómica, start idempotente y concurrente, seed secreta, orden
  materializado, guardados con versión, timer y submit definitivo incluso tras
  vencimiento.
- **Calificación y feedback:** ausencias a cero, grading automático, long text
  pendiente, correcciones manuales append-only, basis points/passed y políticas
  `none`, `score_only` y `full_after_grading`.
- **API y seguridad:** endpoints v1, 404 anti-IDOR por organización, allowlists
  contra mass assignment, sesión HttpOnly/CSRF, sin JWT/browser storage y sin
  claves, rúbricas, tolerancias o seed en learner/SSR/logs.
- **UI/UX:** sistema claro en escala de grises, sin fondos oscuros de contenido
  ni gamificación; PageHeader compacto global, jerarquía y densidad académicas,
  formularios con errores inline y experiencias específicas por rol. Learner
  ve únicamente “Mi aprendizaje” y “Mis evaluaciones”.
- **Navegador:** recorrido manual integrado por owner, author, reviewer,
  instructor y learner; creación real de banco, pregunta, evaluación, entrega,
  intento y resultado. A 390 px no hay overflow ni superficies oscuras grandes.
- **E2E:** `pnpm assessments:e2e` pasa 1/1 en Chromium y cubre creación real,
  autoría, ocho respuestas, submit, 409 concurrente, grading y corrección,
  máximo de intentos, timer, leakage, anti-IDOR, axe, 390 px y cleanup.
- **Validación:** 172/172 pruebas backend y 78,06 % de cobertura; 43/43 Vitest;
  Ruff, Pyright, ESLint, Prettier, TypeScript, Next build, OpenAPI, tipos,
  cliente, migraciones desde cero, lockfiles y auditorías pasan.
- **Trazabilidad:** los 180 criterios están clasificados en
  `docs/project/PHASE_13_ACCEPTANCE.md`; no hay FAIL ni BLOCKED esencial.
- **Riesgos y deuda:** no se implementan las capacidades avanzadas del Prompt
  14; la búsqueda remota paginada/virtualizada para catálogos institucionales
  muy grandes sigue siendo optimización de escala no bloqueante.
- **Siguiente paso:** **Prompt 14 — Calificación avanzada y analítica de evaluaciones: partial credit, expresiones matemáticas, pools, regrading, gradebook e indicadores de ítems.**

## Phase 12 — Matrículas y entrega del aprendizaje

- **Fecha y prompt:** 2026-07-30; Prompt 12 ejecutado de principio a fin. El
  Prompt 13 no fue ejecutado.
- **Git:** `HEAD` inicial y final
  `9d6a33d704ad94917ec80af1d5cf77b2bea6f287`; `origin/main` inicial y final en
  el mismo commit; rama `main`; remoto
  `https://github.com/DuvanMontoya/LMS.git`. No hubo cambios externos, commits,
  pushes, ramas ni reescrituras de historial por Codex.
- **Versiones:** Python 3.13.13, uv 0.11.19, Django 6.0.7, DRF 3.17.1,
  django-filter 26.1, drf-spectacular 0.30.0, psycopg 3.3.4, PostgreSQL 18.4,
  Redis 8.8.1, Node 24.18.0, pnpm 10.33.2, Next.js 16.2.12, React 19.2.8,
  TypeScript 6.0.2 y Playwright 1.62.0.
- **Dependencias:** no fue necesaria una dependencia nueva para el dominio. Se
  reutilizaron Django/DRF, django-filter, PostgreSQL, TanStack Query,
  React Hook Form, Zod, el cliente OpenAPI y axe. Las licencias y alternativas
  permanecen documentadas en `docs/research/DEPENDENCY_EVALUATION.md`.
- **ADR:** ADR 0022 fija la propiedad de `domain.learning`, el pinning explícito
  de releases, el progreso transaccional, la continuidad last-write-wins y los
  eventos append-only protegidos por PostgreSQL.
- **Capacidades:** se añadieron seis capacidades `learning.*`; owner/admin
  administran cohortes y matrículas, instructor consulta progreso, author y
  reviewer tienen sólo las lecturas institucionales previstas, y learner accede
  únicamente a su propia matrícula. Ser staff no omite políticas; el superuser
  conserva únicamente el bypass administrativo explícito.
- **Modelos:** `LearningCohort`, `CourseEnrollment`,
  `EnrollmentReleaseAssignment`, `CourseProgress`, `UnitProgress` y
  `LearningEvent`, todos con UUID, organización y relaciones explícitas.
- **Constraints e índices:** unicidad case-insensitive del slug de cohorte,
  máximo de una matrícula no revocada por membership/curso, un assignment
  vigente por matrícula, intervalos contiguos, un progreso por assignment y una
  fila por unidad; índices cubren organización, curso, estado, ventanas,
  membership y consultas cronológicas.
- **Triggers:** `learning.0002` rechaza `UPDATE` y `DELETE` de eventos;
  `learning.0003` impide cambiar el release de una cohorte con matrículas.
  Ambos migran desde una base PostgreSQL vacía.
- **Cohortes y matrículas:** creación, archivado lógico, ventanas opcionales,
  matrícula manual y por lote atómica, suspensión, reactivación, revocación
  terminal y reincorporación mediante una matrícula nueva.
- **Assignments, pinning y upgrades:** cada matrícula conserva un historial
  contiguo de assignments. Una publicación nueva nunca migra matrículas. El
  upgrade individual es explícito, cierra el assignment anterior, crea uno
  nuevo y no copia progreso; las matrículas de cohorte no admiten upgrade
  individual.
- **Progreso y completitud:** contadores fijados desde el snapshot, porcentaje
  en basis points, `expected_version`, locks de fila, apertura, completado
  idempotente, reapertura y transición exacta del curso completo/incompleto.
- **Continuidad:** unidad y nodo semántico se validan contra el snapshot; el
  navegador guarda con debounce de cinco segundos y `pagehide`, restaura hash,
  foco y movimiento reducido, y usa fallback seguro sin `localStorage`.
- **Eventos:** alta, suspensión, reactivación, revocación, assignment, upgrade,
  apertura, completado, reapertura y finalización quedan como hechos
  append-only; los movimientos frecuentes de posición no generan eventos.
- **Políticas y acceso:** membership activa, matrícula propia activa, ventana
  vigente, publicación no retirada, assignment vigente e integridad del release
  son requisitos acumulativos. `course.published.view` no sustituye matrícula.
- **API:** rutas versionadas bajo
  `/api/v1/organizations/{slug}/learning/`, con administración de cohortes,
  matrículas y progreso, y superficie propia `me`; filtros, orden, paginación,
  errores estables, 404 anti-IDOR, CSRF y throttle de posición.
- **OpenAPI:** schema sin warnings ni colisiones, cliente TypeScript regenerado
  y checks de drift de learning y plataforma aprobados.
- **Frontend y accesibilidad:** dashboard “Mi aprendizaje”, outline con
  progreso, lector snapshot-only, continuar, anterior/siguiente y pantallas
  institucionales de cohortes, matrículas y progreso. Se verificaron progreso
  nativo, captions, foco, teclado, contraste, axe WCAG 2.2 A/AA y 390 px sin
  overflow.
- **Demo y README:** `pnpm learning:demo` es idempotente, sólo funciona con
  `DEBUG=True`, no crea contraseñas y preserva la matrícula, el release y el
  progreso ya existentes. README documenta comando, cuentas, rutas y pinning.
- **Pruebas:** 18 pruebas learning y 144 pruebas backend pasan; cobertura total
  backend 81.92%. Pasan Ruff, Pyright, ESLint, Prettier, TypeScript, 40 pruebas
  Vitest, Next build, checks de producción, migraciones desde cero, OpenAPI,
  drift, auditorías y los E2E de learning y publishing.
- **Navegador:** Chromium integrado inspeccionó dashboard del estudiante,
  outline/lector, restauración, administración de cohortes y progreso en
  escritorio y 390 px. El E2E aislado repitió el recorrido con axe, teclado,
  dos contextos concurrentes y limpieza final.
- **CI:** instala dependencias bloqueadas, arranca PostgreSQL/Redis, verifica
  migraciones, schema/cliente, límites modulares, pruebas, concurrencia,
  seguridad, build y Chromium, con cleanup incondicional.
- **Auditorías:** `pip-audit` y `pnpm audit --prod` no reportan
  vulnerabilidades conocidas. `uv lock --check`, `uv sync --locked` y
  `pnpm install --frozen-lockfile` pasan.
- **Riesgos y deuda:** Redis conserva su decisión de licencia/operación para
  producción; el throttle de DRF no es un control antiabuso absoluto; el punto
  de lectura usa deliberadamente last-write-wins; los overrides heredados de
  `postcss`/`sharp` se revisarán con Next.js. No hay bloqueo esencial ni cambio
  irreversible adicional al pinning registrado en ADR 0022.
- **Trabajo no realizado:** evaluaciones, bancos de preguntas, intentos,
  calificación, certificados, Celery, ejecución de código y LMS externo quedan
  fuera del alcance.
- **Siguiente paso:** **Prompt 13 — Banco de preguntas y evaluaciones: tipos de pregunta, bancos versionados, composición de evaluaciones, intentos, respuestas y calificación inicial.**

## Auditoría UI/UX posterior a Phase 12 — 2026-07-30

- Se recorrieron en Chromium integrado las rutas protegidas con instancias
  reales disponibles para owner y learner, tanto a 1280 px como a 390 px. El
  build enumeró y compiló además todo el árbol App Router. Las pantallas
  revisadas mantienen un único `main`, no presentan overflow horizontal y
  conservan navegación, permisos y datos reales.
- El shell dejó de anidar landmarks `main`. “Mi aprendizaje” ya no queda activo
  en las rutas administrativas y “Entrega del aprendizaje” permanece activo
  tanto en cohortes como en matrículas, incluidos sus detalles. El drawer móvil
  conserva todas las opciones autorizadas, scroll interno, cierre por
  navegación y separación correcta entre owner y learner.
- Cohortes y matrículas adoptaron el espaciado y superficies del sistema
  académico. Se añadieron búsqueda, filtros, paginación, estados vacíos,
  etiquetas de estado y fechas en español, progreso compacto, métricas y
  tarjetas adaptables. Los formularios ya no exigen UUID, slug de curso ni
  número de release manuales: usan membresías, cursos, releases y cohortes
  autorizados obtenidos de la API.
- Archivar, suspender, reactivar, revocar y actualizar release requieren
  diálogos descriptivos; el botón final nombra la acción concreta. Una
  matrícula revocada vuelve a estar disponible para reincorporación mediante
  una matrícula nueva, sin alterar su historial.
- La auditoría detectó un defecto funcional en `_ordered`: solicitar
  `ordering=-created_at` producía `--created_at` y rompía el listado de
  matrículas. La normalización quedó corregida y una regresión API cubre orden
  ascendente y descendente en cohortes y matrículas.
- El lector solicitaba el worker local de accesibilidad de MathJax, pero la
  copia reproducible no lo incluía y respondía 404. `speech-worker.js` forma
  ahora parte de los assets verificados por `prebuild`; el servidor local
  responde 200 con el archivo completo.
- Evidencia final: `pnpm check`, `pnpm web:test` (40/40), `pnpm web:build`,
  `pnpm learning:check`, `pnpm learning:test` (18/18), `pnpm api:test`
  (144/144; 81.92 %) y `pnpm learning:e2e` (1/1 con axe, 390 px, concurrencia y
  cleanup) pasan. El recorrido manual comprobó el lector anclado al nodo de
  continuidad, sin recursos externos ni overflow.
- Deuda residual no bloqueante: los selectores administrativos cargan hasta 100
  cursos, cohortes y membresías por formulario. Antes de operar organizaciones
  mayores se debe sustituir ese límite por búsqueda remota paginada y
  virtualización accesible; no se introdujo una dependencia sólo para anticipar
  esa escala.

## Delivered scaffold

- El checkout actual está en `main`, sigue `origin/main` y conserva su historial
  previo. La precondición del Prompt 9 que afirmaba “sin remote/sin commit” no
  coincidía con el estado autoritativo del repositorio. Mientras la validación
  seguía activa, a las 14:05 del 2026-07-29, `HEAD` y `origin/main` avanzaron
  externamente de `475c129` a `ee40ffd`; Codex no ejecutó `commit` ni `push`, no
  creó una rama y no reescribió ese movimiento. Los ajustes del cierre hostil
  permanecen preservados como cambios locales sobre ese commit.
- Root pnpm workspace with Node 24.18.0 and pnpm 10.33.2 pinned in `.node-version` and `package.json`.
- `apps/api`: uv project pinned to Python 3.13.13, Django 6.0.7, DRF 3.17.1, drf-spectacular 0.30.0, psycopg 3.3.4; `uv.lock` present.
- Five official Django app skeletons: `identity`, `catalog`, `content`, `learning`, `assessments`; ADR 0010 records their intentional grouping.
- Environment settings package (`base`, `development`, `test`, `production`) with PostgreSQL-only configuration, safe production checks and `.env.example` placeholders.
- `apps/web`: Next 16.2.12, React 19.2.8, Tailwind 4.3.3, TypeScript 6.0.2, ESLint 9.39.5, Prettier, Vitest, Testing Library and Playwright Chromium; root `pnpm-lock.yaml` present.
- Root scripts and PowerShell `preflight`, `bootstrap`, and `check` runbooks; Linux CI workflow created.

## Delivered local infrastructure

- `compose.yaml` declares only PostgreSQL 18.4 and Redis 8.8.1, a private bridge network, loopback ports, health checks and named volumes; `compose.lock.yaml` fixes their verified Linux amd64 digests.
- `infrastructure/local/.env` is generated with cryptographically random local secrets and ignored. The selected PostgreSQL host port is `5433` because a non-LMS PostgreSQL process already owned `5432`; Redis uses free port `6379`.
- `scripts/infrastructure.ps1` provides explicit init, validation, pull/lock, lifecycle, restart, smoke and confirmation-gated reset operations. The smoke proves PostgreSQL SCRAM failures/success, UTF-8, UTC, checksums, Django connectivity and restart persistence; it also proves Redis authentication, AOF persistence, cleanup and non-root service operation.
- ADR 0012 records the Redis 8.8.1 upgrade and tri-license condition; ADR 0013 records the Compose/digest model. CI runs the disposable Linux Compose smoke and always cleans its project resources.

## Delivered Django foundation

- Pre-migration audit found no application tables, no `django_migrations` and no prior migrations. `identity.0001_initial` was generated by Django 6.0.7, its SQL inspected, then all built-in and identity migrations were applied without fake operations.
- `identity.User` extends `AbstractUser`, has UUID primary key, removes `username`, uses normalized required email as `USERNAME_FIELD`, and protects exact plus `Lower(email)` uniqueness in PostgreSQL. ADR 0014 records this irreversible choice.
- `Django[argon2]` resolved `argon2-cffi 25.1.0`; Argon2id is first in `PASSWORD_HASHERS`. DRF defaults to SessionAuthentication/IsAuthenticated/JSON. Redis remains unrelated to Django.
- Internal forms/admin work without username. No persistent superuser, authentication endpoint, allauth, profile, role, academic model or SQLite database was created.
- `/health/live/` and `/health/ready/` are outside OpenAPI; real checks passed for 200, HEAD and controlled PostgreSQL 503/restore. Pytest PostgreSQL suite: 21 passed, 89.82% coverage; Ruff and Pyright passed.
- `scripts/django.ps1`, package commands and CI now cover checks, plans, migration, health, PostgreSQL tests and a clean ephemeral migration database. The documentation path cited as `0013-compose-image-locking.md` in the prompt was corrected to the actual decision `0013-local-compose-and-image-locking.md`.

## Delivered headless authentication

- `django-allauth[headless-spec] 65.18.0` and `redis 8.0.1` are exact direct dependencies. `PyYAML` is the only allauth extra dependency. The distribution's browser-session headless module works without the `headless` optional extra, which would install `PyJWT[crypto]` for excluded JWT capability; no `django-redis`, REST-auth wrapper, JWT library, social extra, MFA or app client is installed.
- `allauth`, `allauth.account` and `allauth.headless` are configured with the official account middleware and both official authentication backends. `identity.User` and its immutable `identity.0001` remain unchanged; allauth migrations `account.0001` through `account.0009` applied normally and no social table exists.
- The public contract is `/_allauth/browser/v1/`; `/accounts/` retains only allauth internals while `HEADLESS_ONLY=True` removes headed login/signup. Browser authentication uses PostgreSQL-backed Django sessions and real CSRF. Session cookies are HttpOnly/SameSite=Lax and production enables Secure; no access, refresh or `X-Session-Token` is issued. `LMS_FRONTEND_URL` supplies only future signup/reset links required for neutral allauth mail; it does not create a Next.js UI.
- Registration is email/password only, normalized by the existing user model and manager. Mandatory allauth email codes allow three attempts, expire after 900 seconds and support resend. Password-reset codes allow three attempts and the official 180-second timeout; reset does not authenticate the account. Development mail is written under ignored `apps/api/.local/mail`; tests use locmem. Spanish plaintext/HTML templates contain no password, UUID, tracker or remote asset.
- Redis logical database 1 is explicitly reserved for Django `RedisCache` keys prefixed `lms-auth`; it provides allauth rate limits and never stores sessions, users or custom codes. There is no LocMem/Dummy fallback. `/health/ready/` now checks PostgreSQL and the public cache API without revealing which dependency failed; liveness remains dependency-free.
- `domain.identity.adapters.LMSHeadlessAdapter` provides the official OpenAPI-aware minimal user payload: UUID string, email, display and `has_usable_password`. `scripts/auth.ps1` and root `auth:*` commands validate configuration, official routes/specification, migrations, functional/security/email/rate tests, safe smoke and scoped development-mail cleanup. CI starts the project Compose PostgreSQL and Redis pair before authentication checks.

## Delivered Next.js browser authentication integration

- `apps/web` now presents Spanish routes for login, registration, email verification, password recovery/reset and the minimal protected `/estudiar` area. Django remains the owner of every cookie, session, CSRF decision and account flow; Next does not create auth cookies or store tokens.
- `next.config.ts` validates the server-only `DJANGO_INTERNAL_ORIGIN` and rewrites only `/_allauth`, `/api/v1` and `/health`. `FRONTEND_ORIGIN` defaults to canonical `http://127.0.0.1:3000` while `CSRF_TRUSTED_ORIGINS` dynamically accepts loopback alternatives (`http://localhost:3000` and `http://127.0.0.1:3000`) to prevent 403 CSRF rejection during browser dev sessions; no CORS or `/admin` rewrite exists.
- The generated `openapi/allauth.openapi.json` (12 browser paths) and `src/lib/api/generated/allauth.ts` are produced from the real allauth endpoint by `scripts/generate-allauth-client.mjs`. `auth:web:client:generate` writes them atomically and `auth:web:client:check` verifies drift without modification.
- `openapi-fetch 0.17.0`, TanStack Query 5.101.4, React Hook Form 7.83.0, resolvers 5.5.7, Zod 4.4.3, `server-only` 0.0.1 and axe Playwright 4.12.1 are exact dependencies. `openapi-typescript 6.7.6` is the latest stable line compatible with the repository TypeScript 6 policy; 7.13.0 was rejected for its TypeScript 5-only peer.
- Browser CSRF bootstraps through official allauth config, uses only same-origin credentials and appends `X-CSRFToken` for unsafe methods. Query keys and no-retry auth mutations are centralized. `proxy.ts` is optimistic only; the protected server layout checks Django with forwarded Cookie and `no-store`.
- ADR 0016 records the same-origin, generated-contract and server-authoritative decisions. `config.settings.e2e` accepts only a UUID-named PostgreSQL database, an `lms-e2e-` Redis prefix and the ignored `apps/api/.local/e2e-mail` directory. The runner creates, migrates and drops that database, clears only its Redis keys, mail and `.local/e2e-results`, and refuses occupied ports 3000/8000 on Windows.
- The Playwright configuration starts Django and Next directly at `127.0.0.1:8000` and `127.0.0.1:3000` with `reuseExistingServer: false`, one Chromium worker, no trace/video/screenshot, and no browser storage of sessions or codes. It covers registration, mandatory email-code verification, logout/login, password reset, protected-route return, open-redirect rejection, CSRF rejection, keyboard focus order and axe WCAG 2.2 A/AA checks. The 13-test unit/component suite, all five browser cases, lint, strict typecheck, generated-client drift check, backend checks and production Next build pass.

## Compatibility correction

TypeScript 7.0.2 and ESLint 10.8.0 were installed temporarily and rejected after real peer-resolution evidence from `eslint-config-next`/`typescript-eslint`. The working selection is TypeScript 6.0.2 and ESLint 9.39.5 (ADR 0011). No parallel compiler was retained.

## Security result

`pip-audit` reported no known Python vulnerabilities. `pnpm audit --prod` initially identified one moderate and three high vulnerabilities inherited through Next's PostCSS/sharp dependencies. Root overrides pin `postcss@8.5.18` and `sharp@0.35.3`; the audit then reported no known vulnerabilities. pnpm still reports optional WASM peer warnings and intentionally blocks `unrs-resolver` lifecycle scripts; lint, tests and build pass without approving them. Reassess both on every Next upgrade.

## Validation evidence

- El 2026-07-29 se consultaron las guías oficiales de Next.js sobre `rewrites` y preservación de la barra final, y de openapi-fetch sobre serialización JSON. El BFF conserva ahora las rutas API con barra final antes de reenviarlas a Django, y el adaptador CSRF conserva `Content-Type` del `Request` generado antes de añadir `X-CSRFToken`.
- La matriz aislada `pnpm organizations:e2e` ejecutó 9 escenarios Chromium: autenticación existente, owner (alta, suspensión, reactivación, revocación y reincorporación), administrador sin controles sobre owners, aislamiento entre organizaciones y axe WCAG A/AA institucional. Pasó después de corregir la navegación post-login, el reenvío con barra final, los encabezados JSON y la actualización de la tabla de membresías.
- El navegador integrado cargó visualmente el login local y el entorno de demostración quedó disponible en `127.0.0.1:3000`/`127.0.0.1:8000`. Las cuentas demo reproducibles se generan sólo con `DEBUG=True` mediante `pnpm organizations:demo`; el README documenta su uso y las credenciales.
- La validación de la superficie de currículo sigue abierta, pero su corte actual está probado: `pnpm catalog:test` pasó 66 pruebas Python con 79.75% de cobertura, `pnpm web:typecheck` y `pnpm web:lint` pasaron, y `pnpm catalog:visual` ejecutó 14 escenarios Chromium aislados. Entre ellos están la jerarquía curricular, creación visual de disciplina, asignatura, tema, objetivo y concepto, reducción y reubicación visible de un tema, rechazo visible de ciclos de prerrequisitos, asociaciones ordenadas tema/objetivo–concepto y axe WCAG 2.2 A/AA; la base temporal, Redis y correo temporal se eliminaron al finalizar.
- El 2026-07-29 se completaron las rutas REST de detalle, actualización, archivado/restauración y movimiento para disciplinas, asignaturas, temas y objetivos. `Topic.objects.move()` sustituye el método de instancia deprecado por Treebeard 6. La interfaz permite crear un tema hijo y la prueba Chromium aislada verificó el flujo; queda pendiente completar la edición visible de todas las entidades y las listas completas de prerrequisitos antes de cerrar la fase.
- El 2026-07-29 la página de prerrequisitos pasó a listas accesibles para asignaturas y conceptos: muestra relaciones entrantes y salientes, permite varias aristas con tipo y justificación, y excluye entidades archivadas. Chromium verificó la creación y el rechazo del ciclo de conceptos; la repetición completa posterior pasó 14/14.
- La validación de cierre local pasó: `pnpm check`, `pnpm test` (50 pruebas Python, cobertura 80.92%; 16 pruebas Vitest), `pnpm organizations:test` (14), políticas (4), concurrencia (1), contrato OpenAPI sin drift y `pnpm web:build`.
- Django `check`: exit 0; `check --deploy` in development: exit 0 with five expected deployment warnings.
- Production-like `check --deploy`: exit 0 with a long non-secret placeholder key and `lms.invalid` host.
- Ruff lint/format, Pyright strict, pytest (36 tests, 91.95% coverage), ESLint, Prettier, `tsc`, Vitest (13 tests), Next build, production same-origin proxy smoke, isolated Playwright Chromium (5 tests) and isolated axe WCAG 2.2 A/AA (1 tagged test) have passed individually.
- `pnpm install --frozen-lockfile` and `uv sync --locked` pass. PostgreSQL 18.4
  and Redis 8.8.1 Docker Official Images are available through local Compose
  only, locked by Linux amd64 digest, loopback-published, authenticated and
  persistence-smoke-tested. No SQLite database, application container, Celery,
  S3 o cambio de remote fue creado por Codex; tampoco ejecutó `commit` ni
  `push`. El avance externo de Git observado durante la validación queda
  registrado en “Delivered scaffold”.

## Remaining risk / debt

- Security overrides for `postcss` and `sharp` are necessary compatibility debt until Next updates its own dependency pins.
- pnpm's optional WASM peer/build-script warnings are not hidden; they are non-blocking only because the checked toolchain passes without executing those scripts.
- `identity.0001` y el modelo de usuario permanecen inmutables. Cualquier cambio
  futuro exige ADR, plan de migración y evidencia PostgreSQL real.
- Redis 8 remains conditional for production pending a legal license choice and a production design for ACL users, rotation, TLS and network policy.
- django-allauth 65.18.0 exports phone patterns even when `ACCOUNT_PHONE_VERIFICATION_ENABLED=False`. `domain.identity.headless_urls` filters only those exported URL leaves before Django includes them; tests prove they are 404 and absent from generated OpenAPI. Reassess the shim on every allauth upgrade.
- The browser-only deployment intentionally omits allauth's optional `headless` extra because it installs `PyJWT[crypto]`; the installed distribution still provides, and tests prove, the supported browser-session headless routes and official OpenAPI schema through `headless-spec`. Re-evaluate this narrow dependency decision on every allauth upgrade.
- A production SMTP provider, a real reverse-proxy trust chain, administrative network restriction, social login, MFA and user-session inventory are intentionally deferred.
- The Windows production-smoke wrapper still needs process-tree cleanup before it can be CI evidence: `pnpm.cmd` can leave child Node processes after a wrapper stop. The isolated Playwright runner avoids that path by using direct Node server launchers and force-stopping only processes bound to its prechecked local ports.

## Next exact step

**Prompt 11 — Publicación inmutable: snapshots completos del curso, versiones publicadas, validación, retiro y experiencia de lectura.**

## Prompt 8 latest evidence

El 2026-07-29 `pnpm catalog:e2e` pasó 20/20 en Chromium aislado. Incluyó
creación y edición visible de área, disciplina, asignatura, tema, concepto y
objetivo por owner/author; reviewer, instructor y learner de solo lectura;
`POST` directo del revisor con cookie/CSRF que devolvió 403; URL
cross-organization, árbol, asociaciones, ciclos, archivado y restauración de
un concepto sólo después de retirar sus asociaciones y aristas, archivado
oculto al learner y axe WCAG 2.2 A/AA en las cinco rutas curriculares. La base
PostgreSQL, prefijo Redis y correo efímeros se limpiaron en `finally`.

El mismo día, `pnpm catalog:test` pasó 69 pruebas Python con 81.23% de cobertura,
`pnpm check`, `pnpm catalog:schema`, `pnpm catalog:client:check` y
`pnpm web:build` pasaron sin warnings. Las listas agrupadas `topic-concepts`, `objective-concepts`,
`subject-prerequisites` y `concept-prerequisites` permiten que las pantallas
curriculares eviten una carga N+1. La comprobación manual Chromium con las
cuentas demo verificó login, redirección y el currículo de
`organizacion-demo` con conteos, filtros y jerarquía visibles.

La revisión final añadió selectores explícitos de visibilidad por organización
y estado para áreas, disciplinas, asignaturas, temas, conceptos y objetivos.
Las vistas de lista aplican `DjangoFilterBackend` y ordenamiento permitido sólo
después de esa frontera; el esquema OpenAPI declara `search`, `status`,
relaciones y `ordering`, y el cliente generado quedó sincronizado. El reemplazo
de prerrequisitos conserva las aristas no modificadas, bloquea la organización y
el grafo antes de validar ciclos y sólo inserta, actualiza o retira el diff.
Una regresión `TransactionTestCase` adicional ejecuta dos escrituras Treebeard
simultáneas sobre la misma asignatura y confirma dos nodos válidos y
`find_problems()` vacío tras la serialización por bloqueo.

## Prompt 9 latest evidence

El 2026-07-29 se creó `domain.courses` con el generador oficial de Django y una
única migración inicial inspeccionada y aplicada en PostgreSQL 18.4. El dominio
mantiene `Course`, revisiones de autoría, historial de transiciones append-only,
módulos y unidades ordenados, y alineaciones explícitas con asignaturas, temas y
objetivos de `domain.catalog`. No se alteró `identity.0001`, no se copiaron roles
a `User`, `Group` ni almacenamiento del navegador, y una revisión aprobada no
se modela como publicación.

Se añadieron seis capacidades a la matriz central de organizaciones y todas las
decisiones de autorización atraviesan policies/services. Las escrituras usan
`transaction.atomic()`, `select_for_update()` y `expected_version`; los
conflictos devuelven un `409 revision_conflict` estable y conservan la edición
del usuario en la interfaz. La base protege slug reservado, unicidad por
organización, cardinalidad de asignatura principal, posiciones válidas y únicas,
transiciones inmutables y ausencia de borrado físico en la API. Dos
transacciones PostgreSQL reales probaron que una actualización concurrente se
guarda y la otra falla, y que la reordenación conserva una secuencia íntegra.

El contrato `/api/v1/organizations/{organization_slug}/courses/` cubre listado,
detalle, revisión, outline, readiness, metadatos, alineaciones, estructura,
archivado/restauración y flujo draft → in_review → changes_requested/approved.
Los `404` no revelan cursos, revisiones, módulos ni unidades de otra
organización. El esquema drf-spectacular se generó sin warnings y el cliente
TypeScript quedó sincronizado; el frontend consume únicamente esos tipos
generados y mantiene las decisiones de autorización en el servidor.
Como todas las vistas PATCH validan serializers explícitos sin `partial=True`,
drf-spectacular usa `COMPONENT_SPLIT_PATCH=False`: `expected_version` permanece
obligatorio también en el schema y el tipo TypeScript, no sólo en runtime.

Las cinco rutas Next.js —lista, creación, workspace, estructura y revisión—
fueron inspeccionadas en el navegador integrado con la cuenta owner de
demostración. A 1280 px mostraron los encabezados y controles esperados; a
390 px las cinco tuvieron `scrollWidth == clientWidth`. El editor de estructura
mostró los tres módulos y ocho unidades del curso de demostración sin
desbordamiento, y la consola no registró errores.

`pnpm courses:e2e` pasó 3/3 escenarios Chromium aislados: flujo completo
author/reviewer/owner, dos contextos con conflicto optimista visible y valores
preservados, edición y reordenación de módulos/unidades, alineaciones, archivo y
restauración por teclado, readiness, solicitud de cambios con foco en el
faltante, corrección, reenvío, aprobación, solo lectura por rol, visibilidad del
instructor, ocultamiento al learner, axe WCAG 2.2 A/AA, viewport de 390 px e
IDOR multinivel. La base PostgreSQL temporal, el prefijo Redis y el correo
temporal se eliminaron en `finally`.

`pnpm courses:demo` es idempotente y sólo funciona con `DEBUG=True`. Mantiene
los identificadores del curso `introduccion-calculo-diferencial`, su revisión
draft, tres módulos, ocho unidades y sus alineaciones; una prueba impide su uso
en configuración no development. La deuda intencional restante es mover una
unidad entre módulos, que no forma parte del contrato del Prompt 9. Contenido
semántico, publicación, enrolment, evaluación y delivery permanecen fuera de
este dominio y de esta fase.

El cierre hostil añadió regresiones directas para mass assignment,
`expected_version` ausente, slug inmutable, inmutabilidad de `in_review` y
`approved`, módulo sin unidad, unidad sin objetivo, referencias de catálogo
archivadas, relaciones entre organizaciones, objetivos no alineados y una
regresión N+1 que mantiene constante el número de consultas del outline al
cuadruplicar módulos y unidades. La suite de Courses pasó 17/17 con 79.03% de
cobertura aislada (`models` 88%, `services` 82%, `readiness` 78%, `policies`
75%, serializers 97%); la suite global pasó 86 pruebas Python con 80.46% y 18
pruebas Vitest. La ejecución
Chromium global pasó 23/23 escenarios y limpió su base, Redis y correo. Ruff,
Pyright (0 errores), ESLint, Prettier, TypeScript, Next build, OpenAPI sin
warnings, drift checks, `pip-audit` y `pnpm audit --prod` quedaron verdes.

## Acceso local persistente y experiencia institucional — 2026-07-29

- `bootstrap_local_access` crea o reconcilia únicamente en desarrollo la cuenta
  local solicitada y un espacio institucional real. Recibe la contraseña por la
  variable efímera `LMS_LOCAL_ACCESS_PASSWORD`, no la imprime, no la escribe en
  Git y evita recalcular el hash si ya coincide. `--exclusive` revoca otras
  membresías mediante el servicio de organizaciones sin borrar datos ni
  historial. La cuenta local quedó como owner de
  `espacio-academico-rmontoyac`; no necesita ejecutar los bootstraps demo.
- `pnpm dev:start`, `dev:status`, `dev:logs`, `dev:restart` y `dev:stop`
  administran Django y Next en procesos ocultos identificados, con estado y logs
  bajo `.local/dev` ignorado. PostgreSQL y Redis permanecen administrados por
  Compose. El objetivo operativo es que una revisión o tarea no detenga el
  entorno que el propietario está probando.
- El frontend adoptó una única base visual generada con shadcn/ui y Radix:
  blanco, grises fríos y azul sólo como énfasis. El sidebar es claro,
  colapsable y móvil; su estado activo usa una marca discreta y no bloques de
  color. El encabezado global dejó de duplicar el título de cada página.
- Currículo usa explorador jerárquico con inspector; cursos usa catálogo en
  filas y workspace; miembros usa directorio y diálogos; organizaciones e
  inicio académico usan listas de trabajo. La creación de áreas, disciplinas,
  asignaturas, conceptos, objetivos y temas ocurre en diálogos contextuales.
  Los formularios de curso, alineación, revisión y metadatos se compactaron con
  divisores, controles consistentes y acciones breves.
- El login reproduce la composición visual autorizada de
  `DuvanMontoya/Frontera-Matematica`: campo geométrico de investigación,
  ecuaciones, tipografía editorial y panel translúcido. Sólo se adaptó la
  identidad textual; formularios, CSRF, errores, recuperación, verificación y
  sesión siguen usando allauth/Django reales.
- `shadcn` se usó como generador fijado en `4.16.0` y se retiró del runtime con
  `eject`. Permanecen sólo componentes consumidos; se eliminaron componentes,
  `next-themes` y `sonner` sin consumidores. Las nuevas dependencias directas
  están fijadas exactamente y su evaluación/licencia está en
  `docs/research/DEPENDENCY_EVALUATION.md`.
- El micro-pulido final se realizó sobre las rutas reales con la cuenta local:
  inicio, organizaciones, resumen, currículo, asignatura, conceptos, objetivos,
  prerrequisitos, cursos, creación y miembros. Se compactaron encabezados,
  espacios, estados vacíos y formularios; las acciones de temas, conceptos,
  objetivos, membresías, historial y conflictos usan controles y diálogos
  coherentes, sin `window.confirm`. El editor semántico conserva su lógica y
  schema, pero adoptó los mismos tokens, superficies y estados del resto de la
  plataforma.
- Un Chromium aislado a 390 px recorrió once rutas autenticadas y confirmó
  `scrollWidth == clientWidth` en todas. La revisión visual detectó y corrigió
  el estrechamiento del inspector curricular móvil y la superposición de la
  acción del formulario de curso. Axe con WCAG 2 A/AA y 2.2 AA quedó sin
  violaciones en login y los flujos representativos de inicio, resumen,
  currículo, asignatura, prerrequisitos, creación de curso y miembros; también
  se corrigieron los dos contrastes detectados en avatar y acción destructiva.
- Después del último cambio pasaron Prettier, ESLint, TypeScript, las 27 pruebas
  Vitest y `next build` 16.2.12 con todas las rutas. La suite API global ya había
  pasado 113 pruebas con 82.69% de cobertura, `check` y verificación de
  migraciones. La sesión real quedó abierta y `pnpm dev:status` confirma Django
  en `127.0.0.1:8000` y Next en `127.0.0.1:3000`.

## Corrección de navegación, membresías y editor semántico — 2026-07-30

- En contextos con una sola organización, `/organizaciones` redirige al resumen
  institucional y el sidebar presenta la organización como identidad estática,
  no como una acción que vuelve a abrir la misma pantalla. El resumen enlaza
  `Inicio` con `/estudiar`; el selector y la ruta de cambio se conservan sólo
  cuando existen varias organizaciones.
- El alta de miembros mantiene el contrato vigente: sólo incorpora cuentas
  registradas, activas y verificadas, sin inventar invitaciones ni un segundo
  sistema de identidad. La interfaz explica ese requisito, permite copiar la
  ruta real de registro, busca por correo y muestra el detalle seguro devuelto
  por la API. Se verificó el flujo completo en el navegador con una identidad
  temporal verificada y rol learner; la membresía, sus eventos, asignaciones,
  correo y usuario temporales se eliminaron inmediatamente después.
- El error de guardado del contenido provenía de la extensión de enlace de
  Tiptap: serializaba atributos HTML (`target`, `rel` y `class`) que el contrato
  canónico prohíbe. `CanonicalLink` conserva en JSON únicamente `href` y el
  `title` opcional; los atributos de seguridad se agregan sólo al renderizar.
  Los errores de schema ahora se deduplican y se presentan en español. El
  documento real con enlaces se guardó sin cambio semántico y la API confirmó
  que no creó una versión duplicada.
- Currículo, estructura de cursos, miembros y contenido recibieron un
  micro-pulido coherente con el sistema visual existente: menos texto técnico,
  jerarquía más compacta, estados y alertas consistentes, módulos y unidades
  escaneables, alineaciones agrupadas y barra de autoría adaptable. No se
  cambiaron rutas, arquitectura ni reglas de negocio.
- La revisión en el navegador integrado cubrió resumen, miembros, currículo,
  estructura y contenido en escritorio y a 390 px; las cinco rutas tuvieron
  `scrollWidth == clientWidth`. También se verificaron la redirección de
  `/organizaciones`, el alta y limpieza real de un miembro, el error controlado
  para un correo inexistente y el guardado del documento que antes fallaba.
- Pasaron Prettier, ESLint, TypeScript, las 31 pruebas Vitest, el build de
  Next.js 16.2.12 y las 24 pruebas de `domain.content`. Docker Desktop tuvo que
  reactivarse porque PostgreSQL no respondía en el primer intento; PostgreSQL y
  Redis quedaron saludables y la suite integrada pasó completa al repetirla.

## Prompt 11 — Publicación inmutable empresarial — 2026-07-30

- Git inicial: `main`, HEAD y `origin/main`
  `1272d5d35e4e05fb6f4799341bee64b0221b03b3`, worktree limpio. Git final
  conserva los mismos HEAD/remoto y sólo cambios locales de esta fase. Codex no
  ejecutó commit, push, add, reset, rebase, merge ni clean. Los servidores del
  usuario en 3000/8000 fueron preservados; E2E usó puertos y `.next` efímeros.
- ADR 0021 asigna a `domain.publishing` el canal mutable, releases/eventos
  append-only, snapshot completo, cadena SHA-256, retiro, clonación y biblioteca
  snapshot-only. Courses/content no importan publishing y publican sólo
  contratos estables de clonación.
- No hubo dependencia nueva. Se revalidaron Django 6.0.7, PostgreSQL 18.4,
  DRF 3.17.1, drf-spectacular 0.30.0, jsonschema 4.26.0, Ajv 8.20.0, Next
  16.2.12, React 19.2.8, TanStack 5.101.4 y Playwright/axe bloqueados.
- Capacidades nuevas: `course.release.publish`, `withdraw`, `history.view`,
  `create_draft` y `course.published.view`, evaluadas sólo por policies de
  organizaciones. Owner/administrator administran releases; learner lee.
- `CoursePublication`, `CourseRelease` y `CoursePublicationEvent` usan UUID,
  constraints/índices, lock version, current/previous pointers, métricas y
  eventos. `publishing.0002` instala triggers PostgreSQL que rechazan
  UPDATE/DELETE en releases y eventos; ORM y SQL directo están probados.
- `course-release-v1.schema.json` es Draft 2020-12, estricto y local. Snapshot
  determinista incluye curso, subject/objetivos, módulos/unidades/topics y
  documento semántico vigente; excluye HTML, secretos, actores, permisos,
  matrículas/progreso/evaluaciones. Límites, schema, canonicalización y digest
  se validan antes del INSERT.
- `publish_approved_revision` bloquea filas en `atomic`, exige aprobación,
  readiness/contenido, valida snapshot, numera contiguamente, encadena digest,
  inserta evento y actualiza el canal. Es idempotente para la misma revisión y
  seguro ante carreras. Retiro exige nota, conserva current release y sólo un
  release nuevo reactiva.
- `create_draft_from_release` clona estructura con UUID nuevos y documentos v1
  con digest conservado, sin historial previo; open draft y conflictos hacen
  rollback. Los servicios públicos viven en courses/content.
- API `/api/v1` cubre estado, publish, withdraw, releases, verify, create-draft
  y biblioteca list/detail/outline/unit. No hay DELETE ni snapshot entrante.
  IDOR devuelve 404, permisos 403, payload/version inválidos 400/409 y respuestas
  de lectura son `private, no-store`.
- OpenAPI fue generado/validado sin warnings y `platform.ts` quedó sincronizado.
  El schema genera tipos/validator Ajv de forma atómica; drift checks no escriben.
- Next agrega publicación, historial, retiro/draft confirmados y biblioteca con
  lector semántico, anterior/siguiente, MathJax local, código inert, tablas y
  bloques pedagógicos. Server Components usan no-store y TanStack desactiva
  retry/optimistic updates. No usa JWT, localStorage, sessionStorage o IndexedDB.
- Demo `introduccion-calculo-diferencial` fue publicado idempotentemente con
  servicios reales y verificado. `bootstrap_demo_publication` rechaza
  production. README y doce diagramas documentan uso, seguridad y operación.
- Chromium aislado recorrió release 1, historial, biblioteca, dos unidades,
  clonación, aprobación, release 2, independencia del snapshot, teclado, 390 px,
  axe y retiro. La revisión detectó/fijó estructura `<dl>`,
  conflicto de puertos/lock `.next` y cambio de identidad en un mismo contexto.
  E2E terminó 1/1 verde en 1.1 min y eliminó base, Redis, correo y procesos.
- Pytest publishing cubre schema, servicios, API y dos carreras; la suite
  integrada cubre release 2, reactivación, clonación, corrupción, triggers,
  roles e IDOR. Ruff, Pyright, cobertura ≥75 %, ESLint, Prettier, TypeScript,
  Vitest, Next build, auditorías y regresiones auth/organizations/catalog/
  courses/content forman el cierre obligatorio. La suite global cerró 126/126
  con 81,94 % de cobertura y Vitest 34/34.
- CI instala locks, levanta PostgreSQL/Redis, migra desde cero, valida triggers,
  schema/tipos/OpenAPI/drift, ejecuta suites/concurrencia, calidad, build,
  Chromium/axe y cleanup `always()`. No publica artefactos sensibles.
- Riesgo residual: la cadena detecta corrupción pero no es firma externa; la
  seguridad depende de control de acceso PostgreSQL y backups. Decisión
  irreversible: releases/eventos productivos no se corrigen in-place. Deuda:
  ampliar Playwright con visual regression estable; no bloquea contratos.
- Matriz completa: `docs/project/PHASE_11_ACCEPTANCE.md` (158 PASS).
- Trabajo no realizado: matrícula, progreso, evaluación, cache público,
  restauración de publication, media, búsqueda y Prompt 12.

## Remediación de navegación del frontend — 2026-07-30

- Se auditó el shell protegido y la matriz real de rutas antes de modificar la
  interfaz. El sidebar conservó su única implementación y ahora separa
  plataforma, institución, gestión académica, curso actual y administración.
- Currículo expone estructura curricular, conceptos, objetivos y
  prerrequisitos. Cursos expone listado y creación sólo con
  `course.authoring.manage`; dentro de un curso aparecen resumen, estructura,
  revisión y, únicamente con `course.release.history.view`, publicación.
  Biblioteca y miembros continúan filtrados por sus capacidades existentes.
- Las rutas dinámicas se derivan del `pathname` institucional ya autorizado; no
  se agregó estado, endpoint, ruta, permiso, capa de navegación ni regla de
  negocio paralela. Las unidades mantienen activa la sección Estructura y los
  releases la sección Publicación sin declarar como actual una URL distinta.
- El drawer móvil cierra al seleccionar enlaces principales o anidados y la
  navegación actual usa `aria-current="page"` sólo para coincidencias exactas.
  El modo colapsado conserva iconos y tooltips del componente existente.
- La revisión en el navegador integrado recorrió 15 pantallas reales en
  escritorio sin errores ni overflow: inicio, resumen institucional, las cuatro
  superficies de currículo, listado y creación de curso, resumen, estructura,
  revisión, publicación, biblioteca, contenido de unidad y miembros. En 390 px
  se verificaron el drawer, la ruta activa, el cierre tras navegar, Biblioteca,
  Publicación y `scrollWidth <= clientWidth`.
- Pasaron Prettier, ESLint, TypeScript, las 37 pruebas Vitest —incluidas tres
  nuevas sobre el contexto dinámico del curso— y el build de producción de
  Next.js 16.2.12. El backend persistente, iniciado con `--noreload` antes de
  Phase 11, entregaba capacidades antiguas; tras reiniciarlo, el contexto real
  de owner/administrator expuso Biblioteca y Publicación como establecen las
  policies, sin modificar datos ni permisos.
- La suite E2E aislada de publicación pasó 1/1 en Chromium: permisos de
  navegación para owner y learner, publicación de dos releases, historial,
  detalle inmutable, Biblioteca, lector de curso y unidades, 390 px, axe,
  clonación, retiro, 404 posterior y limpieza de base/Redis/correo/procesos.

Siguiente paso:

> **Prompt 12 — Matrículas y entrega del aprendizaje: acceso por curso, cohortes, progreso, continuidad, completitud y experiencia del estudiante.**

## Reestructuración de membresías, grupos y matrículas — en curso 2026-08-01

- **Estado:** implementación iniciada desde worktree limpio en `main`; no se han
  creado ramas, commits ni cambios de producción. La auditoría reprodujo
  `pnpm learning:test`: **19/19** en PostgreSQL real (2:31).
- **Brecha confirmada:** el vínculo actual `AcademicGroup → LearningCohort` no
  crea matrícula y la FK directa `CourseEnrollment.cohort` no conserva
  traslados. Las policies vigentes también resuelven capacidades al alcance de
  toda la institución para docentes.
- **Decisión:** ADR 0035 preserva identidad, rutas y FK v1 de lectura mientras
  introduce asignaciones históricas de roster y staff, sincronización opt-in,
  política de ventana heredable/excepciones y restricción docente por grupo de
  curso. No hay adopción automática de cohortes existentes.
- **Evidencia pendiente:** migración/backfill sobre PostgreSQL vacío y datos
  existentes; constraints/triggers, concurrencia, privacy matrix, contratos
  assessments/scheduling, OpenAPI/cliente, Chromium/axe/teclado/390 px y la
  batería transversal. La matriz viva está en
  `docs/project/MEMBERSHIP_ROSTER_ACCEPTANCE.md`.
- **Límite conocido durante la implementación:** las APIs de roster y matrícula
  ya aceptan paginación y búsqueda del lado del servidor, pero el selector de
  personas del asistente administrativo conserva el límite histórico de 100.
  La sustitución por búsqueda remota accesible permanece como aceptación
  pendiente; no se declara cerrado mientras exista esa carga acotada.

## Cierre local de correo, miembros, grupos y clases — 2026-08-01

- Sin tocar VPS ni producción, Hostinger recibió los registros exactos de
  Resend para `papyros.pro` y el dominio quedó `verified`. Se conservaron los
  registros web preexistentes. La clave completa existe sólo en el `.env` local
  ignorado y nunca se imprimió, copió a frontend ni incorporó al repositorio.
- Django admite SMTP Resend en desarrollo mediante `EMAIL_DELIVERY_MODE=smtp`,
  timeout y TLS/SSL excluyentes. Producción conserva validación fail-closed. Los
  envíos existentes reutilizan django-allauth y `domain.notifications`; las
  invitaciones ahora tienen alternativas texto/HTML e idempotencia, sin sistema
  de tokens paralelo.
- `organizations.0005` amplía invitaciones y perfiles con datos colombianos,
  edad calculada, sugerencia documental, WhatsApp, situación/nivel educativo,
  departamento, municipio, dirección, estrato y motivo. `User` no cambió.
- Las cuentas administradas pueden activarse manualmente sólo tras confirmar
  identidad y definir una contraseña temporal válida; la operación verifica el
  email, activa la cuenta, crea membresía y audita el método.
- ADR 0033 y `learning.0005` incorporan grupos académicos intercurso con roster
  de estudiantes, docentes y acompañantes. Las cohortes siguen siendo la unidad
  release-pinned y pueden vincular un grupo sin conceder acceso implícito. El
  formulario de cohorte permite escogerlo y el roster se guarda atómicamente en
  una sola solicitud y transacción.
- Se agregó `/clases`, con clases de curso y sesiones independientes filtradas
  por los permisos existentes. El aula del curso incluye una pestaña de clases
  en vivo y conserva el cálculo de progreso de asistencia en Django.
- Evidencia local: migraciones reales en PostgreSQL, Django check, Ruff,
  TypeScript, OpenAPI sincronizado, build optimizado de Next.js, learning 19/19,
  scheduling 16/16, organizations 30/30, notifications 7/7, auth-email 6/6 y
  frontend 51/51. Chrome real verificó Resend `verified`, el directorio con dos
  clases, el selector grupo-cohorte y, bajo identidad de estudiante matriculado,
  las dos clases dentro del curso y su contribución al progreso. El smoke real
  negoció STARTTLS y autenticó Django en `smtp.resend.com:587` sin enviar correo.
- Pendiente explícito: obtener autorización y destinatario para transmitir un
  único correo real y comprobar su recepción. No se realizó ningún despliegue.

## Remediación integral de estructura de cursos y asignaturas — 2026-08-02

- Se reprodujo en `calculo-integral` la contaminación con temas y objetivos de
  Cálculo Diferencial. La causa no era sólo visual: el workspace cargaba todo el
  catálogo institucional, aplanaba únicamente raíces de temas y permitía que la
  interfaz ofreciera selecciones que el dominio rechazaba después.
- El curso carga inicialmente sólo la asignatura principal. Las asignaturas de
  apoyo quedan disponibles de forma explícita y sus temas se solicitan bajo
  demanda al abrir su pestaña; no se descargan ni mezclan cientos de opciones.
  El árbol se recorre recursivamente y muestra la ruta de ancestros, por lo que
  los temas hijos también pueden seleccionarse sin perder contexto.
- La página de asignatura limita las asociaciones de conceptos a los temas de
  esa asignatura. Se sustituyó la composición extensa por métricas compactas,
  árbol jerárquico y acciones progresivas de tema/conceptos, conservando las
  operaciones y contratos existentes.
- Información, duración, temas y objetivos de una lección se guardan mediante
  un único PATCH y una sola transacción con control de versión. La validación y
  el reemplazo de alineaciones ocurren bajo el mismo lock; un dato ajeno a la
  revisión o asignatura provoca rollback completo, sin estados parciales.
- Añadir lección, clase en vivo y evaluación son ahora tres flujos separados.
  Clases y evaluaciones usan endpoints transaccionales especializados que crean
  y vinculan la actividad en una operación. La evaluación hereda título,
  descripción, duración, umbral y límite de intentos de su versión aprobada; la
  clase calcula su mínimo de asistencia desde su propia duración en servidor.
- Se reparó mediante el servicio de dominio la revisión local de Cálculo
  Integral: se retiraron las alineaciones de apoyo accidentales con Cálculo
  Diferencial y Precálculo, manteniendo Cálculo Integral como principal y sin
  borrar los temas reales `Antiderivada` y `Sumas de Riemann`.
- Evidencia verde: courses 24/24, assessments API 9/9, scheduling 21/21, Vitest
  focal 4/4, Ruff, ESLint, TypeScript, OpenAPI/cliente sincronizados,
  `makemigrations --check` sin cambios y build de producción Next.js. Chromium
  recorrió el curso y la asignatura con identidad autora; comprobó aislamiento,
  tema padre/hijo, metadatos heredados de evaluación, axe en el flujo de curso
  y ausencia de overflow a 390 px en ambas superficies.
- El E2E focal de cursos cerró 1/1 y las otras tres rutas del archivo ya habían
  cerrado verdes en la corrida integrada. La prueba de jerarquía curricular
  actualizada cerró 1/1; los seis escenarios CRUD encadenados restantes siguen
  usando contratos visuales anteriores (campos hoy dentro de diálogos) y no se
  declaran verdes. El producto y las APIs ejercitadas no fallaron, pero esa
  modernización transversal del archivo E2E queda registrada como deuda de
  pruebas preexistente fuera de esta remediación.
- No se añadieron dependencias, modelos ni migraciones, no se alteraron límites
  de dominio y no se realizó commit, push ni despliegue.

## Remediación integral de espacios curriculares — 2026-08-02

- Objetivos dejó de presentar el catálogo institucional completo: exige un
  contexto explícito de asignatura, conserva ese contexto en la URL y consulta
  únicamente sus objetivos y asociaciones visibles. La respuesta está paginada
  a 20 registros y las asociaciones/conceptos relacionados se leen por lotes
  acotados, sin volver a cargar miles de filas en segundo plano.
- Conceptos se define y presenta como diccionario institucional reutilizable,
  no como temario. Incluye búsqueda remota, filtro por uso en una asignatura,
  estado, conteo, paginación de 24 y tarjetas compactas; la estructura temática
  permanece en la página de cada asignatura.
- Prerrequisitos separa el grafo entre asignaturas del grafo entre conceptos.
  Sólo abre un objetivo a la vez, carga sus aristas directas e inversas y no
  muestra todos los candidatos hasta que existe una búsqueda intencional. La UI
  explica por qué otras asignaturas sí son candidatas en ese grafo y no las
  presenta como contenido ya asociado.
- Las cuatro superficies de currículo comparten una navegación compacta y
  semántica. Los filtros y editores se remontan al cambiar de contexto para
  evitar selecciones visuales obsoletas después de una navegación suave.
- API añadió filtros por asignatura, UUID de objetivos y extremos del grafo,
  además de ventanas `limit/offset` con `X-Total-Count`; conserva las lecturas
  legacy no paginadas para no romper consumidores existentes. UUID y límites se
  validan con error 400 y todas las consultas siguen confinadas a la organización.
- Evidencia: `domain/catalog/tests/test_api.py` 12/12 sobre PostgreSQL real;
  Ruff, ESLint, TypeScript, OpenAPI/cliente y `makemigrations --check` verdes.
  El E2E focal de Chromium pasó 1/1 con navegación suave, aislamiento explícito,
  390 px, ausencia de overflow y axe WCAG A/AA en objetivos, conceptos y ambos
  grafos de prerrequisitos.
- La sesión Chrome autenticada del usuario recorrió las tres rutas locales:
  Cálculo Integral mostró sólo `CNPER`; su filtro de conceptos devolvió 0 y el
  grafo de asignaturas mantuvo Cálculo Integral como objetivo, sin mostrar el
  grafo conceptual simultáneamente. No se modificaron datos durante esta revisión.
- La suite global del backend continúa con 320/348 pruebas verdes y 28 fallos de
  fixtures/policies preexistentes en varios dominios; la prueba focal de catálogo
  queda verde, pero no se declara la batería global resuelta. No se añadieron
  dependencias ni migraciones y no se realizó commit, push o despliegue.
