# Solución de problemas

| Síntoma | Diagnóstico y solución | Verificación |
| --- | --- | --- |
| Falta `infrastructure/local/.env` al generar OpenAPI. | Inicialice infraestructura; el generador no acepta secretos improvisados. | `pnpm infra:init` |
| PostgreSQL o Redis no están listos. | Arranque el Compose del proyecto y revise su estado; no cambie puertos externos sin revisar configuración. | `pnpm infra:up`, `pnpm infra:status` |
| El esquema OpenAPI muestra warning. | Corrija serializer, queryset, parámetro o anotación de la vista. Los warnings no se suprimen. | `pnpm docs:openapi:generate` |
| El cliente generado tiene drift. | Genere el contrato por el script del dominio y revise el cambio; no edite archivos generados. | `pnpm platform:client:check` |
| Zensical falla en modo estricto. | Corrija el enlace, ancla o referencia reportada. Use enlaces relativos a páginas Markdown. | `pnpm docs:check` |
| Puerto ocupado. | Identifique el proceso por el puerto antes de detenerlo. Los scripts sólo deben detener sus propios procesos. | `pnpm dev:status` |
| Error CSRF o 401 en web. | Compruebe sesión, origen interno Django, cookie y petición same-origin; no agregue JWT. | `pnpm auth:web:check` |
| Un cambio devuelve 409. | Actualice la versión del servidor y combine deliberadamente. | Prueba de flujo específica del dominio |
| Un recurso no es entregable. | Confirme que terminó procesamiento y está `READY`; una carga en cuarentena no se distribuye. | `pnpm assets:smoke` |

Para problemas de dominio, use primero el comando de comprobación específico (`pnpm courses:check`, `pnpm learning:check`, `pnpm assessments:check`, entre otros). Los comandos globales no deben reemplazar la evidencia dirigida cuando se investiga seguridad, concurrencia o datos.
