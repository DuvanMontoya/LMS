'use client';

import { useEffect, useId, useRef, useState } from 'react';

import { MathLiveField } from '@/components/content/math-live-field';

export type MathExpressionValue = {
  latex: string;
  mathjson: unknown;
};

export type MathExpressionValidationState =
  'idle' | 'validating' | 'valid' | 'invalid';

const BASE_OPERATORS = new Set([
  'Rational',
  'Add',
  'Subtract',
  'Negate',
  'Multiply',
  'Divide',
  'Power',
  'Sqrt',
  'Root',
  'Abs',
]);

export function MathExpressionField({
  allowedFunctions,
  allowedSymbols,
  label,
  onChange,
  onValidationStateChange,
  value,
}: Readonly<{
  allowedFunctions: readonly string[];
  allowedSymbols: readonly string[];
  label: string;
  onChange: (value: MathExpressionValue | null) => void;
  onValidationStateChange?: (state: MathExpressionValidationState) => void;
  value: MathExpressionValue | null;
}>) {
  const labelId = useId();
  const [latex, setLatex] = useState(value?.latex ?? '');
  const [error, setError] = useState('');
  const [validationState, setValidationState] =
    useState<MathExpressionValidationState>(value ? 'valid' : 'idle');
  const onChangeRef = useRef(onChange);
  const onValidationStateChangeRef = useRef(onValidationStateChange);
  const symbolsKey = allowedSymbols.join(',');
  const functionsKey = allowedFunctions.join(',');

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    onValidationStateChangeRef.current = onValidationStateChange;
  }, [onValidationStateChange]);

  function updateValidationState(state: MathExpressionValidationState) {
    setValidationState(state);
    onValidationStateChangeRef.current?.(state);
  }

  useEffect(() => {
    let active = true;
    if (!latex.trim()) {
      return;
    }
    const timer = window.setTimeout(() => {
      void import('@cortex-js/compute-engine')
        .then(({ ComputeEngine }) => {
          if (!active) return;
          const engine = new ComputeEngine();
          const expression = engine.parse(latex, {
            canonical: false,
            structural: true,
          });
          if (!expression?.isValid) {
            throw new Error('invalid_expression');
          }
          const mathjson = normalizeMathJsonNumbers(expression.json);
          validateClientMathJson(
            mathjson,
            new Set(symbolsKey.split(',').filter(Boolean)),
            new Set(functionsKey.split(',').filter(Boolean)),
          );
          setError('');
          updateValidationState('valid');
          onChangeRef.current({
            latex: expression.toLatex(),
            mathjson,
          });
        })
        .catch(() => {
          if (!active) return;
          setError(
            'La expresión usa una estructura, símbolo o función no permitida.',
          );
          updateValidationState('invalid');
          onChangeRef.current(null);
        });
    }, 120);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [functionsKey, latex, symbolsKey]);

  return (
    <div aria-labelledby={labelId} role="group">
      <span className="mb-2 block text-sm font-medium" id={labelId}>
        {label}
      </span>
      <MathLiveField
        onChange={(nextLatex) => {
          setLatex(nextLatex);
          if (!nextLatex.trim()) {
            setError('');
            updateValidationState('idle');
            onChangeRef.current(null);
            return;
          }
          setError('');
          updateValidationState('validating');
          onChangeRef.current(null);
        }}
        value={latex}
      />
      <p className="mt-2 text-xs text-muted-foreground">
        Símbolos: {allowedSymbols.join(', ') || 'ninguno'} · Funciones:{' '}
        {allowedFunctions.join(', ') || 'ninguna'} · máximo 200 nodos y
        profundidad 24.
      </p>
      {validationState === 'validating' ? (
        <p aria-live="polite" className="mt-1 text-sm text-muted-foreground">
          Validando expresión…
        </p>
      ) : null}
      {validationState === 'valid' ? (
        <p
          aria-live="polite"
          className="mt-1 text-sm text-emerald-700 dark:text-emerald-400"
        >
          Expresión lista para guardar.
        </p>
      ) : null}
      {error ? (
        <p className="mt-1 text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function normalizeMathJsonNumbers(value: unknown): unknown {
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('math_number');
    if (Number.isInteger(value)) return value;
    const decimal = value.toString();
    if (!/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(decimal)) {
      throw new Error('math_decimal');
    }
    return decimal;
  }
  return Array.isArray(value) ? value.map(normalizeMathJsonNumbers) : value;
}

export function validateClientMathJson(
  value: unknown,
  allowedSymbols: ReadonlySet<string>,
  allowedFunctions: ReadonlySet<string>,
) {
  const pending: Array<{ depth: number; value: unknown }> = [
    { depth: 1, value },
  ];
  let nodes = 0;
  while (pending.length) {
    const current = pending.pop();
    if (!current) break;
    nodes += 1;
    if (nodes > 200 || current.depth > 24) throw new Error('math_limits');
    if (
      typeof current.value === 'number' &&
      Number.isInteger(current.value) &&
      Number.isFinite(current.value)
    ) {
      continue;
    }
    if (typeof current.value === 'string') {
      if (
        /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(current.value) ||
        current.value === 'Pi' ||
        current.value === 'ExponentialE' ||
        allowedSymbols.has(current.value)
      ) {
        continue;
      }
      throw new Error('math_symbol');
    }
    if (!Array.isArray(current.value) || current.value.length < 2) {
      throw new Error('math_shape');
    }
    const [operator, ...args] = current.value;
    if (
      typeof operator !== 'string' ||
      (!BASE_OPERATORS.has(operator) && !allowedFunctions.has(operator))
    ) {
      throw new Error('math_operator');
    }
    if (operator === 'Power') {
      const exponent = args[1];
      if (
        typeof exponent !== 'number' ||
        !Number.isInteger(exponent) ||
        Math.abs(exponent) > 20
      ) {
        throw new Error('math_exponent');
      }
    }
    for (const argument of args) {
      pending.push({ depth: current.depth + 1, value: argument });
    }
  }
}
