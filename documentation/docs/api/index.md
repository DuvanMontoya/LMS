# API OpenAPI

La plataforma expone un contrato OpenAPI 3 generado por drf-spectacular desde URLs, serializers, permisos y anotaciones `extend_schema`. El esquema es la referencia de endpoints: no se mantiene una lista manual paralela.

## Acceso local

Con Django iniciado y una sesión autenticada:

| Recurso | Ruta |
| --- | --- |
| Esquema YAML/JSON negociado | `http://127.0.0.1:8000/api/v1/schema/` |
| Swagger UI autocontenido | `http://127.0.0.1:8000/api/v1/docs/` |
| ReDoc autocontenido | `http://127.0.0.1:8000/api/v1/redoc/` |
| Copia reproducible del portal | [schema.yaml](schema.yaml) |

Las tres rutas Django requieren una sesión válida. Swagger UI y ReDoc se sirven con los archivos bloqueados de `drf-spectacular-sidecar`, no con una CDN flotante.

## Generación y validación

```powershell
pnpm docs:openapi:generate
pnpm docs:check
```

El primer comando ejecuta `manage.py spectacular --validate --fail-on-warn` y escribe `documentation/docs/api/schema.yaml`. El segundo además compila Zensical en modo estricto, por lo que un warning de enlace o referencia interna interrumpe el proceso.

## Autenticación y convenciones

La API usa la cookie de sesión de Django, mismo origen a través de Next.js y CSRF para solicitudes mutables. No use un header `Bearer` ni guarde tokens en el navegador. Los recursos institucionales incluyen el contexto de organización en su ruta; las políticas devuelven `403` cuando el actor conoce un recurso pero no puede operar, y `404` cuando la revelación de su existencia sería una fuga entre tenants.

Los endpoints se agrupan por los módulos de dominio. Las anotaciones existentes conservan `operationId`, parámetros, respuestas y serializers específicos donde la inferencia no basta.
