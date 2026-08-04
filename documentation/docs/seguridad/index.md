# Seguridad

## Controles implementados

- Sesión Django en cookie y protección CSRF para mutaciones; no hay JWT de navegador.
- Autorización por organización, membresía activa, capacidad y alcance; los roles no son atributos globales del usuario.
- Respuestas `404` para referencias cruzadas que no deben revelar existencia y serializers cerrados contra mass assignment.
- Versionado explícito y bloqueo transaccional para no perder modificaciones concurrentes.
- JSON semántico validado y renderizado sin HTML canónico ni ejecución de código arbitrario.
- Recursos privados: cuarentena, antivirus, validación de MIME/formato, variantes inmutables y entrega temporal autorizada.
- Claves de evaluación, tolerancias, semillas y payloads de calificación sólo en servidor.
- Observabilidad estructurada con reglas de privacidad para no registrar secretos, cookies, correos, URLs firmadas ni contenido excluido.

## Configuración que debe mantenerse fuera de Git

Las claves de Django, PostgreSQL, Redis, correo, S3, LiveKit, LTI, Sentry e integraciones se inyectan por variables de entorno. Los archivos `.env` están ignorados. Los `.env.example` sólo contienen valores de ejemplo no utilizables en producción.

## Riesgos y límites conocidos

La documentación y el código no sustituyen una revisión de configuración del proxy, TLS, backups, restauración ni control de acceso a los proveedores. Antes de producción, ejecute `pnpm api:check:production`, aplique migraciones antes del tráfico, pruebe restauración y mantenga las versiones de imagen verificadas.

No existe un canal público de reporte de vulnerabilidades registrado en el repositorio. Use el canal de contacto mantenido por la organización propietaria del despliegue; no se inventa una dirección de correo en esta documentación.
