'use client';

import { useEffect, useRef, useState } from 'react';

type MathJaxApi = {
  startup: { promise: Promise<unknown> };
  typesetClear: (elements: HTMLElement[]) => void;
  typesetPromise: (elements: HTMLElement[]) => Promise<unknown>;
};

type PendingTypeset = {
  host: HTMLElement;
  reject: (reason: unknown) => void;
  resolve: () => void;
  source: string;
};

declare global {
  interface Window {
    MathJax?: MathJaxApi | Record<string, unknown>;
    __lmsMathJaxPromise?: Promise<MathJaxApi>;
    __lmsMathJaxPending?: PendingTypeset[];
    __lmsMathJaxScheduled?: boolean;
    __lmsMathJaxTypesetQueue?: Promise<void>;
  }
}

function loadMathJax(): Promise<MathJaxApi> {
  if (window.__lmsMathJaxPromise) return window.__lmsMathJaxPromise;
  window.__lmsMathJaxPromise = new Promise<MathJaxApi>((resolve, reject) => {
    window.MathJax = {
      loader: {
        load: ['ui/safe'],
        paths: { mathjax: '/vendor/mathjax' },
      },
      options: {
        enableMenu: false,
        safeOptions: {
          allow: {
            URLs: 'none',
            classes: 'none',
            cssIDs: 'none',
            styles: 'none',
          },
          safeProtocols: {
            data: false,
            file: false,
            http: false,
            https: false,
            javascript: false,
          },
        },
      },
      startup: { typeset: false },
      svg: { fontCache: 'local' },
      tex: {
        packages: ['base', 'ams'],
        processEscapes: false,
        processRefs: true,
      },
    };
    const script = document.createElement('script');
    script.async = true;
    script.dataset.lmsMathjax = 'true';
    script.onerror = () =>
      reject(new Error('No fue posible cargar el renderer matemático local.'));
    script.onload = async () => {
      const api = window.MathJax as MathJaxApi;
      await api.startup.promise;
      resolve(api);
    };
    script.src = '/vendor/mathjax/tex-svg.js';
    document.head.append(script);
  });
  return window.__lmsMathJaxPromise;
}

function queueTypeset(
  host: HTMLElement,
  mathJax: MathJaxApi,
  source: string,
): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    const pending = (window.__lmsMathJaxPending ??= []);
    pending.push({ host, reject, resolve, source });
    if (window.__lmsMathJaxScheduled) return;
    window.__lmsMathJaxScheduled = true;
    window.setTimeout(() => {
      window.__lmsMathJaxScheduled = false;
      const batch = window.__lmsMathJaxPending?.splice(0) ?? [];
      const task = (window.__lmsMathJaxTypesetQueue ?? Promise.resolve())
        .catch(() => undefined)
        .then(async () => {
          const connected = batch.filter(({ host: item }) => item.isConnected);
          if (!connected.length) {
            batch.forEach(({ resolve: finish }) => finish());
            return;
          }
          const hosts = connected.map(({ host: item }) => item);
          connected.forEach(({ host: item, source: text }) => {
            item.textContent = text;
          });
          try {
            mathJax.typesetClear(hosts);
            await mathJax.typesetPromise(hosts);
            batch.forEach(({ resolve: finish }) => finish());
          } catch (cause) {
            batch.forEach(({ reject: fail }) => fail(cause));
          }
        });
      window.__lmsMathJaxTypesetQueue = task;
    });
  });
}

export function MathJaxFormula({
  display = false,
  latex,
}: Readonly<{ display?: boolean; latex: string }>) {
  const ref = useRef<HTMLSpanElement>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const host = ref.current;
    if (!host) return;
    let active = true;
    const hideVisualSvgFromAssistiveTechnology = () => {
      host.querySelectorAll('mjx-container').forEach((container) => {
        container.setAttribute('aria-hidden', 'true');
        container.setAttribute('tabindex', '-1');
      });
      host.querySelectorAll('svg').forEach((svg) => {
        svg.setAttribute('aria-hidden', 'true');
        svg.setAttribute('focusable', 'false');
      });
    };
    const observer = new MutationObserver(hideVisualSvgFromAssistiveTechnology);
    observer.observe(host, { childList: true, subtree: true });
    host.textContent = display ? `\\[${latex}\\]` : `\\(${latex}\\)`;
    void loadMathJax()
      .then(async (mathJax) => {
        if (!active) return;
        await queueTypeset(
          host,
          mathJax,
          display ? `\\[${latex}\\]` : `\\(${latex}\\)`,
        );
        if (active) {
          hideVisualSvgFromAssistiveTechnology();
          setError('');
        }
      })
      .catch((cause: unknown) => {
        if (active)
          setError(
            cause instanceof Error
              ? cause.message
              : 'La fórmula no pudo renderizarse.',
          );
      });
    return () => {
      active = false;
      observer.disconnect();
    };
  }, [display, latex]);

  return (
    <span
      aria-label={`Fórmula ${display ? 'en bloque' : 'en línea'}: ${latex}`}
      className={display ? 'block overflow-x-auto py-3 text-center' : ''}
      data-mathjax-safe="true"
      role="math"
    >
      <span aria-hidden="true" data-mathjax-visual="true" ref={ref} />
      {error ? <span className="text-red-700">{error}</span> : null}
    </span>
  );
}
