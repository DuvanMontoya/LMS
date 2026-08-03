# ADR 0041 — Assessment rich media and attempt-bound asset delivery

- Estado: aceptada localmente
- Fecha: 2026-08-03
- Decisores: arquitectura y dominio académico

## Contexto

El contrato público de una pregunta reutilizaba el documento semántico v1 y
las opciones sólo admitían texto. Aunque `domain.assets` ya procesaba recursos
privados y el renderer podía representar nodos multimedia, la autoría de
evaluaciones no podía fijarlos, no existía una relación durable con
`QuestionVersion` y un learner no recibía descriptores temporales autorizados.
El resultado era una brecha funcional para gráficas, diagramas, geometría,
audio o video y una falsa sensación de soporte multimedia.

QTI 3 permite contenido enriquecido, incluidas referencias multimedia, dentro
de una opción. W3C exige que una imagen informativa tenga alternativa textual y
que una imagen compleja disponga además de una descripción extensa que
transmita la información esencial.

## Decisión

1. `question-public-v1` conserva compatibilidad y amplía opcionalmente cada
   opción con `media`. La primera capacidad es una imagen READY fijada por
   `asset_version_id`, con `alt_text` obligatorio, pie opcional y descripción
   extensa opcional. El identificador de opción y la clave de scoring no
   cambian.
2. El enunciado pasa a validar `unit-document-v2`, que admite imágenes, audio,
   video, documentos y datasets como bloques de primer nivel. Los nodos
   semánticos heredados siguen validándose contra v1; no se relaja su contrato.
3. `domain.assessments` puede leer el contrato estable de `domain.assets`.
   Antes de guardar una revisión valida organización, tipo, estado ACTIVE y
   versión READY. Al aprobar crea `AssessmentAssetReference`, append-only y
   protegida por claves foráneas y triggers PostgreSQL.
4. Ningún bucket, object key ni URL firmada entra en `QuestionVersion`,
   `AssessmentVersion`, `AttemptItem` o release. El intento propio recibe
   descriptores de corta duración calculados desde sus snapshots públicos y
   puede renovarlos mediante un endpoint acotado al mismo intento.
5. La biblioteca de assets agrega las versiones de pregunta a su reporte de
   uso. Archivar un asset impide referencias nuevas, pero no rompe versiones
   históricas ya aprobadas.
6. La UI de autoría reutiliza el selector privado de recursos. Las opciones no
   admiten imágenes decorativas porque la imagen forma parte de la respuesta.
   Matching usa alternativas visuales con radio buttons; un `<select>` no puede
   representar contenido enriquecido de forma accesible.
7. Al alcanzar `expires_at`, el navegador envía el intento automáticamente. Si
   el navegador se cerró, el siguiente inicio finaliza primero el intento
   vencido bajo lock y sólo entonces aplica el límite e inicia otro intento.

## Consecuencias

- La evaluación puede representar gráficas, figuras y alternativas visuales
  sin hacer público el almacenamiento privado ni el grading snapshot.
- `assessments` adquiere una dependencia explícita y unidireccional hacia
  `assets`; `assets` no importa `assessments` y obtiene usos mediante su
  registro de providers.
- Los snapshots existentes continúan válidos porque multimedia es opcional y
  el documento v2 acepta los nodos heredados, que además conservan la
  validación estricta v1.
- QTI sigue siendo una guía de modelado; esta decisión no declara conformidad
  ni implementa importación/exportación QTI.

## Alternativas descartadas

- Guardar URLs firmadas en JSON: expiran, filtran detalles de almacenamiento y
  rompen la inmutabilidad semántica.
- Guardar sólo UUID sin FK: impediría conocer usos y permitiría romper historia
  fuera del dominio.
- Hacer públicas las imágenes: contradice el modelo S3 privado y la asignación
  release-pinned.
- Codificar imágenes como base64 dentro de la pregunta: duplica blobs, evade
  cuarentena/procesamiento y vuelve incontrolable el tamaño del snapshot.

## Fuentes oficiales consultadas

Consulta: 2026-08-03.

- 1EdTech QTI 3 Beginner's Guide, choice interaction y contenido multimedia en
  `qti-simple-choice`: https://www.imsglobal.org/spec/qti/v3p0/guide/
- 1EdTech QTI: https://www.1edtech.org/standards/qti
- W3C WAI Images Tutorial: https://www.w3.org/WAI/tutorials/images/
- W3C WAI Complex Images:
  https://www.w3.org/WAI/tutorials/images/complex/
