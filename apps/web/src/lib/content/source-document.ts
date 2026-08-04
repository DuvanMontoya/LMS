export type LatexLessonBlock =
  | { caption?: string; code: string; language?: string; type: 'code' }
  | { level: 1 | 2 | 3 | 4; text: string; type: 'heading' }
  | { items: string[]; ordered: boolean; type: 'list' }
  | { latex: string; type: 'math' }
  | { text: string; type: 'paragraph' }
  | { rows: string[][]; type: 'table' }
  | {
      caption: string;
      environment: 'axis' | 'tikzcd' | 'tikzpicture';
      source: string;
      type: 'visual';
    };

export type LatexLessonDocument = {
  author?: string;
  blocks: LatexLessonBlock[];
  date?: string;
  title?: string;
};

const HEADING_LEVEL: Readonly<Record<string, 1 | 2 | 3 | 4>> = {
  chapter: 1,
  paragraph: 4,
  section: 2,
  subsection: 3,
  subsubsection: 4,
};
const CALLOUT_LABEL: Readonly<Record<string, string>> = {
  classicalbox: 'Resultado clásico',
  conjecturalbox: 'Escenario conjetural',
  conjecture: 'Conjetura',
  corollary: 'Corolario',
  definition: 'Definición',
  example: 'Ejemplo',
  experimentalbox: 'Exploración experimental',
  insightbox: 'Idea clave',
  keybox: 'Idea clave',
  lemma: 'Lema',
  proof: 'Demostración',
  proofmap: 'Mapa de la demostración',
  proposition: 'Proposición',
  question: 'Pregunta',
  remark: 'Observación',
  researchbox: 'Línea de investigación',
  rigorousbox: 'Desarrollo riguroso',
  theorem: 'Teorema',
  warning: 'Advertencia',
  warningbox: 'Advertencia',
};
const MATH_ENVIRONMENTS = new Set([
  'align',
  'align*',
  'equation',
  'equation*',
  'gather',
  'gather*',
  'multline',
  'multline*',
  'split',
]);
const TABLE_ENVIRONMENTS = new Set(['longtable', 'tabular', 'tabularx']);
const CODE_ENVIRONMENTS = new Set(['lstlisting', 'verbatim']);
const VISUAL_ENVIRONMENTS = new Set(['axis', 'tikzcd', 'tikzpicture']);
const IGNORED_ENVIRONMENTS = new Set(['titlepage']);

function unescapedComment(line: string) {
  for (let index = 0; index < line.length; index += 1) {
    if (line[index] !== '%') continue;
    let slashes = 0;
    for (
      let cursor = index - 1;
      cursor >= 0 && line[cursor] === '\\';
      cursor -= 1
    )
      slashes += 1;
    if (slashes % 2 === 0) return line.slice(0, index);
  }
  return line;
}

function bracedValue(source: string, command: string) {
  const start = source.search(
    new RegExp(`\\\\${command}(?:\\[[^\\]]*\\])?\\s*\\{`),
  );
  if (start < 0) return undefined;
  const open = source.indexOf('{', start);
  let depth = 0;
  for (let index = open; index < source.length; index += 1) {
    if (source[index] === '{' && source[index - 1] !== '\\') depth += 1;
    if (source[index] === '}' && source[index - 1] !== '\\') depth -= 1;
    if (depth === 0) return source.slice(open + 1, index).trim();
  }
  return undefined;
}

function readableText(value: string) {
  const normalized = value
    .replace(/\\(?:label|index)\{[^{}]*\}/g, '')
    .replace(/\\(?:cref|Cref|ref|eqref|autoref)\{([^{}]*)\}/g, 'referencia $1')
    .replace(/\\cite[a-zA-Z*]*\{([^{}]*)\}/g, '[$1]')
    .replace(/\\href\{([^{}]*)\}\{([^{}]*)\}/g, '$2 ($1)')
    .replace(/\\url\{([^{}]*)\}/g, '$1')
    .replace(/\\multicolumn\{[^{}]*\}\{[^{}]*\}\{([^{}]*)\}/g, '$1')
    .replace(
      /\\(?:emph|textbf|textit|texttt|underline|mbox|mathrm|textrm|textsf)\{([^{}]*)\}/g,
      '$1',
    )
    .replace(/\\bibitem(?:\[[^\]]*\])?\{[^{}]*\}/g, ' ')
    .replace(/\\(?:vspace|hspace)\*?\{[^{}]*\}/g, ' ')
    .replace(/\\fontsize\{[^{}]*\}\{[^{}]*\}/g, ' ')
    .replace(/\\(?:color|pagecolor)\{[^{}]*\}/g, ' ')
    .replace(
      /\\(?:Large|LARGE|large|huge|Huge|small|footnotesize|scriptsize|tiny|normalsize|sffamily|rmfamily|ttfamily|bfseries|mdseries|itshape|upshape|selectfont|centering|raggedright|raggedleft|par|vfill|hfill|newblock)\b/g,
      ' ',
    )
    .replace(/\\(?:LaTeX|TeX)\b/g, 'LaTeX')
    .replace(/\\\\(?:\[[^\]]*\])?/g, ' ')
    .replace(/\\\(/g, '$')
    .replace(/\\\)/g, '$')
    .replace(/\\\[/g, '$$')
    .replace(/\\\]/g, '$$')
    .replace(
      /\\(?:quad|qquad|enspace|noindent|smallskip|medskip|bigskip)\b/g,
      ' ',
    )
    .replace(/\\\\/g, ' ')
    .replace(/~/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return normalized
    .split(/(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g)
    .map((segment, index) =>
      index % 2 === 0 ? segment.replace(/[{}]/g, '') : segment,
    )
    .join('')
    .trim();
}

function tableRows(lines: string[]) {
  return lines
    .join(' ')
    .replace(
      /\\(?:toprule|midrule|bottomrule|hline|endhead|endfirsthead|endfoot|endlastfoot)\b/g,
      '',
    )
    .split(/\\\\(?:\[[^\]]*\])?/)
    .map((row) => row.split('&').map(readableText).filter(Boolean))
    .filter((row) => row.length > 0);
}

function mathValue(lines: string[]) {
  return lines
    .join('\n')
    .replace(/\\(?:label|tag)\{[^{}]*\}/g, '')
    .trim();
}

export function parseLatexLesson(source: string): LatexLessonDocument {
  const bodyMatch = source.match(
    /\\begin\{document\}([\s\S]*?)\\end\{document\}/,
  );
  const body = bodyMatch?.[1] ?? source;
  const lines = body.split(/\r?\n/);
  const blocks: LatexLessonBlock[] = [];
  let paragraph: string[] = [];
  let listItems: string[] = [];
  let listOrdered = false;
  let mathEnvironment = '';
  let mathLines: string[] = [];
  let visualDepth = 0;
  let visualEnvironment: 'axis' | 'tikzcd' | 'tikzpicture' = 'tikzpicture';
  let visualLines: string[] = [];
  let tableEnvironment = '';
  let tableLines: string[] = [];
  let codeEnvironment = '';
  let codeLines: string[] = [];
  let codeCaption = '';
  let codeLanguage = '';
  let ignoredEnvironment = '';

  function flushParagraph() {
    const text = readableText(paragraph.join(' '));
    if (text) blocks.push({ text, type: 'paragraph' });
    paragraph = [];
  }

  function flushList() {
    if (listItems.length)
      blocks.push({
        items: listItems.map(readableText),
        ordered: listOrdered,
        type: 'list',
      });
    listItems = [];
  }

  for (const rawLine of lines) {
    const line = unescapedComment(rawLine).trim();
    const environmentStart = line.match(/^\\begin\{([^}]+)\}/)?.[1];
    const environmentEnd = line.match(/^\\end\{([^}]+)\}/)?.[1];

    if (ignoredEnvironment) {
      if (environmentEnd === ignoredEnvironment) ignoredEnvironment = '';
      continue;
    }

    if (environmentStart && IGNORED_ENVIRONMENTS.has(environmentStart)) {
      flushParagraph();
      flushList();
      ignoredEnvironment = environmentStart;
      continue;
    }

    if (codeEnvironment) {
      if (environmentEnd === codeEnvironment) {
        blocks.push({
          ...(codeCaption ? { caption: readableText(codeCaption) } : {}),
          code: codeLines.join('\n').trimEnd(),
          ...(codeLanguage ? { language: codeLanguage } : {}),
          type: 'code',
        });
        codeEnvironment = '';
        codeLines = [];
        codeCaption = '';
        codeLanguage = '';
      } else codeLines.push(rawLine);
      continue;
    }

    if (tableEnvironment) {
      if (environmentEnd === tableEnvironment) {
        const rows = tableRows(tableLines);
        if (rows.length) blocks.push({ rows, type: 'table' });
        tableEnvironment = '';
        tableLines = [];
      } else tableLines.push(line);
      continue;
    }

    if (visualDepth) {
      visualLines.push(line);
      if (environmentStart && VISUAL_ENVIRONMENTS.has(environmentStart))
        visualDepth += 1;
      if (environmentEnd && VISUAL_ENVIRONMENTS.has(environmentEnd))
        visualDepth -= 1;
      if (!visualDepth) {
        const caption = readableText(
          visualLines
            .join(' ')
            .match(/\\caption(?:\[[^\]]*\])?\{([^{}]*)\}/)?.[1] ??
            'Contenido gráfico definido en el archivo LaTeX.',
        );
        blocks.push({
          caption,
          environment: visualEnvironment,
          source: visualLines.join('\n'),
          type: 'visual',
        });
        visualLines = [];
      }
      continue;
    }

    if (mathEnvironment) {
      if (
        environmentEnd === mathEnvironment ||
        (mathEnvironment === '\\]' && line === '\\]') ||
        (mathEnvironment === '$$' && line === '$$')
      ) {
        const latex = mathValue(mathLines);
        if (latex) blocks.push({ latex, type: 'math' });
        mathEnvironment = '';
        mathLines = [];
      } else mathLines.push(line);
      continue;
    }

    if (environmentStart && VISUAL_ENVIRONMENTS.has(environmentStart)) {
      flushParagraph();
      flushList();
      visualDepth = 1;
      visualEnvironment = environmentStart as typeof visualEnvironment;
      visualLines = [line];
      continue;
    }
    if (environmentStart && TABLE_ENVIRONMENTS.has(environmentStart)) {
      flushParagraph();
      flushList();
      tableEnvironment = environmentStart;
      tableLines = [];
      continue;
    }
    if (environmentStart && CODE_ENVIRONMENTS.has(environmentStart)) {
      flushParagraph();
      flushList();
      codeEnvironment = environmentStart;
      codeLines = [];
      codeCaption = line.match(/caption=\{([^}]*)\}/)?.[1] ?? '';
      codeLanguage = line.match(/language=([^,\]]+)/)?.[1]?.trim() ?? '';
      continue;
    }
    if (environmentStart && MATH_ENVIRONMENTS.has(environmentStart)) {
      flushParagraph();
      flushList();
      mathEnvironment = environmentStart;
      mathLines = [];
      continue;
    }
    if (line === '\\[' || line === '$$') {
      flushParagraph();
      flushList();
      mathEnvironment = line === '$$' ? '$$' : '\\]';
      mathLines = [];
      continue;
    }
    const heading = line.match(
      /^\\(chapter|section|subsection|subsubsection|paragraph)\*?\{/,
    );
    if (heading?.[1]) {
      const headingText = bracedValue(line, heading[1]);
      flushParagraph();
      flushList();
      if (headingText)
        blocks.push({
          level: HEADING_LEVEL[heading[1]] ?? 2,
          text: readableText(headingText),
          type: 'heading',
        });
      continue;
    }
    if (environmentStart && CALLOUT_LABEL[environmentStart]) {
      flushParagraph();
      flushList();
      const optionalTitle = line.match(/^\\begin\{[^}]+\}\[([^\]]+)\]/)?.[1];
      blocks.push({
        level: 4,
        text: optionalTitle
          ? `${CALLOUT_LABEL[environmentStart]} — ${readableText(optionalTitle)}`
          : CALLOUT_LABEL[environmentStart],
        type: 'heading',
      });
      continue;
    }
    if (
      environmentEnd &&
      (CALLOUT_LABEL[environmentEnd] ||
        ['figure', 'table', 'center'].includes(environmentEnd))
    ) {
      flushParagraph();
      flushList();
      continue;
    }
    if (/^\\begin\{(?:itemize|enumerate)\}/.test(line)) {
      flushParagraph();
      flushList();
      listOrdered = line.includes('enumerate');
      continue;
    }
    if (/^\\end\{(?:itemize|enumerate)\}/.test(line)) {
      flushParagraph();
      flushList();
      continue;
    }
    const item = line.match(/^\\item(?:\[[^\]]*\])?\s*(.*)$/)?.[1];
    if (item !== undefined) {
      flushParagraph();
      if (item) listItems.push(item);
      continue;
    }
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }
    if (
      /^\\(?:end|begin|thispagestyle|hypersetup|addcontentsline|tableofcontents|maketitle|clearpage|newpage|pagenumbering|setcounter|addtocounter|phantomsection|frontmatter|mainmatter|backmatter|appendix|bibliographystyle|bibliography)\b/.test(
        line,
      )
    )
      continue;
    paragraph.push(line);
  }
  flushParagraph();
  flushList();
  const author = bracedValue(source, 'author');
  const date = bracedValue(source, 'date');
  const title = bracedValue(source, 'title');
  return {
    ...(author ? { author } : {}),
    blocks,
    ...(date ? { date } : {}),
    ...(title ? { title } : {}),
  };
}
