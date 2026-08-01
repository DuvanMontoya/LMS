# ADR 0030: Governed onboarding and organization integrations

- Estado: aceptada
- Fecha: 2026-07-31
- Responsables: plataforma académica

## Contexto

La plataforma ya usa `identity.User`, django-allauth en modo browser session,
CSRF, `organizations.Membership` y roles institucionales. El alta directa de
una cuenta previamente verificada no resuelve la política global de registro,
invitaciones, cuentas administradas, solicitudes de ingreso ni perfiles
institucionales. Tampoco existe una frontera para credenciales externas que
evite mezclar secretos con contenido, releases, sesiones o configuración web.

La auditoría acumulativa está en
`docs/project/PRODUCT_COMPLETENESS_AUDIT.md`. La consulta del 2026-07-31
confirmó que django-allauth soporta `DefaultAccountAdapter.is_open_for_signup()`
también en headless browser; su propia documentación indica que las
invitaciones pertenecen a una aplicación de invitaciones y pueden integrarse
desde ese adapter. La documentación oficial de Google exige state y el flujo
web server para OAuth. PyPI publicó `cryptography 49.0.0` como versión estable,
con soporte declarado para Python 3.13 y licencia Apache-2.0 OR BSD-3-Clause.

## Decisión

### Ownership

- `domain.identity` conserva `User`, email, credenciales, autenticación,
  activación, recuperación, sesiones y `PlatformRegistrationSettings`.
  `identity.0001` y el modelo de usuario no se alteran.
- `domain.organizations` conserva `OrganizationMembershipSettings`,
  `MembershipInvitation`, `OrganizationJoinRequest`,
  `OrganizationMemberProfile` y los eventos append-only del lifecycle. El
  servicio de organizaciones aplica roles, perfiles y membresías sólo al
  momento de aceptación o aprobación correcto.
- `domain.integrations` es una frontera nueva generada con `startapp`. Posee
  conexiones, grants OAuth, credenciales cifradas, capabilities, health checks,
  revocación, rotación y adapters. Puede consultar contratos estables de
  organizaciones; los dominios académicos no lo importan.

### Registro e incorporación

`PlatformRegistrationSettings` es singleton con `signup_mode` (`closed`,
`invite_only`, `open`), versión optimista y auditoría. Un `ACCOUNT_ADAPTER`
real consulta la fila en cada solicitud; cerrar el registro no depende de
ocultar el formulario ni requiere reiniciar Django. La verificación de email
permanece obligatoria y no es editable desde UI.

Las invitaciones usan tokens criptográficamente aleatorios, enviados sólo como
parte del enlace. PostgreSQL conserva exclusivamente `SHA-256(token)`, expiry,
estado y metadatos mínimos; APIs, admin, logs, OpenAPI y tareas no devuelven el
token. Un marcador de sesión Django de vida corta enlaza el enlace abierto con
el signup/activación allauth, sin JWT ni almacenamiento del navegador.

`Membership` no se crea al emitir una invitación o solicitud. La aceptación de
una cuenta existente requiere la sesión autenticada del email invitado. Una
cuenta nueva queda vinculada a la invitación y se activa tras confirmar email.
Una cuenta gestionada obtiene contraseña mediante activación limitada por token,
sin que el administrador la conozca. Solicitudes públicas sólo crean una
membership tras aprobación institucional.

### Configuración y eventos

Los cambios de configuración y lifecycle pasan por servicios transaccionales
con `expected_version`; una versión obsoleta devuelve `409 revision_conflict`.
`MembershipEvent` se vuelve append-only y puede ser institucional, incluso
antes de que exista membership. Los eventos conservan datos operativos mínimos,
nunca contraseñas, tokens ni notas administrativas.

### Secretos e integraciones

`cryptography==49.0.0` aporta `AESGCM`. Las claves maestras llegan sólo por
`INTEGRATIONS_MASTER_KEYS` (key IDs y Base64), nunca desde `SECRET_KEY`.
Cada secreto almacena key ID, nonce único y ciphertext; su associated data
incluye organización, proveedor y conexión. La rotación cifra otra vez y un
management command permite re-encryption. Las credenciales no son serializadas,
no se incluyen en argumentos Celery y se redactan en logs/Sentry.

Google Workspace usa authorization-code server-side con state one-time,
PKCE, redirect URI exacta, scopes mínimos e incremental authorization. OpenAI,
Gemini y DeepSeek usan claves por organización y validan/listan modelos contra
sus endpoints de listado, nunca mediante generación. Health checks son objetos
durables despachados después del commit; Celery recibe sólo su UUID y PostgreSQL
es la autoridad.

## Alternativas rechazadas

- Guardar roles de organización en `User`, `Group`, sesiones, formularios
  genéricos o storage de navegador.
- Permitir signup por una bandera de frontend o con un setting de proceso que
  exija reinicio.
- Persistir tokens de invitación/OAuth en texto plano, imprimirlos para tests o
  enviarlos en argumentos Celery.
- Usar `SECRET_KEY`, Fernet no versionado, cifrado sin autenticación o una clave
  hardcoded para credenciales de proveedores.
- Implementar Google domain-wide delegation, service accounts o generación de
  IA sin tenant y credenciales reales autorizadas.
- Convertir una cuenta administrada en usuario con contraseña administrada o
  exponer una operación de lectura/copia de API key.

## Consecuencias

- Aparecen nuevas migraciones para `identity`, `organizations` e
  `integrations`; deben funcionar desde PostgreSQL vacío y no tienen efectos
  retroactivos sobre membresías existentes.
- El entorno local/CI necesita claves de integración de prueba explícitas. La
  ausencia de credenciales reales permite pruebas con stubs, no una afirmación
  de conexión externa real.
- Los adapters conservan tiempos de espera, errores redactados y límites; una
  indisponibilidad de proveedor deja el health check durable como fallo seguro,
  sin bloquear la request ni revelar detalles.
