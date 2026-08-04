# Contribución

## Antes de modificar

1. Revise `AGENTS.md`, `docs/architecture/DOMAIN_MODULES.md` y el estado de Git.
2. No descarte cambios locales ajenos ni introduzca secretos, datos de producción o credenciales de prueba reutilizables.
3. Identifique el dominio dueño de la regla. Un controlador, un componente o una función genérica no reemplazan la política o servicio correspondiente.
4. Si altera un límite arquitectónico, registre primero un ADR y un plan de migración.

## Cambios de API, datos y documentación

- Todo cambio de modelo exige una migración revisada, `pnpm api:migrations:check` y evidencia PostgreSQL proporcional.
- Todo cambio de API se anota sólo cuando la inferencia OpenAPI no sea suficiente; se regenera el contrato y se revisa el cliente TypeScript.
- Toda página nueva se añade a `documentation/zensical.toml`, se escribe en español y se valida con `pnpm docs:check`.
- No documente rutas, variables, roles o proveedores inexistentes. Declare los límites no implementados de forma explícita.

## Antes de abrir una revisión

```powershell
pnpm api:format:check
pnpm api:lint
pnpm api:typecheck
pnpm web:format:check
pnpm web:lint
pnpm web:typecheck
pnpm docs:check
git diff --check
```

Ejecute también la suite del dominio y el recorrido navegador afectado. La CI de `main` es el control integrador; una compilación aislada no prueba permisos, concurrencia ni experiencia accesible.
