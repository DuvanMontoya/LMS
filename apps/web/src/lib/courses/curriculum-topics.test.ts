import { describe, expect, it } from 'vitest';

import type { components } from '@/lib/api/generated/platform';

import { flattenCourseTopics } from './curriculum-topics';

type Topic = components['schemas']['Topic'];

function topic(id: string, title: string, children: Topic[] = []): Topic {
  return {
    children: children as Topic['children'],
    depth: 1,
    description: '',
    id,
    slug: title.toLocaleLowerCase('es-CO').replaceAll(' ', '-'),
    status: 'active',
    title,
  };
}

describe('flattenCourseTopics', () => {
  it('keeps every nested topic with its breadcrumb and subject origin', () => {
    const result = flattenCourseTopics(
      [topic('root', 'Antiderivada', [topic('child', 'Sumas de Riemann')])],
      { id: 'subject-1', name: 'Cálculo integral' },
    );

    expect(result.map((item) => item.title)).toEqual([
      'Antiderivada',
      'Sumas de Riemann',
    ]);
    expect(result[1]).toMatchObject({
      ancestor_titles: ['Antiderivada'],
      subject_id: 'subject-1',
      subject_name: 'Cálculo integral',
    });
  });
});
