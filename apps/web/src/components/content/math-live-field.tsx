'use client';

import { useEffect, useRef, useState } from 'react';

type MathFieldElementLike = HTMLElement & {
  mathVirtualKeyboardPolicy: string;
  value: string;
};

export function MathLiveField({
  onChange,
  value,
}: Readonly<{ onChange: (value: string) => void; value: string }>) {
  const host = useRef<HTMLDivElement>(null);
  const fieldRef = useRef<MathFieldElementLike | null>(null);
  const onChangeRef = useRef(onChange);
  const valueRef = useRef(value);
  const [error, setError] = useState('');

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  useEffect(() => {
    let active = true;
    let field: MathFieldElementLike | undefined;
    void import('mathlive')
      .then(({ MathfieldElement }) => {
        if (!active || !host.current) return;
        MathfieldElement.fontsDirectory = '/vendor/mathlive/fonts';
        field = document.createElement('math-field') as MathFieldElementLike;
        field.setAttribute('aria-label', 'Expresión matemática en LaTeX');
        field.setAttribute('virtual-keyboard-mode', 'manual');
        field.mathVirtualKeyboardPolicy = 'manual';
        field.value = valueRef.current;
        field.addEventListener('input', () => {
          if (field) onChangeRef.current(field.value);
        });
        fieldRef.current = field;
        host.current.replaceChildren(field);
      })
      .catch(() => {
        if (active) setError('No fue posible cargar el teclado matemático.');
      });
    return () => {
      active = false;
      fieldRef.current = null;
      field?.remove();
    };
  }, []);

  useEffect(() => {
    const field = fieldRef.current;
    if (field && field.value !== value) field.value = value;
  }, [value]);

  return (
    <div>
      <div
        className="min-h-12 rounded-lg border border-slate-300 bg-white p-2"
        ref={host}
      />
      {error ? (
        <p className="mt-1 text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
