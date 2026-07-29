'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import type { components } from '@/lib/api/generated/platform';
import {
  RevisionConflictError,
  useUpdateRevisionMetadata,
} from '@/lib/courses/hooks';

type Revision = components['schemas']['Revision'];

export function CourseMetadataForm({
  canManage,
  courseSlug,
  revision,
  slug,
}: Readonly<{
  canManage: boolean;
  courseSlug: string;
  revision: Revision;
  slug: string;
}>) {
  const router = useRouter();
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [values, setValues] = useState({
    description: revision.description,
    duration: revision.estimated_duration_minutes?.toString() ?? '',
    language: revision.language_code,
    subtitle: revision.subtitle,
    summary: revision.summary,
    title: revision.title,
  });
  const editable = ['draft', 'changes_requested'].includes(
    revision.authoring_status,
  );
  const update = useUpdateRevisionMetadata({
    courseSlug,
    revisionId: revision.id,
    slug,
  });

  async function save() {
    setError('');
    setMessage('');
    try {
      await update.mutateAsync({
        description: values.description,
        estimated_duration_minutes: values.duration
          ? Number(values.duration)
          : null,
        expected_version: revision.lock_version,
        language_code: values.language,
        subtitle: values.subtitle,
        summary: values.summary,
        title: values.title,
      });
      setMessage('Información básica actualizada.');
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : 'No fue posible guardar.',
      );
      if (cause instanceof RevisionConflictError) {
        setMessage(
          'Los valores del formulario permanecen intactos para que puedas reconciliarlos.',
        );
      }
    }
  }

  if (!canManage || !editable) {
    return null;
  }

  return (
    <section
      aria-labelledby="course-metadata-heading"
      className="mt-7 rounded-xl border border-slate-200 bg-white p-6"
    >
      <h2 className="text-xl font-semibold" id="course-metadata-heading">
        Información básica
      </h2>
      <form action={save} className="mt-4 grid gap-4 md:grid-cols-2">
        <label className="font-medium">
          Título
          <input
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
            maxLength={200}
            name="title"
            onChange={(event) =>
              setValues((current) => ({
                ...current,
                title: event.target.value,
              }))
            }
            required
            value={values.title}
          />
        </label>
        <label className="font-medium">
          Subtítulo
          <input
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
            maxLength={240}
            name="subtitle"
            onChange={(event) =>
              setValues((current) => ({
                ...current,
                subtitle: event.target.value,
              }))
            }
            value={values.subtitle}
          />
        </label>
        <label className="font-medium md:col-span-2">
          Resumen
          <textarea
            className="mt-2 min-h-28 w-full rounded-lg border border-slate-300 px-3 py-2"
            maxLength={1200}
            name="summary"
            onChange={(event) =>
              setValues((current) => ({
                ...current,
                summary: event.target.value,
              }))
            }
            required
            value={values.summary}
          />
        </label>
        <label className="font-medium md:col-span-2">
          Descripción en texto plano
          <textarea
            className="mt-2 min-h-32 w-full rounded-lg border border-slate-300 px-3 py-2"
            maxLength={5000}
            name="description"
            onChange={(event) =>
              setValues((current) => ({
                ...current,
                description: event.target.value,
              }))
            }
            value={values.description}
          />
        </label>
        <label className="font-medium">
          Idioma
          <input
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
            maxLength={12}
            name="language"
            onChange={(event) =>
              setValues((current) => ({
                ...current,
                language: event.target.value,
              }))
            }
            required
            value={values.language}
          />
        </label>
        <label className="font-medium">
          Duración estimada en minutos
          <input
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
            min={1}
            name="duration"
            onChange={(event) =>
              setValues((current) => ({
                ...current,
                duration: event.target.value,
              }))
            }
            type="number"
            value={values.duration}
          />
        </label>
        <button
          className="w-fit rounded-lg bg-slate-950 px-4 py-2 font-medium text-white"
          type="submit"
        >
          Guardar información básica
        </button>
      </form>
      <div aria-live="polite" className="mt-4 space-y-2">
        {message ? <p className="text-sky-900">{message}</p> : null}
        {error ? (
          <p className="rounded-lg bg-red-50 p-3 text-red-950">{error}</p>
        ) : null}
      </div>
    </section>
  );
}
