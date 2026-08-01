# Auditoría acumulativa de completitud del producto

Fecha de inicio: 2026-07-31  
Alcance de cierre de esta fase: identidad, registro, miembros, configuración e
integraciones. Este documento es acumulativo: una aceptación previa en `PASS`
no elimina una deuda que pertenece a otro alcance.

## Método y evidencia inicial

- Se revisaron `README.md`, el roadmap, `STATUS.md`, los archivos
  `PHASE_*_ACCEPTANCE.md`, los ADR 0001--0029 y la arquitectura modular.
- La regresión inicial completó correctamente el 2026-07-31: `pnpm test`
  informó 255 pruebas Django y 48 pruebas Vitest aprobadas.
- La auditoría Chromium inicial verificó registro y login en
  `http://127.0.0.1:3000`. El formulario de registro está disponible sin una
  política dinámica visible; el login de una cuenta local preparada encontró
  un flujo allauth pendiente (HTTP 409), que confirma que no hay una
  experiencia de incorporación institucional integrada.
- Con la sesión local preexistente de propietario, `/organizaciones` redirigió
  correctamente al único contexto. El resumen institucional mostró una única
  edición de nombre. El enlace visible **Miembros** respondió 404 al abrir
  `/organizaciones/organizacion-demo/miembros`; el centro
  `/administracion/configuracion` también respondió 404. Los enlaces de una
  organización ajena respondieron 404, conservando la protección anti-IDOR.

| Dominio | Deuda o vacío | Evidencia | Severidad | Estado | Fase de cierre |
| --- | --- | --- | --- | --- | --- |
| Identidad y registro | No existe `PlatformRegistrationSettings`; el signup no se consulta dinámicamente por un adapter, ni soporta `closed`, `invite_only` y `open`. | `identity.0001` y `LMSHeadlessAdapter`; `/auth/registro` disponible en la auditoría. | Crítica | IN_PROGRESS | Prompt 16 correctivo |
| Identidad y activación | La activación se limita al flujo allauth genérico; no hay activación de invitación ni cuenta administrada con perfil institucional. | `domain.identity`, `domain.organizations.services`; login local devolvió flujo pendiente. | Crítica | IN_PROGRESS | Prompt 16 correctivo |
| Membresías | Sólo existe alta directa de una cuenta existente y verificada. Faltan invitaciones one-time, solicitudes públicas, perfiles, reenvío, corrección previa a activación y lifecycle de incorporación. | `organizations.models`, `services.py`, `MembershipListCreateView`. | Crítica | IN_PROGRESS | Prompt 16 correctivo |
| Gestión de miembros | Faltan rutas de nuevo miembro, invitaciones, solicitudes y detalle; faltan filtros/lifecycle/tipo, acciones de seguridad y CSV atómico. La ruta visible de miembros devuelve 404. | Árbol `apps/web/src/app`; auditoría Chromium y `MemberManagement`. | Crítica | IN_PROGRESS | Prompt 16 correctivo |
| Auditoría de membresías | `MembershipEvent` no cubre de manera append-only invitaciones, solicitudes, perfiles, configuración ni revocación de sesiones. | Modelo y `MembershipEventType` actuales. | Alta | IN_PROGRESS | Prompt 16 correctivo |
| Configuración global | No existe centro `/administracion/configuracion`, permiso global explícito, control optimista ni evento de cambios. | Auditoría Chromium: 404; no hay modelo/ruta correspondiente. | Crítica | IN_PROGRESS | Prompt 16 correctivo |
| Configuración institucional | Sólo se edita el nombre de la organización. Faltan `OrganizationMembershipSettings`, política de dominio, rol predeterminado, caducidad y versión optimista. | Resumen institucional auditado; `Organization` no contiene settings one-to-one. | Crítica | IN_PROGRESS | Prompt 16 correctivo |
| Integraciones | No existe `domain.integrations`, conexión, secreto cifrado, OAuth state/PKCE, health check durable ni UI/API para proveedores. | Inventario de `apps/api/domain` y búsquedas de modelos requeridos sin coincidencias. | Crítica | IN_PROGRESS | Prompt 16 correctivo |
| Integraciones externas reales | No hay credenciales, tenant Google ni claves reales autorizadas; no se debe simular esa validación. | Entorno local y alcance del encargo. | Alta | OPEN | Operación autorizada posterior; esta fase sólo valida stubs/contratos. |
| Assets y media | AWS/IAM/KMS reales, CDN, HLS, OCR y transcripción siguen aplazados. | `STATUS.md` Phase 15; ADR 0025. | Media | OPEN | Fase de media/operación posterior |
| Búsqueda, notificaciones y observabilidad | Existen módulos heredados (`events`, `discovery`, `notifications`, observabilidad) fuera de este correctivo; requieren auditoría funcional específica y no se extenderán aquí. | ADR 0026--0029 y commits heredados; el STATUS vigente aún sitúa Prompt 16 anterior como siguiente paso. | Media | OPEN | Auditoría de operaciones posterior |
| Riesgos de plataforma heredados | Licencia/operación Redis, overrides de `postcss`/`sharp`, SMTP productivo, trust chain de proxy, MFA y gestión de sesiones productiva permanecen explícitos. | `STATUS.md`, sección "Remaining risk / debt". | Media | OPEN | Seguridad y operaciones posteriores |
| Escala administrativa heredada | Selectores administrativos limitados a 100 registros no sustituyen búsqueda remota/paginada para organizaciones grandes. | `STATUS.md`, Phase 12. | Baja | OPEN | Escala administrativa posterior |

## Límites de esta fase

No se cerrarán despliegue, búsqueda, observabilidad, calendario, clases,
asistencia, comunicaciones, tareas ni generación de IA. Los riesgos de la tabla
siguen visibles aunque el módulo técnico asociado tenga pruebas históricas en
verde.

## Actualización correctiva — 2026-07-31

La implementación posterior a esta auditoría cerró los vacíos estructurales de
registro, incorporación, configuración y credenciales. La evidencia no se
confunde con validación de terceros ni con rutas que aún no tienen una matriz
Chromium propia.

| Aceptación | Estado | Evidencia actual | Pendiente concreto |
| --- | --- | --- | --- |
| Registro dinámico y backend `closed`/`invite_only`/`open` | PASS | Adapter allauth, configuración versionada, APIs y pruebas Django. | E2E de los tres modos. |
| Invitaciones, cuentas administradas, joins, perfiles y sesiones | PASS | Servicios transaccionales, hashes, eventos append-only, permisos y 273 pruebas API. | E2E integral de cada variante. |
| CSV de invitaciones | PASS | UTF-8, seis columnas exactas, 500 filas, errores por fila, preview de sesión y confirmación atómica; prueba API. | E2E de carga de archivo en Chromium. |
| Configuración de plataforma y organización | PASS | Rutas/API, lock optimista, control de permisos y navegador local. | Axe dedicado y viewport 390 px. |
| Integraciones y secretos | PASS local | AES-GCM, AAD, PKCE/state, rotación, health checks, masking, OpenAPI, centro separado por proveedor, pruebas explícitas y 11 pruebas con adaptadores simulados. | Stub E2E oficial y cuentas externas autorizadas. |
| Gestión de miembros profesional completa | PASS local | Directorio con registro explícito de estudiante/persona, filtros remotos por búsqueda/estado/rol/tipo/orden, rutas dedicadas de invitaciones y solicitudes, ficha con perfil/roles/lifecycle/sesiones/recuperación, activación administrada inactiva y CSV transaccional; Chromium y 26 pruebas del dominio. | E2E de las acciones mutantes y medición móvil/axe. |
| Integraciones externas reales | DEFERRED | No se inventaron credenciales ni resultados externos. | Tenant y credenciales autorizadas por la organización. |
| Accesibilidad integral nueva y 390 px | IN_PROGRESS | Labels, fieldsets, diálogos y navegación por teclado se revisaron en Chromium; las regresiones existentes contienen axe. | Ejecución axe y medición 390 px sobre todas las rutas nuevas. |

La siguiente auditoría no debe tratar los elementos `IN_PROGRESS` o `DEFERRED`
como evidencia de aceptación cerrada.

## Matriz de aceptación del Prompt 16 — actualización 2026-07-31

La matriz separa implementación y evidencia. `BLOCKED` no significa que se haya
ocultado una falla: el runner Chromium aislado alcanzó repetidamente el límite
de compilación en frío de Next antes de completar toda la batería nueva. Sus
bases, colas, correo y procesos efímeros se limpiaron al finalizar cada intento.

| # | Criterio | Estado | Evidencia o bloqueo exacto |
| ---: | --- | --- | --- |
| 1 | Registro acumulativo de deuda | PASS | Este documento conserva deuda fuera de fase. |
| 2 | Registro público dinámico | PASS | Settings, adapter allauth y Chromium en `closed`/`invite_only`/`open`. |
| 3 | Backend bloquea signup cerrado | PASS | Adapter servidor y pruebas de settings. |
| 4 | Invite-only funciona | PASS | Sesión de invitación validada por backend y UI pública. |
| 5 | Invitación de cuenta existente | PASS | Servicio idempotente, roles/perfil y prueba de aceptación. |
| 6 | Invitación de cuenta nueva | PASS | Enlace hash-only y aceptación tras verificación. |
| 7 | Cuenta administrada | PASS | Usuario inactivo, contraseña inutilizable y activación. |
| 8 | Admin no conoce contraseña | PASS | No hay campo de contraseña administrativa ni lectura de credencial. |
| 9 | Tokens one-time y hasheados | PASS | Digest SHA-256, expiración y respuestas sin token. |
| 10 | Expiración | PASS | Materialización transaccional y prueba de invitación vencida. |
| 11 | Reenvío | PASS | Servicio, evento y envío después del commit. |
| 12 | Revocación | PASS | Servicio, estado terminal y evento append-only. |
| 13 | Public join | PASS | Ruta pública, sesión de join y policy institucional. |
| 14 | Aprobación | PASS | Servicio de review crea membresía sólo al aprobar. |
| 15 | Rechazo | PASS | Acción de rechazo y estado terminal de solicitud. |
| 16 | Membership en momento correcto | PASS | Flujos no crean membresía antes de aceptación/activación/aprobación. |
| 17 | Perfiles institucionales | PASS | Perfil one-to-one, campos requeridos y notas restringidas. |
| 18 | Invariantes de roles | PASS | Policies, owner protegido y pruebas de dominio. |
| 19 | CSV masivo | PASS | Preview UTF-8, 500 filas, errores por fila y confirmación atómica. |
| 20 | Lifecycle | PASS | Suspend/reactivate/revoke individual y bulk transaccional. |
| 21 | Revocación de sesiones | PASS | Endpoint con capability y evento. |
| 22 | Auditoría append-only | PASS | Eventos y guardas PostgreSQL. |
| 23 | IDOR falla | PASS | Selectores por organización y pruebas cross-organization. |
| 24 | Mass assignment falla | PASS | Serializers cerrados y servicios explícitos. |
| 25 | Configuración global | PASS | Singleton versionado y ruta administrativa protegida. |
| 26 | Configuración organizacional | PASS | One-to-one, normalización y lock optimista. |
| 27 | Control optimista | PASS | `expected_version`, 409 y refresh de `lock_version` en UI. |
| 28 | Centro de configuración | PASS | Rutas separadas y navegación visible. |
| 29 | `domain.integrations` | PASS | App de dominio sin romper fronteras existentes. |
| 30 | Secretos cifrados autenticados | PASS | AES-GCM, AAD, key id, nonce y ciphertext separados. |
| 31 | Rotación de claves | PASS | Servicio y comando de re-cifrado. |
| 32 | Plaintext fuera de API | PASS | Serializers/OpenAPI no incluyen secret, token ni digest. |
| 33 | Google OAuth contra stub | BLOCKED | Stub aislado implementado; Chromium no completó la batería por compilación en frío. |
| 34 | State/PKCE/expiry | PASS | Servicios y pruebas de seguridad OAuth. |
| 35 | Calendar contra stub | BLOCKED | Requiere cierre de E2E aislado pendiente. |
| 36 | Meet contra stub | BLOCKED | Requiere cierre de E2E aislado pendiente. |
| 37 | Drive contra stub | BLOCKED | Requiere cierre de E2E aislado pendiente. |
| 38 | YouTube contra stub | BLOCKED | Requiere cierre de E2E aislado pendiente. |
| 39 | OpenAI contra stub | BLOCKED | Adaptador y stub existen; falta evidencia Chromium completa. |
| 40 | Gemini contra stub | BLOCKED | Adaptador y stub existen; falta evidencia Chromium completa. |
| 41 | DeepSeek contra stub | BLOCKED | Adaptador y stub existen; falta evidencia Chromium completa. |
| 42 | Modelos dinámicos | PASS | Adaptadores listan respuestas de proveedor, sin catálogo fijado. |
| 43 | Modelos no hardcoded | PASS | No hay selección productiva fija ni aliases `latest`. |
| 44 | Health checks async | BLOCKED | Servicio/Celery y polling implementados; falta cierre E2E con worker aislado. |
| 45 | Disconnect | PASS | Servicio elimina secreto y conserva evento/estado. |
| 46 | Masking | PASS | Sólo se muestra últimos cuatro; nunca la clave. |
| 47 | Logs sin secretos | PASS | No se registran credenciales, tokens ni plaintext. |
| 48 | Sentry sin secretos | PASS | No se añade captura de secretos ni argumentos sensibles. |
| 49 | OpenAPI sin secretos | PASS | Snapshot regenerado y serializers de salida cerrados. |
| 50 | Cliente TypeScript regenerado | PASS | Generado desde schema Django actual. |
| 51 | Interfaz de miembros completa | PASS | Directorio, alta, invitaciones, solicitudes, ficha, filtros y bulk. |
| 52 | Configuración coherente | PASS | Reglas y enlace público visibles desde configuración institucional. |
| 53 | Integraciones coherentes | PASS | Cards separadas y estados/acciones explícitos. |
| 54 | Chromium durante implementación | PASS | Rutas locales de miembros, configuración e integraciones inspeccionadas. |
| 55 | Problemas visuales documentados/corregidos | PASS | Registro, aceptación y seguimiento de salud ajustados. |
| 56 | Axe | BLOCKED | La matriz nueva no cerró por el límite del runner aislado. |
| 57 | Teclado | BLOCKED | La matriz nueva no cerró por el límite del runner aislado. |
| 58 | 390 px | BLOCKED | La matriz nueva no cerró por el límite del runner aislado. |
| 59 | Migración limpia | PASS | Múltiples bases PostgreSQL E2E vacías aplicaron todas las migraciones. |
| 60 | Sin migraciones pendientes | PASS | `identity.0002`, `organizations.0002-.0004` e integraciones aplican. |
| 61 | Regresiones anteriores | PASS | `pnpm api:test` (278/278), `pnpm web:test` (48/48) y `pnpm check` terminaron verdes. |
| 62 | Sin capas paralelas | PASS | Ownership preservado en identity, organizations e integrations. |
| 63 | Sin generación IA | PASS | Sólo health/model listing, sin generación facturable. |
| 64 | Sin afirmar conexión real | PASS | Sólo contratos/stubs locales; no hay tenant ni credenciales externas. |
| 65 | Sin commit/push | PASS | No se ejecutaron operaciones Git mutantes. |

**Resultado:** la fase no está cerrada. No debe declararse lista para una
auditoría de profundidad II hasta convertir los criterios 33 y 35--41, 44 y
56--58 en evidencia Chromium reproducible y verde.
