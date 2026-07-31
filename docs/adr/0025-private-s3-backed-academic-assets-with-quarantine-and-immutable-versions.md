# ADR 0025: Private S3-backed academic assets with quarantine and immutable versions

- Estado: aceptada
- Fecha: 2026-07-31
- Responsables: plataforma académica

## Contexto

Content v1 sólo conservaba JSON semántico y publication fijaba ese documento
en un release. Imágenes, documentos, audio, video, subtítulos y datasets
necesitan identidad, historial, procesamiento y entrega privada sin convertir
`domain.content` en propietario de archivos ni hacer que un release dependa de
un objeto mutable.

El upload es entrada no confiable. Un nombre, extensión, `Content-Type`, ETag o
resultado del navegador no demuestran identidad ni seguridad. Los bytes deben
quedar inaccesibles hasta verificar tamaño, SHA-256, firma, MIME y límites de
formato con antivirus y herramientas reproducibles.

## Decisión

### Propiedad y grafo

`domain.assets` posee el asset lógico, versiones, variantes, sesiones/partes de
carga, jobs, eventos, gateway S3 y procesamiento. No importa content,
publishing ni learning. `domain.content`, `domain.publishing` y
`domain.learning` consumen sus contratos estables; la dirección inversa está
prohibida.

AWS S3 es el contrato productivo. Desarrollo y CI usan LocalStack sólo para S3.
MinIO fue rechazado porque su distribución comunitaria quedó archivada y no
mejora la fidelidad del contrato AWS. Se usa Boto3 directo: `django-storages`
1.14.6 no declara soporte oficial para Django 6/Python 3.13.

### Storage privado y upload

Existen dos buckets sin acceso público: quarantine, con expiración corta, y
private, con versioning. CORS sólo admite el origen configurado, multipart
incompleto expira y server-side encryption es obligatoria. Los object keys se
generan en servidor con UUID; nunca contienen el filename.

El backend firma POST simple o partes multipart, pero no recibe bytes. Cada
parte lleva checksum SHA-256; al completar se compara tamaño, checksum y
`HeadObject`. SHA-256 es la identidad autoritativa y ETag sólo evidencia el
protocolo S3. Complete y abort son idempotentes; expiración y máximo de partes
son límites de dominio.

### Cuarentena y procesamiento

Todo source inicia en quarantine. Un job Celery durable se despacha
`transaction.on_commit`, toma locks, tolera entrega duplicada y trabaja en un
directorio temporal que siempre limpia. ClamAV 1.5.3 falla cerrado. Malware
queda `rejected`, registra firma y elimina el objeto; nunca obtiene URL.

Pillow 12.3.0 valida imágenes, aplica EXIF orientation, rechaza animación y
decompression bombs, elimina metadata y produce thumbnail/medium/large. pypdf
6.14.2 valida páginas y rechaza cifrado. FFmpeg/ffprobe 8.1.2, compilado desde
source verificado por PGP, valida y normaliza audio, produce H.264/AAC y poster
para video. WebVTT se normaliza sin markup peligroso. CSV, JSON y texto exigen
UTF-8, límites estructurales y previews que neutralizan prefijos de fórmula.

El worker corre Linux no root, filesystem read-only, tmpfs temporal, sin
puertos, con red deshabilitada en FFmpeg y colas separadas. PostgreSQL conserva
estado; Redis es sólo broker.

### Inmutabilidad e integración

`Asset` es identidad editable/archivable sin hard delete. `AssetVersion`,
`AssetVariant` y `AssetEvent` son append-only; una versión terminal no vuelve a
procesarse. Reprocess agrega variantes de pipeline sin alterar source.
Promoción usa optimistic locking.

Content schema v2 añade `imageAsset`, `audioAsset`, `videoAsset`,
`documentAsset` y `datasetAsset`, siempre con `assetVersionId`; v1 permanece
válido y puede proyectarse a v2. `ContentAssetReference` materializa referencias
append-only y valida organización, estado, tipo, alt, transcript y captions.

Release schema v2 incorpora un manifest sin bucket, key ni URL. Sus versiones
fijadas participan en el digest. Un cambio posterior de `current_version` no
modifica el release. Learning sólo entrega descriptors temporales para el
release asignado y una matrícula efectiva; refresh valida la unidad en lote.

### Seguridad, límites y API

Capabilities institucionales gobiernan library, create, update, archive,
promote, reprocess, original y security details. Staff/superuser no omiten
policies ni antivirus. Los selectores filtran por organización y responden 404
anti-IDOR. Serializers cerrados evitan mass assignment. No existe DELETE,
upload remoto, SSRF, JWT ni almacenamiento browser. URLs firmadas expiran y
quarantine nunca se firma.

SVG, HTML, archives y ejecutables se rechazan. Los límites por clase están en
`domain.assets.limits`; cambios productivos requieren medir costo, memoria y
tiempo.

## Consecuencias

- Los uploads dependen de S3 compatible y el procesamiento de ClamAV/FFmpeg.
- La publicación es reproducible y un asset archivado sigue disponible para
  releases históricos autorizados.
- Se operan buckets y workers adicionales, con reconciliación explícita.
- LocalStack Community 4.14.0 quedó fijado por tag y digest como excepción
  local: las versiones nuevas requieren token/licencia. Debe reevaluarse antes
  de actualizar.
- Licencias directas: Boto3 Apache-2.0, Pillow MIT-CMU y pypdf BSD-3-Clause.
  FFmpeg se compila GPL por libx264; se debe conservar su oferta de source y
  avisos en toda distribución de la imagen.

## Decisiones aplazadas

HLS, CDN, OCR y transcripción automática no forman parte de esta fase. Una
evolución futura puede añadir variantes HLS y un origin/CDN conservando
`AssetVersion`, manifest y descriptors; requiere ADR, threat model, costos y
licencias propios.
