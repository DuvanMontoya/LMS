# ADR 0015: Headless authentication with django-allauth

- Estado: aceptada
- Fecha: 2026-07-28

## Contexto

La plataforma ya posee `identity.User` con UUID y correo normalizado como identidad
irreversible. La autenticación pública requiere registro, verificación obligatoria,
recuperación de contraseña, sesiones, CSRF y límites de abuso sin implementar
criptografía, códigos o estados de cuenta propios.

## Decisión

Se adopta `django-allauth[headless-spec]` 65.18.0 únicamente con
`allauth`, `allauth.account` y `allauth.headless`. El único cliente publicado es
`browser`; sus rutas oficiales son `/_allauth/browser/v1/...` y las rutas internas
de allauth permanecen bajo `/accounts/`. `HEADLESS_ONLY=True` evita las vistas
headed de login y registro.

El navegador usa sesiones Django almacenadas en PostgreSQL y cookies `HttpOnly`,
`SameSite=Lax` y `Secure` en producción. CSRF permanece activo y el decorador
oficial browser de allauth inicializa la cookie mediante `get_token()`. No se
habilita el cliente `app`, `X-Session-Token`, JWT, refresh tokens, social login,
MFA, perfiles ni roles.

El correo es obligatorio y se verifica por el mecanismo oficial de código:
tres intentos, 900 segundos y reenvío limitado por allauth. La recuperación de
contraseña también usa el código oficial, tres intentos, su timeout oficial de
180 segundos y nunca inicia sesión automáticamente. Las plantillas son locales,
en español, y los códigos no se registran en logs ni asuntos.

Redis 8 es una dependencia efectiva de autenticación, exclusivamente como caché
nativa de Django (`RedisCache`) para los rate limits de allauth. La base lógica
1 se reserva para claves `lms-auth`; las sesiones continúan en PostgreSQL. No hay
fallback a memoria ni fail-open: una caída de Redis degrada readiness y hace
fallar el límite de forma visible. El entorno local no confía en headers de proxy
(`ALLAUTH_TRUSTED_PROXY_COUNT=0`).

El frontend queda deliberadamente fuera de esta decisión: Prompt 6 integrará el
proxy same-origin y formularios. Existen dos contratos no fusionados: el OpenAPI
propio de DRF y el OpenAPI oficial de allauth.

`LMS_FRONTEND_URL` configura exclusivamente los enlaces de alta y recuperación
que allauth necesita incluir en correo neutral de prevención de enumeración. No
crea, publica ni presupone una interfaz Next.js; producción debe proporcionarla
antes de habilitar correo para usuarios reales.

## Consecuencias

Se incorporan tablas `account_*` mediante migraciones reales de allauth, sin
modificar `identity.0001`. El despliegue de producción debe proporcionar Redis y
SMTP explícitamente; el correo de desarrollo se escribe solo en una carpeta
ignorada. Antes de un proxy real se requiere decidir la cadena confiable y
sanitizar headers.

allauth 65.18.0 mantiene rutas `phone` en su árbol headless aunque
`ACCOUNT_PHONE_VERIFICATION_ENABLED=False`. El URLconf local filtra únicamente
esas hojas del árbol exportado antes de incluirlo: no copia vistas, no remapea
rutas, no agrega wrappers y conserva los nombres y vistas oficiales restantes.
Así, las capacidades no habilitadas no son resolubles ni aparecen en el OpenAPI
que allauth genera mediante resolución de URLs. Esta compatibilidad debe
revisarse al actualizar allauth.

La distribución incluye el módulo `allauth.headless` necesario para la estrategia
browser de sesiones. El extra opcional `headless` declara `PyJWT[crypto]`, una
capacidad JWT expresamente fuera de alcance; por ello se instala solamente
`headless-spec`, que aporta la especificación oficial sin una biblioteca JWT.
La carga de rutas, el schema y los flujos browser se prueban contra ese conjunto
exacto de dependencias y deben revalidarse en cada actualización de allauth.

El login interno de Django Admin sigue siendo una superficie administrativa
separada. `secure_admin_login` no se activa con `HEADLESS_ONLY`; producción deberá
restringir el admin por red, VPN, proxy o SSO administrativo futuro.
