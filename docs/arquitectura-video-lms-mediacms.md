# Arquitectura de vídeo: LMS, MediaCMS y Contabo

Fecha de revisión: 2026-08-03. Esta revisión fue sólo de lectura: no se
crearon credenciales, buckets, contenedores ni se cambiaron datos.

## Decisión recomendada

Usar **el SSD local del VPS como almacenamiento operativo de MediaCMS** y el
Object Storage de Contabo como almacenamiento S3 privado para el LMS y para
copias/archivo. No montar el bucket como `MEDIA_ROOT` de MediaCMS ni activar
su acceso público.

MediaCMS actual guarda originales, codificados y HLS bajo su `MEDIA_ROOT`, y
su protección de reproducción se basa en Nginx/X-Accel sobre esos paths
locales. Un montaje FUSE/S3 para ese árbol añade una dependencia remota para
miles de segmentos HLS pequeños, complica escrituras de transcodificación y
debilita esa ruta de autorización. Por eso no es el primer despliegue correcto.

## Recursos comprobados

| Recurso | Estado actual | Lectura operativa |
|---|---:|---|
| VPS | 10 vCPU, 35 GiB RAM | Suficiente para LMS, MediaCMS y transcodificación moderada. |
| Disco local | 461 GiB libres de 492 GiB | Adecuado para la biblioteca activa y sus rendiciones. |
| Salida medida | ~480 Mbit/s sostenidos; planificar 360 Mbit/s | 40 alumnos a 720p (~2.8 Mbit/s) consumen ~112 Mbit/s; a 1080p (~4.5 Mbit/s), ~180 Mbit/s. |
| Object Storage | 250 GB en EU, 0 B usados, autoescalado desactivado | Capacidad inicial de archivo/respaldo; no basta para crecer sin control si se duplican todas las rendiciones. |
| Bucket existente | `archivos`, `https://eu2.contabostorage.com/archivos`, público inactivo | No exponerlo públicamente. Es S3 compatible, no una implementación idéntica a AWS S3. |

El VPS ya aloja la pila Laila y Caddy ocupa 80/443. Cualquier servicio nuevo
debe convivir con ella: Caddy sigue como único borde TLS y enruta un subdominio
de MediaCMS hacia una red Docker privada.

## Distribución propuesta

```mermaid
flowchart LR
  U[Alumno autenticado] --> L[LMS: matrícula y autorización]
  L --> M[media.dominio: MediaCMS privado]
  M --> N[Nginx interno: HLS protegido]
  N --> D[SSD local VPS: media_files]
  M --> B[Contabo S3 privado: archivo y respaldo]
  L --> Q[Contabo S3 privado: cuarentena LMS]
  Q --> W[Worker LMS: ClamAV y FFmpeg]
  W --> P[Contabo S3 privado: assets LMS]
```

### MediaCMS

- Subdominio: `media.tu-dominio` detrás del Caddy existente; nunca publicar
  directamente puertos de MediaCMS.
- Portal privado, registro público deshabilitado, descarga de originales
  deshabilitada salvo necesidad explícita, revisión editorial activada.
- HLS H.264/AAC: 360p (~0.8 Mbit/s), 480p (~1.4), 720p (~2.8) y 1080p
  (~4.5). Activar 1080p sólo para fuentes que lo justifiquen; 720p debe ser el
  perfil normal para la primera cohorte.
- Mantener `MEDIA_ROOT` sobre un volumen local persistente. El bucket recibe
  una copia verificable de originales y/o un respaldo periódico del catálogo,
  no es el path operativo HLS.
- No ejecutar transcodificaciones pesadas en paralelo con muchas cargas:
  comenzar con una sola tarea de encode y medir antes de aumentar.

### LMS

El repositorio ya tiene un diseño sólido, pero todavía no una conexión de
producción a Contabo:

- `domain.assets` es propietario de `AssetVersion`, cuarentena, Boto3,
  ClamAV, FFmpeg, URLs firmadas y entrega basada en matrícula/release.
- Los vídeos actuales se validan y normalizan a MP4/poster; HLS/CDN siguen
  expresamente aplazados.
- La configuración de producción rechaza endpoints S3 personalizados y
  credenciales estáticas; por tanto no puede apuntarse al endpoint Contabo
  simplemente llenando variables de entorno.
- No hay integración MediaCMS/LTI implementada en el LMS. MediaCMS no debe
  convertirse en una segunda autoridad de matrículas o de permisos.

La integración correcta requiere un adaptador de almacenamiento productivo que
soporte endpoint S3 compatible y secretos gestionados, más una prueba contra
Contabo de: multipart, SHA-256, `HeadObject`, copia, URLs firmadas, CORS,
versioning, lifecycle, cifrado solicitado y expiración. Contabo advierte que
su API no es completamente idéntica a AWS; ningún cambio debe pasar a
producción sin esa matriz.

## Buckets a crear cuando se autorice la implantación

No reutilizar `archivos` para todo. Crear nombres con el dominio/entorno real:

1. `lms-assets-quarantine-prod`: privado, expiración corta, CORS sólo para el
   origen LMS, sin URL de descarga.
2. `lms-assets-private-prod`: privado, versioning, acceso únicamente mediante
   URL firmada después de comprobar matrícula/release.
3. `mediacms-archive-prod`: privado, copia/archivo de MediaCMS; sin CORS de
   navegador ni acceso público.

Las claves S3 no van al repositorio, al frontend ni a capturas. Deben rotarse y
entregarse a contenedores mediante un mecanismo de secretos. Se necesita
además una copia fuera de la misma cuenta Contabo para poder hablar de backup
real ante pérdida total de cuenta/proveedor.

## Capacidad inicial y límites

MediaCMS conserva original, codificados y HLS; usar como estimación inicial
unas tres veces el tamaño de los originales dentro del almacenamiento operativo.
Con 461 GiB libres, reservar como máximo 300 GiB para MediaCMS hasta medir el
resto de las aplicaciones y mantener una alarma al 70/80 %. El bucket de 250
GB no debe recibir una copia completa ilimitada: si almacena toda la biblioteca
procesada, su margen práctico es aproximadamente 80 GB de fuentes antes de
considerar redundancia. Si guarda sólo originales, dura más pero continúa
siendo una capacidad finita que debe vigilarse.

Para 30--40 alumnos simultáneos no hace falta CDN el primer día. La prioridad
es HLS adaptativo, TLS, autorización de cada manifest/segmento y métricas.
Un CDN privado con URLs firmadas se evalúa después de una prueba real de 40
reproducciones y medición desde Colombia, no por anticipación.

## Secuencia antes de producción

1. Acordar el dominio y la frontera: MediaCMS será catálogo/transcodificador,
   mientras LMS conserva identidad, matrícula y decisión académica.
2. Crear los buckets privados y una credencial S3 de mínimo privilegio, una
   vez autorizado.
3. Implementar y probar el adaptador Contabo del LMS contra una cuenta/buckets
   de prueba; no relajar cuarentena, checksums ni URLs firmadas.
4. Desplegar MediaCMS en un Compose independiente, PostgreSQL/Redis propios,
   volumen local persistente y ruta Caddy `media.tu-dominio`.
5. Integrar explícitamente LMS--MediaCMS (preferiblemente LTI 1.3 o un
   contrato server-to-server diseñado para el LMS), sin compartir cookies ni
   dar al navegador claves de servicio.
6. Ejecutar pruebas reales: carga, transcodificación, acceso autorizado/no
   autorizado a manifest y segmentos HLS, 40 espectadores, restauración desde
   backup y rotación de credenciales.

## Fuentes técnicas verificadas

- Panel Contabo de esta cuenta: bucket `archivos`, región EU, 250 GB,
  0 B usados y acceso público inactivo.
- [Contabo: endpoint y credenciales S3](https://help.contabo.com/en/support/solutions/articles/103000275473-where-can-i-find-s3-connection-setting-for-object-storage-)
- [Contabo: alcance de compatibilidad S3](https://help.contabo.com/en/support/solutions/articles/103000275459-is-contabo-object-storage-compatible-with-s3-storage-)
- [MediaCMS: capacidades y requisitos](https://github.com/mediacms-io/mediacms)
- [MediaCMS settings actuales](https://raw.githubusercontent.com/mediacms-io/mediacms/main/cms/settings.py)
