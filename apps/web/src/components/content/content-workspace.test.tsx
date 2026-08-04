import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';

import { completeContentFixture } from '@/lib/content/test-fixtures';

import { ContentWorkspace } from './content-workspace';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

const current = {
  character_count: 100,
  content: completeContentFixture(),
  digest: 'a'.repeat(64),
  document_id: '00000000-0000-4000-8000-000000000100',
  document_version: 2,
  editable: false,
  is_meaningful: true,
  no_op: false,
  node_count: 14,
  schema_version: 1,
  updated_at: '2026-07-29T12:00:00Z',
  word_count: 20,
};

function renderWorkspace(element: React.ReactElement) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      {element}
    </QueryClientProvider>,
  );
}

describe('ContentWorkspace read-only mode', () => {
  it('renders the real document and history without editing or restore controls', () => {
    renderWorkspace(
      <ContentWorkspace
        courseSlug="calculo"
        current={current}
        organizationSlug="demo"
        revisionId="00000000-0000-4000-8000-000000000101"
        revisionStatus="approved"
        unitId="00000000-0000-4000-8000-000000000102"
        versions={[]}
      />,
    );
    expect(screen.getByText(/contenido en solo lectura/i)).toBeInTheDocument();
    expect(screen.queryByRole('toolbar')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Guardar contenido' }),
    ).not.toBeInTheDocument();
    expect(screen.getByText('Historial de versiones (0)')).toBeInTheDocument();
  });
});

describe('ContentWorkspace editable mode', () => {
  it('does not report internal stable-ID transactions as unsaved user changes', async () => {
    renderWorkspace(
      <ContentWorkspace
        courseSlug="calculo"
        current={{ ...current, editable: true }}
        organizationSlug="demo"
        revisionId="00000000-0000-4000-8000-000000000101"
        revisionStatus="draft"
        unitId="00000000-0000-4000-8000-000000000102"
        versions={[]}
      />,
    );

    await waitFor(() =>
      expect(screen.getByText('Sin cambios')).toBeInTheDocument(),
    );
    expect(
      screen.queryByText(/cambios locales que todavía no están guardados/i),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Guardar contenido' }),
    ).toBeDisabled();
    expect(
      screen.queryByRole('button', { name: 'Fórmula' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Ecuación' }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/Escribe LaTeX directamente en el contenido/i),
    ).toBeInTheDocument();
  });
});
