import type { LMSUnitAcademicDocumentVersion1 } from './generated/unit-document-v1';

const id = (number: number) =>
  `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`;

export function completeContentFixture(): LMSUnitAcademicDocumentVersion1 {
  return {
    type: 'doc',
    content: [
      {
        type: 'heading',
        attrs: { level: 2, nodeId: id(1) },
        content: [{ type: 'text', text: 'Funciones' }],
      },
      {
        type: 'paragraph',
        attrs: { nodeId: id(2) },
        content: [
          { type: 'text', text: 'Una función ' },
          {
            type: 'inlineMath',
            attrs: { latex: 'f(x)=x^2', nodeId: id(3) },
          },
          {
            type: 'text',
            text: ' relaciona entradas y salidas.',
            marks: [{ type: 'bold' }],
          },
        ],
      },
      {
        type: 'pedagogicalBlock',
        attrs: {
          kind: 'definition',
          nodeId: id(4),
          title: 'Definición',
        },
        content: [
          {
            type: 'paragraph',
            attrs: { nodeId: id(5) },
            content: [{ type: 'text', text: 'El dominio reúne las entradas.' }],
          },
        ],
      },
      {
        type: 'displayMath',
        attrs: {
          label: 'quadratic-function',
          latex: 'f(x)=x^2',
          nodeId: id(6),
        },
      },
      {
        type: 'codeBlock',
        attrs: {
          caption: 'Ejemplo',
          code: 'def f(x):\n    return x**2',
          language: 'python',
          nodeId: id(7),
        },
      },
      {
        type: 'table',
        attrs: { caption: 'Tabla de valores', nodeId: id(8) },
        content: [
          {
            type: 'tableRow',
            attrs: { nodeId: id(9) },
            content: [
              {
                type: 'tableHeader',
                attrs: {
                  colspan: 1,
                  colwidth: null,
                  nodeId: id(10),
                  rowspan: 1,
                },
                content: [
                  {
                    type: 'paragraph',
                    attrs: { nodeId: id(11) },
                    content: [{ type: 'text', text: 'x' }],
                  },
                ],
              },
            ],
          },
          {
            type: 'tableRow',
            attrs: { nodeId: id(12) },
            content: [
              {
                type: 'tableCell',
                attrs: {
                  colspan: 1,
                  colwidth: null,
                  nodeId: id(13),
                  rowspan: 1,
                },
                content: [
                  {
                    type: 'paragraph',
                    attrs: { nodeId: id(14) },
                    content: [{ type: 'text', text: '2' }],
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  };
}
