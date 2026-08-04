# Desarrollo local

## Requisitos bloqueados

El repositorio fija Node `24.18.0`, pnpm `10.33.2`, Python `3.13.13`, Django `6.0.7`, Next.js `16.2.12` y Zensical `0.0.51`. Use PowerShell 7+ y Docker Desktop. No sustituya los gestores: JavaScript se resuelve con pnpm y Python con uv.

## Preparar una copia limpia

```powershell
corepack enable
pnpm install --frozen-lockfile
uv sync --locked --directory apps/api --group docs
pnpm infra:init
pnpm infra:up
pnpm infra:status
pnpm api:migrate
pnpm platform:client:check
```

`pnpm infra:init` crea `infrastructure/local/.env` con secretos aleatorios locales e ignorados por Git. No copie ese archivo a otro entorno ni lo añada a la documentación.

Para el uso diario:

```powershell
pnpm dev:start
pnpm dev:status
```

La web se abre en `http://127.0.0.1:3000`; Django escucha en `http://127.0.0.1:8000`; PostgreSQL local usa `5433` y Redis `6379`. Use `pnpm dev:logs`, `pnpm dev:restart` y `pnpm dev:stop` para gestionar sólo los procesos de desarrollo que inició el proyecto.

## Interfaz de documentación

| Necesidad | Comando |
| --- | --- |
| Abrir y recargar el portal | `pnpm docs:serve` |
| Generar el contrato YAML | `pnpm docs:openapi:generate` |
| Construir producción | `pnpm docs:build` |
| Validar OpenAPI, enlaces y portal estricto | `pnpm docs:check` |

Los cuatro comandos usan las versiones bloqueadas de `apps/api/uv.lock`. La compilación sale en `documentation/site/`, que no se versiona.

## Convenciones

- El límite entre dominios se define en `docs/architecture/DOMAIN_MODULES.md`; un cambio material exige ADR.
- Las reglas están en servicios y políticas, no en controladores HTTP ni componentes React.
- Las modificaciones estructurales requieren migraciones revisadas y evidencia PostgreSQL.
- OpenAPI es el contrato de transporte y el cliente TypeScript es generado; no duplique DTOs a mano.
- No se usa almacenamiento del navegador para sesión, roles, permisos o progreso.
