# LMS

Plataforma académica propia orientada al estudio profundo y a la calidad académica. No adapta ningún LMS existente.

## Estado

El scaffolding reproducible y la infraestructura local mínima están completados: el repositorio Git local está en `main`, existen `apps/api` (Django) y `apps/web` (Next.js), y los lockfiles están versionados. Compose aporta solamente PostgreSQL y Redis para desarrollo local; no hay funcionalidades académicas, migraciones, workers ni despliegue productivo.

La primera migración ya define `identity.User`: UUID, email obligatorio/case-insensitive, Argon2id y administración interna. La autenticación pública usa la API oficial browser de django-allauth a través del mismo origen Next.js: sesiones Django, CSRF, verificación por código y Redis para rate limits; no hay JWT ni cliente móvil. La interfaz de acceso está en `/auth/*` y `/estudiar` se valida en Django desde Server Components. Usa `pnpm auth:web:client:check` para verificar el contrato generado; no se crean superusuarios automáticamente.

La fuente de estado es [docs/project/STATUS.md](docs/project/STATUS.md). La siguiente fase autorizada es Prompt 7: autorización y estructura institucional.

## Documentación

- Arquitectura y decisiones: `docs/architecture/` y `docs/adr/`.
- Investigación oficial y compatibilidad: `docs/research/`.
- Alcance, roadmap y estado: `docs/project/`.

Toda contribución debe seguir [AGENTS.md](AGENTS.md).

## Comprobaciones locales

Desde PowerShell ejecuta `./scripts/preflight.ps1`, `./scripts/bootstrap.ps1` y `./scripts/check.ps1`. `bootstrap` genera `infrastructure/local/.env` con secretos locales si falta, pero no inicia contenedores. Para operar los servicios usa `pnpm infra:init`, `pnpm infra:up`, `pnpm infra:smoke`, `pnpm infra:status`, `pnpm infra:down`; `pnpm infra:reset` elimina explícitamente los dos volúmenes locales. Consulta `infrastructure/README.md` antes de actualizar el lock de imágenes.

Con PostgreSQL y Redis locales activos, `pnpm auth:web:check` verifica el cliente OpenAPI, lint y tipos; `pnpm auth:web:test`, `pnpm auth:web:test:components` y `pnpm auth:web:test:a11y` ejecutan pruebas unitarias, de interfaz y accesibilidad aislada. `pnpm auth:web:test:e2e` crea y elimina una base PostgreSQL temporal, un prefijo Redis y correo de archivos para recorrer autenticación real en Chromium; no usa la base de desarrollo. `pnpm auth:web:smoke` construye Next y verifica las reescrituras del mismo origen, incluida la conservación de CSRF y la ausencia de proxy para `/admin/`.
