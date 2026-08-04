# Despliegue

## Arquitectura prevista

Producción separa Next.js web, Django API y workers Celery Linux no-root. Un proxy termina TLS delante de web/API; PostgreSQL, Redis, S3 privado, correo, LiveKit y observabilidad se configuran como servicios dependientes. No se introduce Kubernetes ni se transforma el monolito en microservicios.

Antes de recibir tráfico, se deben aplicar migraciones, verificar salud, confirmar que las imágenes y dependencias bloqueadas son las aprobadas, y conservar copias de seguridad verificables. Un rollback no borra releases, matrículas, eventos ni versiones de calificación.

## Portal estático

El flujo `documentation.yml` compila una copia estática y conserva el artefacto
de Pages desde `main` sin secretos adicionales. La URL prevista es
`https://duvanmontoya.github.io/LMS/`; sólo se considera desplegada después de
que GitHub Actions concluya correctamente.

El workflow realiza instalación bloqueada, generación y validación OpenAPI con
configuración de pruebas, compilación estricta de Zensical y publicación del
artefacto. El despliegue aprovecha el token de GitHub Actions; no contiene
credenciales, dominio privado ni rutas `localhost` de producción.

El despliegue se activa sólo cuando la variable de repositorio no secreta
`DOCS_PAGES_ENABLED` tiene el valor exacto `true`. Esa protección mantiene
verdes las validaciones cuando la cuenta no dispone de GitHub Pages. Cuando el
plan permita Pages, configure Pages para compilar mediante GitHub Actions,
establezca esa variable y el siguiente push a `main` publicará el artefacto sin
modificar código.

## Configuración de aplicación

El despliegue de la aplicación necesita las variables productivas que ya exige Django: hosts y origen frontend, secretos de sesión, PostgreSQL, Redis, correo y los proveedores opcionales habilitados. Véase [Referencia de configuración](../referencia/index.md). No introduzca valores inventados en CI ni archivos versionados.

Los criterios de infraestructura, medias, workers y proxy se mantienen en `docs/architecture/DEPLOYMENT_ARCHITECTURE.md` y en los runbooks operativos.
