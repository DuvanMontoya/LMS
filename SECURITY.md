# Seguridad de LMS

## Alcance

LMS protege sesión Django, CSRF, autorización por membresía institucional, aislamiento de tenants, recursos académicos privados, evaluaciones y observabilidad. La arquitectura y controles actuales se describen en `docs/architecture/SECURITY_ARCHITECTURE.md` y en la documentación oficial.

## Reporte responsable

El repositorio no declara un canal público de reporte de vulnerabilidades. No publique detalles explotables, secretos, cookies, URL firmadas o datos personales en issues, commits o documentación. Use el canal privado establecido por la organización que opera el despliegue para coordinar la divulgación.

## Gestión de secretos

No añada claves, tokens, contraseñas, cadenas de conexión, backups o archivos `.env` a Git. Los archivos de ejemplo contienen únicamente nombres y valores de desarrollo no productivos. Una variable `NEXT_PUBLIC_` nunca debe contener un secreto.

## Verificación

Antes de publicar cambios, ejecute las comprobaciones de dominio afectadas, `pnpm api:check:production`, auditorías de dependencias y `pnpm docs:check`. Una vulnerabilidad encontrada debe corregirse de forma compatible y documentarse sin facilitar explotación.
