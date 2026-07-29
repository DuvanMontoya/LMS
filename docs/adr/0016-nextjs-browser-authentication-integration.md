# ADR 0016: Next.js browser authentication integration

**Estado:** aceptada — 2026-07-29.

## Decisión

El navegador utiliza un único origen y llama rutas relativas. Next.js reescribe
solamente `/_allauth`, `/api/v1` y `/health` a Django mediante `next.config.ts`;
no hay CORS, Route Handler catch-all ni destinos controlados por usuarios.
Django conserva por completo usuarios, cookies, sesiones PostgreSQL, CSRF,
rate limits y correo. Next.js no es un proveedor de identidad y no crea
cookies de autenticación.

El contrato browser se descarga desde el OpenAPI oficial real de allauth, se
normaliza y genera tipos con `openapi-typescript`. `openapi-fetch` consume esos
tipos en una frontera central. TanStack Query conserva únicamente estado remoto
efímero; React Hook Form y Zod ofrecen validación de experiencia mínima, sin
duplicar validadores de contraseña del servidor.

`proxy.ts` solo detecta de forma optimista la cookie de sesión para evitar
render innecesario de `/estudiar`. El layout Server Component consulta a Django
sin caché y constituye la comprobación autoritativa. No se usa Auth.js, JWT,
almacenamiento de navegador ni persistencia del caché de autenticación.

## Riesgos y alternativas

El OpenAPI upstream marca opcionales los request bodies de verificación y
restablecimiento aunque los endpoints de códigos los requieren. Hasta que
allauth corrija ese metadato, esas dos mutaciones usan `csrfFetch` encapsulado
en la misma frontera, con paths y bodies derivados del archivo generado; no se
distribuyen `fetch` ni DTOs manuales a componentes. Debe reevaluarse en cada
actualización de allauth.

Se rechazan CORS, Auth.js, un BFF de autenticación, proxy HTTP genérico, Axios,
JWT y almacenamiento local: todos duplicarían o debilitarían la autoridad de
Django. CSP completa, confianza de proxy productivo, MFA y autorización quedan
aplazadas a sus fases autorizadas.
