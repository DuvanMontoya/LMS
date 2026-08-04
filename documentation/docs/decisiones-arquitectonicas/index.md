# Decisiones arquitectónicas

Las decisiones se conservan en `docs/adr/` y se actualizan mediante ADR cuando cambia un límite material. Las primeras decisiones formalizan la base del sistema y las posteriores delimitan cada capacidad académica.

| ADR | Decisión |
| --- | --- |
| 0001–0006 | Monolito modular, monorepo, Django, Next.js, PostgreSQL y REST/OpenAPI. |
| 0007–0009 | Contenido semántico versionado, autenticación y trabajos en segundo plano. |
| 0014–0017 | Usuario personalizado, allauth headless, sesión de navegador y RBAC institucional. |
| 0018–0022 | Currículo, cursos, contenido, publicación inmutable, matrículas y progreso. |
| 0023–0025 | Evaluaciones, calificación avanzada y recursos S3 privados. |
| 0026–0030 | Outbox, búsqueda, notificaciones, observabilidad, onboarding e integraciones. |
| 0031–0044 | Agenda, LiveKit, grupos, responsabilidades, separación de deberes, grabaciones, medios y lectores nativos. |

## ADR 0045: Portal de documentación con Zensical

**Estado:** aceptada — 2026-08-03.

**Contexto.** El repositorio tenía documentación de arquitectura, ADR y runbooks, pero no un portal navegable ni una ruta reproducible que uniera el contrato OpenAPI, navegación, búsqueda y validación de enlaces.

**Decisión.** Se añade `documentation/` con Zensical `0.0.51` fijado en el grupo `docs` del proyecto Python. El portal usa TOML nativo, búsqueda local integrada, Mermaid `11.16.0` renderizado desde un archivo local, modo claro/oscuro y construcción estricta. `drf-spectacular==0.30.0` genera `schema.yaml`; Swagger y ReDoc usan el sidecar bloqueado, sin CDN flotante.

**Alternativas.** Se descartó duplicar endpoints en Markdown, depender de un servicio comercial de documentación y usar una integración MkDocs antigua cuando Zensical ofrece configuración actual y búsqueda integrada.

**Consecuencias.** Cambios de API deben pasar `pnpm docs:check`; el portal se publica como artefacto estático. La URL de Pages queda sujeta a una ejecución exitosa del workflow y no reemplaza la seguridad de las rutas Django.
