import type {
  Course,
  LearningObjective,
  Subject,
  Unit,
} from '@/lib/publishing/generated/course-release-v1';

export type PublishedUnitView = Unit & {
  module: { id: string; position: number; title: string };
};

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

export function requirePublishedCourse(value: unknown): Course {
  if (
    !record(value) ||
    typeof value.id !== 'string' ||
    typeof value.slug !== 'string' ||
    typeof value.title !== 'string' ||
    typeof value.summary !== 'string'
  ) {
    throw new Error('El contrato del curso publicado es inválido.');
  }
  return value as unknown as Course;
}

export function requirePublishedUnit(value: unknown): PublishedUnitView {
  if (
    !record(value) ||
    typeof value.id !== 'string' ||
    typeof value.title !== 'string' ||
    !Array.isArray(value.topics) ||
    !Array.isArray(value.learning_objectives) ||
    !record(value.content) ||
    !record(value.content.document) ||
    value.content.document.type !== 'doc' ||
    !record(value.module) ||
    typeof value.module.id !== 'string' ||
    typeof value.module.title !== 'string' ||
    typeof value.module.position !== 'number'
  ) {
    throw new Error('El contrato de la unidad publicada es inválido.');
  }
  return value as unknown as PublishedUnitView;
}

export function requirePublishedSubjects(value: unknown): readonly Subject[] {
  if (
    !Array.isArray(value) ||
    value.some(
      (item) =>
        !record(item) ||
        typeof item.id !== 'string' ||
        typeof item.name !== 'string' ||
        typeof item.alignment_type !== 'string',
    )
  ) {
    throw new Error('El contrato de asignaturas publicadas es inválido.');
  }
  return value as Subject[];
}

export function requirePublishedObjectives(
  value: unknown,
): readonly LearningObjective[] {
  if (
    !Array.isArray(value) ||
    value.some(
      (item) =>
        !record(item) ||
        typeof item.id !== 'string' ||
        typeof item.code !== 'string' ||
        typeof item.statement !== 'string',
    )
  ) {
    throw new Error('El contrato de objetivos publicados es inválido.');
  }
  return value as LearningObjective[];
}
