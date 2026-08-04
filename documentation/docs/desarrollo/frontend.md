# Frontend Next.js

## Arquitectura

`apps/web` contiene Next.js con App Router, React Server Components y componentes de cliente cuando hay interacción. Las rutas protegidas se organizan bajo `src/app/(protected)` y el control de acceso de interfaz se complementa siempre con la política Django. `src/proxy.ts` usa la cookie de sesión sólo como una señal optimista; la API decide de forma autoritativa.

Las rutas same-origin `/_allauth`, `/api/v1` y `/health` se reescriben al origen interno Django. El cliente server-only reenvía la sesión y las solicitudes mutables aplican CSRF. No hay JWT, Axios como contrato paralelo ni tokens en almacenamiento del navegador.

## Comandos verificados

```powershell
pnpm web:dev
pnpm web:build
pnpm web:lint
pnpm web:format:check
pnpm web:typecheck
pnpm web:test
pnpm web:test:e2e
```

El build también comprueba que los assets matemáticos locales requeridos estén preparados. Las pruebas del navegador usan Playwright y no reutilizan la base de desarrollo.

## Variables del navegador y servidor Next

| Variable | Uso | Exposición |
| --- | --- | --- |
| `DJANGO_INTERNAL_ORIGIN` | Origen interno de Next hacia Django. | Sólo servidor. |
| `AUTH_SESSION_COOKIE_NAME` | Nombre de cookie usado de forma optimista por `proxy.ts`. | Sólo servidor. |
| `NEXT_PUBLIC_LIVEKIT_URL` | Origen WSS público de LiveKit, sin ruta ni credenciales. | Navegador. |
| `NEXT_PUBLIC_MEDIACMS_AUTHORING_URL` | Portal privado de autoría de MediaCMS. | Navegador; no es entrega estudiantil. |
| `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_RELEASE`, `SENTRY_TRACES_SAMPLE_RATE` | Observabilidad de servidor opt-in. | Sólo servidor. |
| `NEXT_PUBLIC_SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE` | Observabilidad de navegador opt-in. | Navegador. |

La lista y los comentarios de formato están en `apps/web/.env.example`. Una variable con prefijo `NEXT_PUBLIC_` debe contener sólo datos que pueden ser públicos.
