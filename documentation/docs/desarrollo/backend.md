# Backend Django

## Estructura

`apps/api/config` contiene configuración, URLs, salud y observabilidad. `apps/api/domain` alberga los módulos del monolito: identity, organizations, catalog, courses, content, publishing, learning, scheduling, assessments, assets, events, discovery, notifications e integrations. Cada módulo conserva sus modelos, servicios, políticas, API y pruebas.

La API REST está bajo `/api/v1/`. Django usa PostgreSQL como autoridad de los hechos académicos. Redis se reserva para caché, límites de autenticación y broker; Celery no es dueño del estado de dominio.

## Comandos

```powershell
pnpm api:dev
pnpm api:check
pnpm api:database:check
pnpm api:migrate
pnpm api:migrations:check
pnpm api:migrations:plan
pnpm api:test
pnpm api:format:check
pnpm api:lint
pnpm api:typecheck
pnpm api:health
```

Los workers de calificación, media, eventos, notificaciones e integraciones se gestionan mediante los scripts de dominio y los comandos `pnpm async:*` o `pnpm media:*` correspondientes. Revise los [runbooks](../operacion/index.md) antes de intervenir una cola.

## Autenticación, errores y datos

La autenticación de DRF es `SessionAuthentication`. El formato de error proviene de `config.observability.api_exceptions.json_api_exception_handler`; el contrato exacto, códigos y serializers se publican en el [esquema generado](../api/index.md). Las vistas no deben añadir reglas de negocio: delegan en políticas y servicios transaccionales.

Los valores y ejemplos seguros para desarrollo están en `apps/api/.env.example`. Las variables productivas de correo, Redis, S3, LiveKit, LTI e integraciones se resuelven fuera de Git; sus nombres, no valores, se muestran en la [referencia](../referencia/index.md).
