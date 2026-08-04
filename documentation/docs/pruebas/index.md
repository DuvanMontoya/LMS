# Pruebas y calidad

La automatización está repartida por dominio y se ejecuta desde los scripts de raíz. CI usa PostgreSQL y Redis locales temporales, instala Chromium y limpia únicamente recursos efímeros que crea.

## Controles principales

| Área | Evidencia |
| --- | --- |
| Backend | Ruff, Pyright, migraciones, pytest, cobertura mínima de 75 %, checks Django y `pip-audit`. |
| Frontend | Prettier, ESLint, TypeScript estricto, Vitest, Testing Library y build Next.js. |
| Contrato | Validación OpenAPI, cliente TypeScript generado y detección de drift. |
| Navegador | Playwright, axe WCAG 2.2 A/AA, teclado y rutas críticas en escritorio y 390 px. |
| Documentación | OpenAPI con `--fail-on-warn`, Zensical `--strict` y enlaces/anclas internos. |

## Ejecución dirigida

```powershell
pnpm api:test
pnpm web:test
pnpm web:build
pnpm content:test
pnpm learning:test
pnpm assessments:test
pnpm assets:test
pnpm docs:check
```

Los scripts específicos, por ejemplo `pnpm assessments:test:concurrency` o `pnpm assets:test:security`, existen para acotar una verificación sin sacrificar el conjunto completo de CI. Consulte `docs/architecture/TESTING_STRATEGY.md` para el detalle de fixtures, aislamiento y aceptación por dominio.

## Validar el portal

`pnpm docs:check` exige que la infraestructura local haya sido inicializada, porque genera el esquema desde Django. Después construye el portal desde cero con enlaces internos estrictos. No use el simple hecho de que exista Markdown como prueba de publicación.
