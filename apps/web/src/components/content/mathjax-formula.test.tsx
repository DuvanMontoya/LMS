import { act, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MathJaxFormula } from './mathjax-formula';

describe('MathJaxFormula', () => {
  beforeEach(() => {
    delete window.MathJax;
    delete window.__lmsMathJaxPromise;
    delete window.__lmsMathJaxPending;
    delete window.__lmsMathJaxScheduled;
    delete window.__lmsMathJaxTypesetQueue;
    document.head
      .querySelectorAll('script[data-lms-mathjax]')
      .forEach((node) => node.remove());
  });

  it('loads one local safe renderer and typesets text, not HTML', async () => {
    let activeTypesets = 0;
    let maximumConcurrentTypesets = 0;
    const typesetPromise = vi.fn(async (hosts: HTMLElement[]) => {
      activeTypesets += 1;
      maximumConcurrentTypesets = Math.max(
        maximumConcurrentTypesets,
        activeTypesets,
      );
      await Promise.resolve();
      hosts.forEach((host) => {
        const container = document.createElement('mjx-container');
        container.setAttribute('tabindex', '0');
        container.append(document.createElement('svg'));
        host.replaceChildren(container);
      });
      activeTypesets -= 1;
    });
    render(
      <>
        <MathJaxFormula latex="x^2" />
        <MathJaxFormula display latex="y^2" />
      </>,
    );
    const script = document.head.querySelector<HTMLScriptElement>(
      'script[data-lms-mathjax]',
    );
    expect(script?.src).toBe('http://localhost:3000/vendor/mathjax/tex-svg.js');
    expect(
      document.head.querySelectorAll('script[data-lms-mathjax]'),
    ).toHaveLength(1);
    const configuration = JSON.stringify(window.MathJax);
    expect(configuration).toContain('"load":["ui/safe"]');
    expect(configuration).toContain('"packages":["base","ams"]');
    expect(configuration).toContain(
      '"fontPath":"/vendor/mathjax/fonts/%%FONT%%"',
    );
    expect(configuration).toContain('"linebreaks":{"inline":false}');
    expect(configuration).toContain('"javascript":false');
    expect(configuration).not.toContain('texhtml');
    expect(configuration).not.toContain('jsdelivr');
    window.MathJax = {
      startup: { promise: Promise.resolve() },
      typesetClear: vi.fn(),
      typesetPromise,
    };
    await act(async () => script?.dispatchEvent(new Event('load')));
    await waitFor(() => expect(typesetPromise).toHaveBeenCalledTimes(1));
    expect(typesetPromise.mock.calls[0]?.[0]).toHaveLength(2);
    expect(maximumConcurrentTypesets).toBe(1);
    expect(screen.getAllByRole('math')).toHaveLength(2);
    expect(
      [...document.querySelectorAll('svg')].every(
        (svg) => svg.getAttribute('aria-hidden') === 'true',
      ),
    ).toBe(true);
    expect(
      [...document.querySelectorAll('mjx-container')].every(
        (container) => container.getAttribute('tabindex') === '-1',
      ),
    ).toBe(true);
    expect(document.querySelector('[href^="javascript:"]')).toBeNull();
  });
});
