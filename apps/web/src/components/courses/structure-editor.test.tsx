import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { components } from '@/lib/api/generated/platform';
import { QueryProvider } from '@/lib/query/provider';

import { StructureEditor } from './structure-editor';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

const outline: components['schemas']['Outline'] = {
  course: {
    archived_at: null,
    created_at: '2026-07-29T00:00:00Z',
    id: '00000000-0000-0000-0000-000000000001',
    slug: 'algebra',
    status: 'active',
  },
  learning_objectives: [],
  modules: [
    {
      archived_at: null,
      created_at: '2026-07-29T00:00:00Z',
      description: '',
      id: '00000000-0000-0000-0000-000000000003',
      position: 1,
      revision_id: '00000000-0000-0000-0000-000000000002',
      status: 'active',
      title: 'Fundamentos',
      units: [
        {
          archived_at: null,
          content_status: 'Contenido académico pendiente',
          content_updated_at: null,
          content_version: null,
          created_at: '2026-07-29T00:00:00Z',
          estimated_duration_minutes: null,
          id: '00000000-0000-0000-0000-000000000004',
          learning_objectives: [],
          module_id: '00000000-0000-0000-0000-000000000003',
          position: 1,
          status: 'active',
          summary: '',
          title: 'Relaciones',
          topics: [],
          updated_at: '2026-07-29T00:00:00Z',
        },
      ],
      updated_at: '2026-07-29T00:00:00Z',
    },
  ],
  revision: {
    authoring_status: 'approved',
    based_on_revision_id: null,
    course_slug: 'algebra',
    created_at: '2026-07-29T00:00:00Z',
    description: '',
    estimated_duration_minutes: null,
    id: '00000000-0000-0000-0000-000000000002',
    language_code: 'es',
    lock_version: 5,
    number: 1,
    status_changed_at: '2026-07-29T00:00:00Z',
    subtitle: '',
    summary: 'Resumen',
    title: 'Álgebra',
    updated_at: '2026-07-29T00:00:00Z',
  },
  subjects: [],
};

describe('StructureEditor', () => {
  it('renders an accessible read-only hierarchy with a real content route', () => {
    render(
      <QueryProvider>
        <StructureEditor
          canManage={false}
          courseSlug="algebra"
          objectives={[]}
          outline={outline}
          slug="institucion"
          topics={[]}
        />
      </QueryProvider>,
    );
    expect(
      screen.getByRole('heading', { name: 'Estructura del curso' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Contenido académico pendiente/),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ver contenido' })).toHaveAttribute(
      'href',
      '/organizaciones/institucion/cursos/algebra/unidades/00000000-0000-0000-0000-000000000004/contenido',
    );
    expect(
      screen.queryByRole('button', { name: 'Añadir módulo' }),
    ).not.toBeInTheDocument();
  });
});
