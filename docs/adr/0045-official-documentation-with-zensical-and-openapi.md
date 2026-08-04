# ADR 0045: Official documentation with Zensical and OpenAPI

**Status:** accepted — 2026-08-03.

## Contexto

El repositorio ya tenía ADR, documentos de arquitectura, runbooks, clientes
OpenAPI generados, pruebas y scripts. Faltaba un portal navegable y validado
que conectara esas fuentes y un camino reproducible para publicar el esquema.

## Decisión

Se usa Zensical `0.0.51`, fijado en el grupo de dependencias `docs` de
`apps/api/pyproject.toml`, para un portal de documentación en español bajo
`documentation/`. Se mantiene `drf-spectacular==0.30.0` como generador del
esquema API. Una copia reproducible de OpenAPI vive en
`documentation/docs/api/schema.yaml`.

Swagger UI y ReDoc se sirven mediante `drf-spectacular-sidecar`, bloqueado por
uv, por lo que la documentación API no depende de JavaScript de CDN flotante.
Las tres rutas interactivas de esquema/UI requieren sesión Django autenticada.
El portal se construye en modo estricto después de generar OpenAPI con
`--validate --fail-on-warn`.

Mermaid `11.16.0` se fija en las dependencias de desarrollo del workspace y se
copia desde `node_modules` durante cada build. `mermaid-render.js` usa esa
copia local antes que el cargador dinámico del tema, por lo que los diagramas
no descargan una versión flotante en tiempo de ejecución. Tiene licencia MIT;
el owner es el equipo de documentación. Se podrá retirar esta copia si
Zensical ofrece un renderizador local bloqueado que elimine dicha necesidad.

GitHub Actions valida y publica el sitio estático desde `main` usando el token
de Pages del repositorio. El flujo no contiene secretos de despliegue ni un
dominio personalizado inventado.

## Alternativas consideradas

- Se rechaza mantener endpoints manualmente porque divergen de serializers y rutas.
- Se rechaza una configuración de compatibilidad MkDocs para este portal nuevo:
  Zensical actual aporta TOML, búsqueda integrada y una ruta compatible para
  renderizar Mermaid localmente.
- Se rechaza un servicio comercial porque el repositorio puede construir y
  servir el portal de forma privada y reproducible.

## Consecuencias

Los cambios en rutas API, serializers, settings, scripts o páginas del portal
deben pasar `pnpm docs:check`. El portal estático documenta el contrato, pero
no modifica la autorización Django. La URL esperada de GitHub Pages se vuelve
pública sólo después de un despliegue correcto.

## Evidencia de versiones y compatibilidad

- [Zensical 0.0.51](https://pypi.org/project/zensical/) y su guía oficial de
  [diagramas](https://zensical.org/docs/authoring/diagrams/), consultadas el
  2026-08-03.
- [drf-spectacular 0.30.0](https://pypi.org/project/drf-spectacular/) y su
  documentación oficial de
  [Swagger UI y ReDoc](https://drf-spectacular.readthedocs.io/en/stable/readme.html),
  consultadas el 2026-08-03.
- Registro oficial de npm de `mermaid` `11.16.0` (licencia MIT), consultado el
  2026-08-03.
- Las licencias distribuidas verificadas en el entorno bloqueado son MIT para
  Zensical, BSD-3-Clause para drf-spectacular y BSD para su sidecar. El owner
  de estas dependencias es el equipo de plataforma; la alternativa de retiro
  es volver a las páginas estáticas sin interfaz interactiva ni diagramas.
