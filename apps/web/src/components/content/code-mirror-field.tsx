'use client';

import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { javascript } from '@codemirror/lang-javascript';
import { json } from '@codemirror/lang-json';
import { python } from '@codemirror/lang-python';
import { sql } from '@codemirror/lang-sql';
import {
  defaultHighlightStyle,
  syntaxHighlighting,
} from '@codemirror/language';
import { EditorState, type Extension } from '@codemirror/state';
import {
  drawSelection,
  EditorView,
  highlightActiveLine,
  highlightActiveLineGutter,
  keymap,
  lineNumbers,
} from '@codemirror/view';
import { useEffect, useRef } from 'react';

function languageExtension(language: string): Extension {
  if (language === 'python') return python();
  if (language === 'json') return json();
  if (language === 'sql') return sql();
  if (language === 'javascript') return javascript();
  if (language === 'typescript') return javascript({ typescript: true });
  return [];
}

export function CodeMirrorField({
  ariaLabel,
  code,
  language,
  maxLength = 50_000,
  onChange,
}: Readonly<{
  ariaLabel: string;
  code: string;
  language: string;
  maxLength?: number;
  onChange: (value: string) => void;
}>) {
  const host = useRef<HTMLDivElement>(null);
  const onChangeRef = useRef(onChange);
  const initialCodeRef = useRef(code);
  const viewRef = useRef<EditorView | null>(null);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    if (!host.current) return;
    const state = EditorState.create({
      doc: initialCodeRef.current,
      extensions: [
        lineNumbers(),
        highlightActiveLineGutter(),
        history(),
        drawSelection(),
        highlightActiveLine(),
        syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
        languageExtension(language),
        keymap.of([...defaultKeymap, ...historyKeymap]),
        EditorView.contentAttributes.of({
          'aria-label': ariaLabel,
          'aria-multiline': 'true',
          role: 'textbox',
        }),
        EditorState.transactionFilter.of((transaction) =>
          transaction.newDoc.length <= maxLength ? transaction : [],
        ),
        EditorView.updateListener.of((update) => {
          if (update.docChanged)
            onChangeRef.current(update.state.doc.toString());
        }),
        EditorView.theme({
          '&': { fontSize: '14px', minHeight: '10rem' },
          '.cm-content': { fontFamily: 'ui-monospace, monospace' },
          '.cm-scroller': { overflow: 'auto' },
        }),
      ],
    });
    const view = new EditorView({ parent: host.current, state });
    viewRef.current = view;
    return () => {
      if (viewRef.current === view) viewRef.current = null;
      view.destroy();
    };
  }, [ariaLabel, language, maxLength]);

  useEffect(() => {
    const view = viewRef.current;
    if (!view || view.state.doc.toString() === code) return;
    view.dispatch({
      changes: {
        from: 0,
        to: view.state.doc.length,
        insert: code,
      },
    });
  }, [code]);

  return (
    <div>
      <div
        className="overflow-hidden rounded-lg border border-slate-300"
        ref={host}
      />
      <p className="mt-1 text-xs text-slate-600">
        Tab sale del editor de código. El código nunca se ejecuta.
      </p>
    </div>
  );
}
