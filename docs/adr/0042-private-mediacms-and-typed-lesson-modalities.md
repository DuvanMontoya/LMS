# ADR 0042 — MediaCMS privado y modalidades tipadas de lección

- Estado: aceptada localmente
- Fecha: 2026-08-03
- Responsables: plataforma académica

## Contexto

La LMS ya preserva dos límites necesarios: `CourseActivity` mantiene la
secuencia académica de `lesson`, `live_class` y `assessment`; y
`domain.content` fija el documento semántico versionado exclusivamente a una
`CourseUnit` de modalidad `document`, con referencias a `AssetVersion` READY
de `domain.assets`.
Crear una actividad distinta por vídeo, LaTeX, Markdown, PDF, diapositivas o
audio fragmentaría la secuencia y duplicaría contratos de finalización,
publicación y aprendizaje.

MediaCMS 8.1.3 incorpora catálogo, transcodificación, HLS, roles y LTI 1.3,
pero no es la autoridad de matrícula, release ni progreso de esta LMS. Su LTI
1.3 exige cookies seguras con HTTPS. El entorno solicitado es local HTTP y no
existe todavía un issuer, JWKS ni registro de plataforma verificable.

## Decisión

1. `CourseUnit.lesson_kind` pertenece a `domain.courses` como metadato
   estructural inmutable de una actividad `lesson`. Las opciones son
   `document`, `mediacms_video`, `latex_source`, `markdown_source`, `pdf`,
   `slides` y `audio`. No se añade un nuevo `ActivityType` ni se cambia la
   identidad de `CourseActivity`.
2. La entrega es excluyente y queda fijada en el release: `document` contiene
   sólo el JSON semántico; `mediacms_video` contiene sólo su binding LTI; y
   `latex_source`, `markdown_source`, `pdf`, `slides` y `audio` contienen sólo
   una referencia a una `AssetVersion` READY. `UnitLessonResource` pertenece a
   `domain.content` porque es el vínculo de autoría a assets, no estructura de
   curso. Valida organización, estado, MIME y extensión; audio exige además su
   variante privada de reproducción. Ningún release almacena buckets, object
   keys, URLs firmadas ni contenido adicional de otra modalidad.
3. Se instala localmente MediaCMS desde la etiqueta oficial exacta `v8.1.3`,
   commit `a3fe375a8302f5b26fac214ef2346dd92fec7361`. Su Compose se separa de
   `lms_internal`, sólo publica `127.0.0.1:8091`, deshabilita registro,
   catálogo público, compartir y originales, y guarda PostgreSQL, Redis,
   media y estáticos en volúmenes locales.
4. La modalidad `mediacms_video` abre el flujo de autoría de MediaCMS y se
   entrega sólo mediante el lanzamiento LTI de `domain.learning`, conforme a
   ADR 0043. Un enlace directo eludiría la matrícula y el release fijado, por
   lo que queda prohibido.
5. MediaCMS se consume sin modificar desde su fuente oficial y está licenciado
   bajo GNU AGPL-3.0. La responsable de plataforma debe realizar una revisión
   legal antes de una puesta en producción, de distribuir una imagen derivada o
   de cambiar el código que se ofrezca por red. Mientras tanto, esta instalación
   se limita a evaluación y autoría local. La alternativa de retirada es
   detener el Compose: la LMS conserva su contrato de assets privados y no
   contiene dependencias de código ni datos de MediaCMS.

## Consecuencias

- La interfaz ofrece las siete modalidades solicitadas sin crear estructuras
  académicas paralelas, y no presenta el editor semántico para modalidades que
  no sean `document`.
- El schema de publicación v6 usa una unión discriminada `delivery`. Los
  snapshots v1–v5 permanecen inmutables y el lector los adapta sólo en memoria
  para conservar la compatibilidad histórica.
- Lecciones existentes migran a `document`, por lo que sus revisiones y
  snapshots siguen siendo válidos.
- PDF se previsualiza sin convertir contenido; Markdown y LaTeX nunca se
  ejecutan ni se compilan en el servidor; PPTX se valida como paquete OOXML y
  se descarga. Una conversión a PDF requerirá una decisión separada sobre un
  conversor aislado y sus actualizaciones.
- La instalación local no altera DNS, Caddy, VPS, datos de producción ni la
  llave SSH. Las credenciales locales viven sólo en `.local/mediacms/.env`.
- El smoke local comprueba tanto la ausencia de enlace de alta en login como la
  página `Sign Up Closed` de la ruta directa, además de PostgreSQL, Redis,
  Django y la cuenta administrativa.

## Alternativas descartadas

- Seis `ActivityType` independientes: rompe el orden canónico y propaga reglas
  de publicación, progreso y finalización duplicadas.
- Guardar una URL de MediaCMS en JSON de contenido o en el release: elude
  autorización de matrícula, vence o revela la topología de almacenamiento.
- Activar LTI 1.3 en HTTP local: el propio MediaCMS marca sus cookies LTI como
  `Secure` y `SameSite=None`; sin HTTPS sería un flujo ficticio e inseguro.
- Usar etiquetas Docker `latest`: impide reproducir y auditar el despliegue.

## Fuentes oficiales consultadas

Consulta: 2026-08-03.

- MediaCMS, repositorio y capacidades: https://github.com/mediacms-io/mediacms
- MediaCMS, licencia AGPL-3.0 incluida en `LICENSE.txt` de `v8.1.3`:
  https://github.com/mediacms-io/mediacms/blob/v8.1.3/LICENSE.txt
- MediaCMS, release `v8.1.3` (2026-05-19):
  https://github.com/mediacms-io/mediacms/releases/tag/v8.1.3
- MediaCMS, configuración LTI 1.3 incluida en `cms/settings.py` de `v8.1.3`:
  https://github.com/mediacms-io/mediacms/blob/v8.1.3/cms/settings.py
- PostgreSQL Docker Official Image, etiqueta `17.2-alpine`:
  https://hub.docker.com/_/postgres
- Redis Docker Official Image: https://hub.docker.com/_/redis
