# Contribuir a LMS

La guía operativa de contribución está en la [documentación oficial](documentation/docs/contribucion/index.md). Antes de modificar el repositorio, lea `AGENTS.md`, el mapa de dominios y los ADR relevantes.

## Flujo mínimo

1. Revise el estado de Git y preserve cambios locales ajenos.
2. Mantenga las reglas de negocio en el dominio propietario y respete sus límites de importación.
3. Añada una migración y evidencia PostgreSQL cuando cambie datos o restricciones.
4. Regenere OpenAPI y revise el cliente generado si cambia el contrato HTTP.
5. Ejecute las validaciones de backend, frontend, dominio y documentación afectadas.

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

No confirme secretos, datos personales, `.env`, resultados generados ni credenciales de demostración reutilizables. No se documentan endpoints, roles, comandos o proveedores que el código no implemente.
