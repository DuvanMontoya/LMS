import 'server-only';

import { notFound } from 'next/navigation';

import type { components } from '@/lib/api/generated/platform';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getCourseWorkspace } from '@/lib/courses/server';

type ContentCurrent = components['schemas']['ContentCurrent'];
type ContentVersion = components['schemas']['ContentVersionSummary'];

async function required<T>(
  request: Promise<{ response: Response; data?: T }>,
  message: string,
): Promise<T> {
  const { data, response } = await request;
  if (response.status === 403 || response.status === 404) notFound();
  if (!response.ok || data === undefined) throw new Error(message);
  return data;
}

export async function getUnitContentWorkspace(
  organizationSlug: string,
  courseSlug: string,
  unitId: string,
) {
  const workspace = await getCourseWorkspace(organizationSlug, courseSlug);
  let courseModule: (typeof workspace.outline.modules)[number] | undefined;
  let unit:
    (typeof workspace.outline.modules)[number]['units'][number] | undefined;
  for (const candidate of workspace.outline.modules) {
    const found = candidate.units.find((item) => item.id === unitId);
    if (found) {
      courseModule = candidate;
      unit = found;
      break;
    }
  }
  if (!courseModule || !unit || unit.status !== 'active') notFound();

  const client = await createPlatformServerClient();
  const path = {
    course_slug: courseSlug,
    organization_slug: organizationSlug,
    revision_id: workspace.revision.id,
    unit_id: unitId,
  };
  const [current, versions] = await Promise.all([
    required(
      client.GET(
        '/api/v1/organizations/{organization_slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/content/',
        { params: { path } },
      ),
      'No fue posible consultar el contenido de la unidad.',
    ) as Promise<ContentCurrent>,
    required(
      client.GET(
        '/api/v1/organizations/{organization_slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/content/versions/',
        { params: { path } },
      ),
      'No fue posible consultar el historial de contenido.',
    ) as Promise<ContentVersion[]>,
  ]);
  return { ...workspace, courseModule, current, unit, versions };
}
