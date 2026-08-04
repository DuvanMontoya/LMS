# Referencia de configuración

Los ejemplos seguros están en `apps/api/.env.example`, `apps/web/.env.example`, `infrastructure/local/.env.example` e `infrastructure/mediacms/.env.example`. Nunca copie un `.env` real a Git, tickets o documentación pública.

## Backend Django

| Grupo | Variables reales |
| --- | --- |
| Base | `DJANGO_SETTINGS_MODULE`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `FRONTEND_ORIGIN` |
| Acceso local | `LMS_LOCAL_PLATFORM_OPERATOR_EMAIL`, `LMS_LOCAL_PLATFORM_OPERATOR_PASSWORD`, `LMS_LOCAL_PLATFORM_OPERATOR_FIRST_NAME`, `LMS_LOCAL_PLATFORM_OPERATOR_LAST_NAME` |
| PostgreSQL y Redis | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_CONNECT_TIMEOUT`, `POSTGRES_CONN_MAX_AGE`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_CACHE_DB` |
| Correo | `EMAIL_DELIVERY_MODE`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_TIMEOUT`, `DEFAULT_FROM_EMAIL`, `SERVER_EMAIL`, `EMAIL_MESSAGE_ID_DOMAIN`, `ACCOUNT_EMAIL_SUBJECT_PREFIX` |
| Assets | `ASSET_S3_REGION`, `ASSET_S3_INTERNAL_ENDPOINT`, `ASSET_S3_PUBLIC_ENDPOINT`, `ASSET_S3_ACCESS_KEY_ID`, `ASSET_S3_SECRET_ACCESS_KEY`, `ASSET_S3_FORCE_PATH_STYLE`, `ASSET_QUARANTINE_BUCKET`, `ASSET_PRIVATE_BUCKET`, `ASSET_S3_SERVER_SIDE_ENCRYPTION`, `ASSET_CLAMAV_HOST`, `ASSET_CLAMAV_PORT` |
| Observabilidad | `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_RELEASE`, `SENTRY_TRACES_SAMPLE_RATE`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`, `OTEL_SERVICE_VERSION`, `OTEL_DEPLOYMENT_ENVIRONMENT` |
| Integraciones | `INTEGRATIONS_MASTER_KEYS`, `INTEGRATIONS_ACTIVE_KEY_ID`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_AUTHORIZE_URL`, `GOOGLE_OAUTH_TOKEN_URL`, `GOOGLE_OAUTH_REDIRECT_URI` |
| LiveKit y LTI | `LIVEKIT_ENABLED`, `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_TOKEN_TTL_SECONDS`, `LIVEKIT_JOIN_BEFORE_START_SECONDS`, `LIVEKIT_JOIN_AFTER_END_SECONDS`, `LIVEKIT_ROOM_EMPTY_TIMEOUT_SECONDS`, `LIVEKIT_MAX_PARTICIPANTS`, `LIVEKIT_STUDENT_CAN_PUBLISH_AUDIO`, `LIVEKIT_STUDENT_CAN_PUBLISH_VIDEO`, `LIVEKIT_EGRESS_ENABLED`, `LMS_LTI_TOKEN_CLOCK_SKEW_SECONDS` |

Todas las credenciales anteriores son secretas. Los orígenes, puertos, booleanos y TTL son configuración; confirme su formato y obligación exactos en el ejemplo y en los validadores de `apps/api/config/settings` antes de desplegar.

## Frontend Next.js

`DJANGO_INTERNAL_ORIGIN` y `AUTH_SESSION_COOKIE_NAME` son sólo de servidor. Las únicas variables de navegador llevan el prefijo `NEXT_PUBLIC_`: `NEXT_PUBLIC_LIVEKIT_URL`, `NEXT_PUBLIC_MEDIACMS_AUTHORING_URL`, `NEXT_PUBLIC_SENTRY_DSN` y `NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE`. `NEXT_PUBLIC_` no vuelve seguro un secreto.

## Puertos locales

| Servicio | Puerto |
| --- | --- |
| Next.js | 3000 |
| Django | 8000 |
| Documentación Zensical | 8100 |
| PostgreSQL del proyecto | 5433 |
| Redis | 6379 |

Los servicios adicionales de Compose se inspeccionan con `pnpm infra:status`, `pnpm async:status`, `pnpm media:status` y `pnpm observability:status`; no asuma que un puerto está expuesto por una imagen de contenedor.
