# ADR 0046 — Matemática integrada y lecciones fuente renderizadas en navegador

- Estado: aceptada localmente
- Fecha: 2026-08-04
- Responsables: plataforma académica

## Contexto

El documento académico ya conserva matemática como nodos semánticos
`inlineMath` y `displayMath`, valida el LaTeX con las mismas restricciones de
seguridad del schema y lo representa con MathJax local. Las extensiones de
Tiptap ya convierten `$…$` y `$$…$$` mediante `nodeInputRule` mientras la
persona escribe.

La superficie de autoría, sin embargo, ofrecía además botones `Fórmula` y
`Ecuación`, un panel MathLive, una selección duplicada entre matemática en
línea/bloque y una vista previa propia. Esa interfaz hacía parecer que la
matemática era un contenido separado y obligaba a abandonar el flujo natural
de escritura.

Las modalidades `latex_source` y `markdown_source` representan otra necesidad:
el archivo completo subido es la lección. Descargarlo no basta. La entrega debe
leer su versión privada fijada y mostrarla como un documento web, sin ejecutar
comandos, compilar TeX, generar PDF ni convertir la fuente en HTML persistido.

## Decisión

1. En documentos académicos, el autor escribe LaTeX directamente en el cuerpo:
   `$…$` para matemática en línea y `$$…$$` en un párrafo independiente para
   matemática en bloque.
2. Las reglas de entrada existentes convierten la sintaxis a los nodos
   canónicos `inlineMath` y `displayMath`. No se persiste HTML, MathML ni una
   segunda fuente de verdad textual.
3. Se eliminan del editor de documentos los botones y el panel específico de
   ecuaciones. MathLive no se usa en esta superficie.
4. MathJax permanece como renderer local en el editor, la vista previa, la
   biblioteca y la entrega al estudiante. La validación de seguridad y los
   límites del schema no cambian.
5. La modalidad `latex_source` de ADR 0042 sigue siendo un archivo `.tex`
   completo y excluyente. La entrega autorizada obtiene el descriptor temporal,
   lee como máximo 10 MiB y representa en React su título, secciones, párrafos,
   listas, bloques académicos y matemática con el MathJax local existente.
6. `latex_source` no ejecuta ni compila LaTeX. Entornos gráficos como TikZ se
   señalan de forma explícita y permanecen disponibles en la descarga de la
   fuente original; no se simula un resultado gráfico que el navegador no
   pueda demostrar.
7. `markdown_source` usa `react-markdown 10.1.0`, `remark-gfm 4.0.1` y
   `remark-math 6.0.0`. Omite HTML crudo, no carga imágenes remotas implícitas y
   delega la matemática al mismo MathJax local.
8. La fuente canónica continúa siendo el `AssetVersion` privado READY fijado en
   el snapshot. El texto leído existe sólo en memoria del navegador; no se
   persiste HTML derivado ni se crea un segundo documento semántico.
9. Las evaluaciones conservan sus contratos MathJSON/MathLive de ADR 0024. La
   retirada del panel separado afecta sólo la autoría de documentos; la lectura
   de fuentes se integra en la entrega snapshot-only de `domain.learning`.

## Consecuencias

- La autoría matemática ocurre en el mismo lugar que el texto y usa una
  convención portátil y visible.
- Los documentos existentes y sus versiones siguen siendo compatibles porque
  el schema y los nodos persistidos no cambian.
- Se añaden tres adaptadores MIT, exactos y reemplazables, únicamente para la
  lectura Markdown. MathLive continúa disponible donde el dominio de
  evaluaciones requiere una respuesta matemática estructurada.
- Una fórmula se corrige en el flujo normal del documento: se elimina el nodo
  y se vuelve a escribir su LaTeX. No existe un formulario paralelo.
- Un `.tex` completo se corrige reemplazando/versionando la fuente; su lectura
  web no modifica el archivo ni pretende ser un compilador TeX.

## Alternativas descartadas

- Mantener el panel MathLive como opción: duplica el flujo y contradice la
  escritura directa solicitada.
- Renderizar delimitadores crudos sin convertirlos a nodos: debilita el schema
  semántico y podría eludir la validación específica de LaTeX.
- Guardar HTML o MathML producido por el navegador: rompe la fuente de verdad
  JSON y la portabilidad de publicación.
- Compilar TeX o ejecutar TikZ en servidor/navegador: amplía de forma innecesaria
  la superficie de ejecución y contradice el objetivo de mostrar la lección.
- LaTeX.js: se descartó tras una prueba local porque los documentos reales usan
  clases y paquetes que no forman parte de su subconjunto compatible. Un éxito
  parcial habría presentado una lección incompleta como si fuese fiel.

## Fuentes oficiales consultadas

Consulta: 2026-08-04.

- Tiptap, Input Rules: https://tiptap.dev/docs/editor/api/input-rules
- Tiptap, Extension API y `addInputRules`:
  https://tiptap.dev/docs/editor/extensions/custom-extensions/create-new/extension
- MathJax, Typesetting Mathematics:
  https://docs.mathjax.org/en/latest/web/typeset.html
- react-markdown 10.1.0: https://www.npmjs.com/package/react-markdown
- remark-math 6.0.0: https://github.com/remarkjs/remark-math
