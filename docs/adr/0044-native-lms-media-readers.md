# ADR 0044 — Lectores nativos de la LMS para vídeo y documentos privados

- Estado: aceptada localmente
- Fecha: 2026-08-03
- Responsables: plataforma académica

## Contexto

La integración inicial de MediaCMS cumplía la autorización LTI 1.3, pero el
reproductor se veía dentro de un `iframe` con la interfaz completa de
MediaCMS. Eso añade un segundo árbol de interfaz, un salto de carga y una
cookie de navegador que la LMS no necesita para presentar una lección. De
forma análoga, el elemento `iframe` nativo para PDF delega la presentación en
un visor variable por navegador y no permite una experiencia de lectura
coherente.

La LMS sigue siendo la autoridad de usuario, matrícula, release y progreso.
MediaCMS mantiene la ingesta, transcodificación H.264/HLS y los archivos
privados; `domain.assets` mantiene las versiones inmutables de recursos
académicos. Ninguna de estas dos infraestructuras puede recibir una URL firmada
o un bearer en el DOM, un snapshot o el historial de navegación.

## Decisión

1. El aula entrega `mediacms_video` con un elemento HTML `video` propio de la
   LMS y HLS nativo cuando esté disponible; en los demás navegadores usa
   `hls.js` 1.6.16. La biblioteca sólo implementa MSE, ABR y recuperación de
   reproducción: no aporta un portal ni una segunda interfaz. Sus solicitudes
   permanecen en el mismo origen de la LMS.
2. La LMS expone una pasarela de streaming de mismo origen, limitada a la
   matrícula efectiva, release asignado, unidad de vídeo y rango solicitado.
   Para cada manifest o segmento obtiene internamente una capacidad RS256 de
   vida corta. MediaCMS recibe esa capacidad únicamente de la pasarela y la
   revalida contra la LMS antes de servir bytes. El navegador nunca recibe la
   capacidad, una cookie de MediaCMS, una URL de archivo ni un enlace HLS.
3. MediaCMS añade un endpoint interno de entrega nativa que acepta sólo la
   petición de la pasarela, compara el vídeo solicitado con el claim firmado y
   vuelve a consultar en la LMS la matrícula vigente antes de abrir el archivo
   HLS privado. Las rutas estáticas protegidas de la integración LTI heredada
   siguen verificando la misma capacidad. La revocación, suspensión o cambio
   de release se hace efectiva en la siguiente petición de manifest, segmento
   o rango.
4. PDF se dibuja dentro de la LMS con la display layer de `pdfjs-dist` 6.2.108
   y su worker local, no con un `iframe`, `object` ni visor del navegador. La
   superficie sólo muestra páginas, scroll natural y zoom estándar con
   Ctrl/⌘+rueda, sin barra de producto de terceros ni controles decorativos.
5. Los archivos LaTeX, Markdown y PPTX no se ejecutan ni se renderizan como
   HTML. Se presentan como recurso privado de una sola descarga; diapositivas
   PDF reutilizan el lector PDF. Audio usa el reproductor HTML nativo de la
   LMS. El encabezado de lección se elimina de la zona de entrega: la cabecera
   global ya comunica posición y título.

## Consecuencias

- El primer píxel del vídeo es un canvas de reproducción nativo de la LMS, no
  una pantalla de "autorizando" ni la interfaz de MediaCMS. Los controles son
  los del navegador, con `playsInline`, subtítulos cuando existan y sin
  descarga expuesta por la UI.
- Los manifest HLS se reescriben sólo a rutas same-origin de la LMS. Esto evita
  CORS permisivo y preserva Range, tipo MIME, ETag y caché privada sin guardar
  credenciales del proveedor en el cliente.
- La pasarela añade un salto de red frente a exponer el CDN directamente. Se
  acepta porque el alcance actual es local y privado; antes de producción se
  evaluará un edge autenticado que conserve exactamente estas comprobaciones y
  no emita URLs reutilizables.
- HLS requiere que el worker largo de MediaCMS tenga `mp4hls` configurado; una
  carga no se declara lista para aula hasta que exista manifest HLS. Se conserva
  el fallback explícito a MP4 codificado para medios históricos sin HLS, sin
  usar el original.

## Alternativas descartadas

- `iframe` LTI visible: conserva un portal ajeno, duplica navegación y exige
  una cookie de MediaCMS al navegador del alumno.
- URL MediaCMS directa o presignada en el componente: expone topología,
  permite reutilización y no vuelve efectiva la revocación por segmento.
- Video.js o un reproductor completo: resuelve controles que el producto no
  necesita, incrementa bundle y no mejora la autorización. `hls.js` aporta la
  parte técnica que el elemento `video` no cubre fuera de Safari.
- PDF embebido con `iframe`, `object` o visor nativo: presenta controles y
  comportamiento no gobernados por la LMS.

## Fuentes oficiales consultadas

Consulta: 2026-08-03.

- HLS.js, API y compatibilidad MSE/HLS: https://github.com/video-dev/hls.js
- HLS.js 1.6.16, Apache-2.0, npm registry:
  https://www.npmjs.com/package/hls.js/v/1.6.16
- PDF.js, display layer y worker: https://mozilla.github.io/pdf.js/getting_started/
- PDF.js 6.2.108, Apache-2.0, npm registry:
  https://www.npmjs.com/package/pdfjs-dist/v/6.2.108
