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
      activities: [
        {
          activity_type: 'lesson',
          availability_rules: [],
          completion_method: 'manual',
          created_at: '2026-07-29T00:00:00Z',
          estimated_duration_minutes: null,
          id: '00000000-0000-0000-0000-000000000005',
          learning_objective_ids: [],
          lesson_unit_id: '00000000-0000-0000-0000-000000000004',
          minimum_attendance_basis_points: null,
          minimum_grade_basis_points: null,
          module_id: '00000000-0000-0000-0000-000000000003',
          position: 1,
          required: true,
          status: 'active',
          summary: '',
          title: 'Relaciones',
          updated_at: '2026-07-29T00:00:00Z',
        },
      ],
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
          content_status: 'missing',
          content_updated_at: null,
          content_version: null,
          created_at: '2026-07-29T00:00:00Z',
          estimated_duration_minutes: null,
          id: '00000000-0000-0000-0000-000000000004',
          delivery_status: 'document_missing',
          lesson_kind: 'document',
          learning_objectives: [],
          mediacms_video: null,
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

const completionPolicy: components['schemas']['CourseCompletionPolicy'] = {
  confirmed_at: null,
  confirmed_by_id: null,
  lock_version: 1,
  minimum_attendance_basis_points: null,
  minimum_grade_basis_points: null,
  require_required_activities: true,
  updated_at: '2026-07-29T00:00:00Z',
};

describe('StructureEditor', () => {
  it('renders an accessible read-only hierarchy with a real content route', () => {
    render(
      <QueryProvider>
        <StructureEditor
          assessmentVersions={[]}
          canManageAssessments={false}
          canManage={false}
          completionPolicy={completionPolicy}
          courseSlug="algebra"
          gradingScheme={[]}
          liveClassBindings={[]}
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
    expect(screen.getAllByText(/Sin documento/)).not.toHaveLength(0);
    expect(screen.getByRole('link', { name: 'Ver documento' })).toHaveAttribute(
      'href',
      '/organizaciones/institucion/cursos/algebra/unidades/00000000-0000-0000-0000-000000000004/contenido',
    );
    expect(
      screen.queryByRole('button', { name: 'Añadir módulo' }),
    ).not.toBeInTheDocument();
  });

  it('presents one canonical sequence and progressive creation controls to authors', () => {
    render(
      <QueryProvider>
        <StructureEditor
          assessmentVersions={[]}
          canManageAssessments
          canManage
          completionPolicy={completionPolicy}
          courseSlug="algebra"
          gradingScheme={[]}
          liveClassBindings={[]}
          objectives={[]}
          outline={{
            ...outline,
            revision: { ...outline.revision, authoring_status: 'draft' },
          }}
          slug="institucion"
          topics={[]}
        />
      </QueryProvider>,
    );

    expect(
      screen.getByRole('heading', { name: 'Secuencia curricular unificada' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Añadir lección')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /clase en vivo/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /evaluación/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('Contenido y alineación de las lecciones'),
    ).not.toBeInTheDocument();
    expect(screen.getByText('Configurar lección')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Guardar configuración' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Esta asignatura aún no tiene currículo utilizable'),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Guardar temas' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Guardar objetivos' }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', {
        name: 'Mover «Relaciones» una posición arriba',
      }),
    ).toBeDisabled();
  });
});
