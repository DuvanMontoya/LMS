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
```

El comando se niega a ejecutarse fuera de `DEBUG=True`, marca los correos como
verificados y nunca debe usarse en producción. Puedes iniciar sesión con:

| Rol | Correo | Contraseña |
| --- | --- | --- |
| Propietario | `owner@demo.local` | `DemoLms!2026Organization` |
| Administrador | `administrator@demo.local` | `DemoLms!2026Organization` |
| Estudiante | `learner@demo.local` | `DemoLms!2026Organization` |
| Owner externo | `external@demo.local` | `DemoLms!2026Organization` |

La organización principal es `Organización de demostración` y se abre en
`/organizaciones/organizacion-demo`. El owner puede administrar miembros; el
administrador puede añadir personas pero no gestionar owners; el estudiante
solamente ve su contexto. La organización externa sirve para comprobar que una
URL ajena devuelve 404.

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
| Generar cliente OpenAPI | `pnpm platform:client:generate` |
| Comprobar drift OpenAPI | `pnpm platform:client:check` |
| E2E Chromium aislado | `pnpm organizations:e2e` |
| Suite completa de calidad | `pnpm check` y `pnpm test` |

El E2E usa una base PostgreSQL temporal, prefijo Redis temporal y correo
aislado; crea sus contraseñas aleatoriamente para el proceso y elimina los
recursos al terminar. No reutiliza las cuentas demo locales.

## Arquitectura y contratos

- Backend institucional: `apps/api/domain/organizations/`.
- OpenAPI de plataforma generado: `apps/web/openapi/platform.openapi.json`.
- Tipos derivados: `apps/web/src/lib/api/generated/platform.ts`.
- Rutas protegidas: `/organizaciones`, `/organizaciones/[slug]` y
  `/organizaciones/[slug]/miembros`.
- Decisión RBAC: [ADR 0017](docs/adr/0017-organization-scoped-role-based-access-control.md).

Consulta [docs/project/STATUS.md](docs/project/STATUS.md) para el estado real,
[AGENTS.md](AGENTS.md) para reglas de contribución y `docs/` para arquitectura,
seguridad, fuentes oficiales y roadmap.
