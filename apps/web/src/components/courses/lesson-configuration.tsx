'use client';

import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Archive,
  BookOpenCheck,
  ExternalLink,
  FileAudio,
  FileText,
  GraduationCap,
  Link2,
  LoaderCircle,
  Save,
  Search,
  Target,
  Video,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { AssetPickerDialog } from '@/components/assets/asset-picker-dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import { apiErrorMessage } from '@/lib/api/api-error';
import type { components } from '@/lib/api/generated/platform';
import {
  type CourseTopicOption,
  flattenCourseTopics,
} from '@/lib/courses/curriculum-topics';
import { cn } from '@/lib/utils';

type Outline = components['schemas']['Outline'];
type Lesson = Outline['modules'][number]['units'][number];
type Objective = components['schemas']['Objective'];
type RevisionSubject = Outline['subjects'][number];
type TopicTree = components['schemas']['Topic'][];

export type LessonConfigurationInput = {
  estimatedDurationMinutes: number | null;
  learningObjectiveIds: string[];
  mediaCmsFriendlyToken?: string;
  summary: string;
  title: string;
  topicIds: string[];
};

type LessonResource = {
  asset_kind: 'audio' | 'document';
  asset_version_id: string;
  detected_mime_type: string;
  extension: string;
  original_filename: string;
  size_bytes: number | null;
  updated_at: string;
};

type LessonResourceResponse = {
  lock_version: number;
  resource: LessonResource | null;
};

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function resourceLessonKind(kind: Lesson['lesson_kind']) {
  return ['latex_source', 'markdown_source', 'pdf', 'slides', 'audio'].includes(
    kind,
  );
}

function searchable(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es-CO');
}

function mediaCmsOrigin(value: string | undefined) {
  if (!value) return null;
  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

export function LessonConfiguration({
  alignedSubjects,
  courseSlug,
  isSaving,
  lesson,
  mediaCmsAuthoringUrl,
  objectives,
  onArchive,
  onDeliverySaved,
  onSave,
  organizationSlug,
  revisionId,
  revisionVersion,
  topics,
}: Readonly<{
  alignedSubjects: readonly RevisionSubject[];
  courseSlug: string;
  isSaving: boolean;
  lesson: Lesson;
  mediaCmsAuthoringUrl?: string;
  objectives: Objective[];
  onArchive: () => void;
  onDeliverySaved: (lockVersion: number, message: string) => void;
  onSave: (input: LessonConfigurationInput) => Promise<void>;
  organizationSlug: string;
  revisionId: string;
  revisionVersion: number;
  topics: CourseTopicOption[];
}>) {
  const [title, setTitle] = useState(lesson.title);
  const [summary, setSummary] = useState(lesson.summary);
  const [duration, setDuration] = useState(
    lesson.estimated_duration_minutes?.toString() ?? '',
  );
  const [mediaCmsFriendlyToken, setMediaCmsFriendlyToken] = useState(() => {
    const media = record(lesson.mediacms_video) ? lesson.mediacms_video : null;
    const token = media?.media_friendly_token;
    return typeof token === 'string' ? token : '';
  });
  const [mediaPickerError, setMediaPickerError] = useState('');
  const mediaPickerWindow = useRef<Window | null>(null);
  const mediaPickerNonce = useRef<string | null>(null);
  const mediaPickerPoll = useRef<number | null>(null);
  const [selectedTopicIds, setSelectedTopicIds] = useState(
    lesson.topics.map((item) => item.topic.id),
  );
  const [selectedObjectiveIds, setSelectedObjectiveIds] = useState(
    lesson.learning_objectives.map((item) => item.learning_objective.id),
  );
  const [query, setQuery] = useState('');
  const queryClient = useQueryClient();
  const subjectById = useMemo(
    () =>
      new Map(alignedSubjects.map((item) => [item.subject.id, item] as const)),
    [alignedSubjects],
  );
  const primarySubject =
    alignedSubjects.find((item) => item.alignment_type === 'primary') ??
    alignedSubjects[0];
  const mediaCmsPickerOrigin = useMemo(
    () => mediaCmsOrigin(mediaCmsAuthoringUrl),
    [mediaCmsAuthoringUrl],
  );
  const [activeSubjectId, setActiveSubjectId] = useState(
    primarySubject?.subject.id ?? '',
  );
  const activeSubject = alignedSubjects.find(
    (item) => item.subject.id === activeSubjectId,
  );
  const {
    data: additionalTopics = [],
    isError: didTopicsFail,
    isLoading: isLoadingTopics,
  } = useQuery({
    enabled:
      Boolean(activeSubject) &&
      activeSubject?.subject.id !== primarySubject?.subject.id,
    queryKey: [
      'course-curriculum-topics',
      organizationSlug,
      activeSubject?.subject.id,
    ],
    queryFn: async () => {
      if (!activeSubject) return [];
      const { data, response } = await platformBrowserClient.GET(
        '/api/v1/organizations/{slug}/catalog/subjects/{subject_id}/topics/',
        {
          params: {
            path: {
              slug: organizationSlug,
              subject_id: activeSubject.subject.id,
            },
          },
        },
      );
      if (!response.ok || !data) {
        throw new Error('No fue posible consultar los temas de la asignatura.');
      }
      return flattenCourseTopics(data as TopicTree, activeSubject.subject);
    },
    staleTime: 60_000,
  });
  const deliveryResource = useQuery({
    enabled: resourceLessonKind(lesson.lesson_kind),
    queryFn: async () => {
      const { data, error, response } = await platformBrowserClient.GET(
        '/api/v1/organizations/{organization_slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/content/delivery-resource/',
        {
          params: {
            path: {
              course_slug: courseSlug,
              organization_slug: organizationSlug,
              revision_id: revisionId,
              unit_id: lesson.id,
            },
          },
        },
      );
      if (!response.ok || !data) {
        throw new Error(
          apiErrorMessage(
            error,
            'No fue posible consultar el archivo de la lección.',
          ),
        );
      }
      return data as unknown as LessonResourceResponse;
    },
    queryKey: [
      'lesson-delivery-resource',
      organizationSlug,
      revisionId,
      lesson.id,
    ],
    staleTime: 15_000,
  });
  const bindDeliveryResource = useMutation({
    mutationFn: async (assetVersionId: string) => {
      const { data, error, response } = await platformBrowserClient.PUT(
        '/api/v1/organizations/{organization_slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/content/delivery-resource/',
        {
          body: {
            asset_version_id: assetVersionId,
            expected_version: revisionVersion,
          },
          params: {
            path: {
              course_slug: courseSlug,
              organization_slug: organizationSlug,
              revision_id: revisionId,
              unit_id: lesson.id,
            },
          },
        },
      );
      if (!response.ok || !data) {
        throw new Error(
          apiErrorMessage(
            error,
            'No fue posible vincular el archivo de la lección.',
          ),
        );
      }
      return data as unknown as LessonResourceResponse;
    },
    onSuccess: async (data) => {
      await queryClient.invalidateQueries({
        queryKey: [
          'lesson-delivery-resource',
          organizationSlug,
          revisionId,
          lesson.id,
        ],
      });
      onDeliverySaved(data.lock_version, 'Archivo de entrega actualizado.');
    },
  });
  const removeDeliveryResource = useMutation({
    mutationFn: async () => {
      const { data, error, response } = await platformBrowserClient.DELETE(
        '/api/v1/organizations/{organization_slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/content/delivery-resource/',
        {
          params: {
            path: {
              course_slug: courseSlug,
              organization_slug: organizationSlug,
              revision_id: revisionId,
              unit_id: lesson.id,
            },
            query: { expected_version: revisionVersion },
          },
        },
      );
      if (!response.ok || !data) {
        throw new Error(
          apiErrorMessage(
            error,
            'No fue posible desvincular el archivo de la lección.',
          ),
        );
      }
      return data as unknown as LessonResourceResponse;
    },
    onSuccess: async (data) => {
      await queryClient.invalidateQueries({
        queryKey: [
          'lesson-delivery-resource',
          organizationSlug,
          revisionId,
          lesson.id,
        ],
      });
      onDeliverySaved(data.lock_version, 'Archivo de entrega desvinculado.');
    },
  });
  const activeTopics =
    activeSubject?.subject.id === primarySubject?.subject.id
      ? topics
      : additionalTopics;
  const normalizedQuery = searchable(query.trim());
  const visibleTopics = activeTopics.filter((topic) => {
    const subject = topic.subject_name;
    return searchable(
      `${topic.ancestor_titles.join(' ')} ${topic.title} ${subject}`,
    ).includes(normalizedQuery);
  });
  const activeObjectives = objectives.filter(
    (objective) => objective.subject_id === activeSubjectId,
  );
  const visibleObjectives = activeObjectives.filter((objective) => {
    const subject = subjectById.get(objective.subject_id)?.subject.name ?? '';
    return searchable(
      `${objective.code} ${objective.statement} ${subject}`,
    ).includes(normalizedQuery);
  });
  const hasCurriculumOptions =
    activeTopics.length > 0 || activeObjectives.length > 0;
  const alignmentCount = selectedTopicIds.length + selectedObjectiveIds.length;
  const deliveryResourceMutationError =
    bindDeliveryResource.error ?? removeDeliveryResource.error;

  useEffect(() => {
    if (lesson.lesson_kind !== 'mediacms_video' || !mediaCmsPickerOrigin) {
      return;
    }
    function receiveMediaSelection(event: MessageEvent<unknown>) {
      if (
        event.origin !== mediaCmsPickerOrigin ||
        !mediaPickerWindow.current ||
        !record(event.data) ||
        event.data.channel !== 'lms-mediacms-picker-v1' ||
        typeof event.data.nonce !== 'string' ||
        event.data.nonce !== mediaPickerNonce.current ||
        typeof event.data.mediaFriendlyToken !== 'string' ||
        !/^[A-Za-z0-9_-]{1,64}$/.test(event.data.mediaFriendlyToken)
      ) {
        return;
      }
      setMediaCmsFriendlyToken(event.data.mediaFriendlyToken);
      setMediaPickerError('');
      mediaPickerWindow.current = null;
      mediaPickerNonce.current = null;
    }
    window.addEventListener('message', receiveMediaSelection);
    return () => window.removeEventListener('message', receiveMediaSelection);
  }, [lesson.lesson_kind, mediaCmsPickerOrigin]);

  useEffect(() => {
    function receiveStoredMediaSelection(event: StorageEvent) {
      if (event.key !== 'lms-mediacms-picker-selection' || !event.newValue)
        return;
      try {
        const data: unknown = JSON.parse(event.newValue);
        if (
          !record(data) ||
          data.channel !== 'lms-mediacms-picker-v1' ||
          typeof data.nonce !== 'string' ||
          data.nonce !== mediaPickerNonce.current ||
          typeof data.mediaFriendlyToken !== 'string' ||
          !/^[A-Za-z0-9_-]{1,64}$/.test(data.mediaFriendlyToken)
        )
          return;
        setMediaCmsFriendlyToken(data.mediaFriendlyToken);
        setMediaPickerError('');
        mediaPickerWindow.current?.close();
        mediaPickerWindow.current = null;
        mediaPickerNonce.current = null;
        if (mediaPickerPoll.current !== null) {
          window.clearInterval(mediaPickerPoll.current);
          mediaPickerPoll.current = null;
        }
        window.localStorage.removeItem('lms-mediacms-picker-selection');
      } catch {
        // La selección no cumple el contrato local del popup.
      }
    }
    window.addEventListener('storage', receiveStoredMediaSelection);
    return () =>
      window.removeEventListener('storage', receiveStoredMediaSelection);
  }, []);

  useEffect(
    () => () => {
      if (mediaPickerPoll.current !== null) {
        window.clearInterval(mediaPickerPoll.current);
      }
    },
    [],
  );

  function openMediaPicker() {
    if (!mediaCmsAuthoringUrl || !mediaCmsPickerOrigin) {
      setMediaPickerError(
        'El selector de MediaCMS no está configurado para este entorno.',
      );
      return;
    }
    const pickerUrl = new URL('/lti/media-picker/', mediaCmsAuthoringUrl);
    const nonce = crypto.randomUUID();
    pickerUrl.searchParams.set('origin', window.location.origin);
    pickerUrl.searchParams.set('nonce', nonce);
    mediaPickerNonce.current = nonce;
    const popup = window.open(
      pickerUrl.toString(),
      'lms-mediacms-picker',
      'popup,width=760,height=680',
    );
    if (!popup) {
      setMediaPickerError(
        'El navegador bloqueó el selector. Permite la ventana emergente e inténtalo de nuevo.',
      );
      return;
    }
    mediaPickerWindow.current = popup;
    if (mediaPickerPoll.current !== null) {
      window.clearInterval(mediaPickerPoll.current);
    }
    mediaPickerPoll.current = window.setInterval(() => {
      const current = mediaPickerWindow.current;
      if (!current || current.closed) {
        if (mediaPickerPoll.current !== null) {
          window.clearInterval(mediaPickerPoll.current);
          mediaPickerPoll.current = null;
        }
        return;
      }
      try {
        if (current.location.origin !== window.location.origin) return;
        const callback = new URL(current.location.href);
        const token = callback.searchParams.get('mediaFriendlyToken') ?? '';
        const returnedNonce = callback.searchParams.get('nonce') ?? '';
        if (
          callback.pathname !== '/auth/mediacms-picker-callback' ||
          returnedNonce !== mediaPickerNonce.current ||
          !/^[A-Za-z0-9_-]{1,64}$/.test(token)
        )
          return;
        setMediaCmsFriendlyToken(token);
        setMediaPickerError('');
        current.close();
        mediaPickerWindow.current = null;
        mediaPickerNonce.current = null;
        if (mediaPickerPoll.current !== null) {
          window.clearInterval(mediaPickerPoll.current);
          mediaPickerPoll.current = null;
        }
      } catch {
        // El popup sigue en el origen aislado de MediaCMS.
      }
    }, 200);
    setMediaPickerError('');
    popup.focus();
  }

  function toggle(current: string[], id: string, checked: boolean) {
    return checked
      ? [...new Set([...current, id])]
      : current.filter((x) => x !== id);
  }

  return (
    <form
      action={() => {
        const input = {
          estimatedDurationMinutes: duration ? Number(duration) : null,
          learningObjectiveIds: selectedObjectiveIds,
          summary,
          title,
          topicIds: selectedTopicIds,
        };
        return lesson.lesson_kind === 'mediacms_video'
          ? onSave({
              ...input,
              mediaCmsFriendlyToken: mediaCmsFriendlyToken.trim(),
            })
          : onSave(input);
      }}
      className="mt-3 overflow-hidden rounded-xl border bg-card shadow-xs"
    >
      <header className="flex flex-wrap items-start justify-between gap-3 border-b bg-muted/15 px-4 py-4 sm:px-5">
        <div>
          <p className="text-xs font-semibold tracking-wider text-primary uppercase">
            Configuración integral
          </p>
          <h5 className="mt-1 font-semibold">
            Define la lección en un solo paso
          </h5>
          <p className="mt-1 text-sm text-muted-foreground">
            La información y la alineación se guardan juntas, sin estados
            parciales.
          </p>
        </div>
        <Badge variant={alignmentCount ? 'secondary' : 'outline'}>
          {alignmentCount}{' '}
          {alignmentCount === 1 ? 'alineación' : 'alineaciones'}
        </Badge>
      </header>

      <div className="grid min-w-0 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
        <section className="border-b p-4 sm:p-5 xl:border-r xl:border-b-0">
          <div className="mb-4 flex items-center gap-2">
            <BookOpenCheck className="size-4 text-primary" />
            <h6 className="font-semibold">Información esencial</h6>
          </div>
          <div className="grid gap-4">
            <div className="space-y-2">
              <Label htmlFor={`lesson-title-${lesson.id}`}>Título</Label>
              <Input
                id={`lesson-title-${lesson.id}`}
                maxLength={200}
                onChange={(event) => setTitle(event.target.value)}
                required
                value={title}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={`lesson-summary-${lesson.id}`}>Resumen</Label>
              <Textarea
                id={`lesson-summary-${lesson.id}`}
                maxLength={1200}
                onChange={(event) => setSummary(event.target.value)}
                placeholder="Explica qué aprenderá la persona en esta lección."
                rows={5}
                value={summary}
              />
            </div>
            <div className="max-w-56 space-y-2">
              <Label htmlFor={`lesson-duration-${lesson.id}`}>
                Duración estimada
              </Label>
              <div className="relative">
                <Input
                  className="pr-16"
                  id={`lesson-duration-${lesson.id}`}
                  min={1}
                  onChange={(event) => setDuration(event.target.value)}
                  placeholder="45"
                  type="number"
                  value={duration}
                />
                <span className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-xs text-muted-foreground">
                  minutos
                </span>
              </div>
            </div>
            {lesson.lesson_kind === 'mediacms_video' ? (
              <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <Video className="size-4 text-primary" />
                  Vídeo privado de MediaCMS
                </div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Elige un vídeo privado ya procesado. La LMS vincula sólo ese
                  vídeo a esta lección.
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Button onClick={openMediaPicker} size="sm" type="button">
                    <Video data-icon="inline-start" />
                    {mediaCmsFriendlyToken ? 'Cambiar vídeo' : 'Elegir vídeo'}
                  </Button>
                  {mediaCmsAuthoringUrl ? (
                    <Button asChild size="sm" type="button" variant="outline">
                      <a
                        href={mediaCmsAuthoringUrl}
                        rel="noreferrer"
                        target="_blank"
                      >
                        Abrir MediaCMS
                        <ExternalLink data-icon="inline-end" />
                      </a>
                    </Button>
                  ) : null}
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                  {mediaCmsFriendlyToken
                    ? 'Vídeo seleccionado y listo para guardar con esta misma versión.'
                    : 'Aún no has seleccionado un vídeo.'}
                </p>
                {mediaPickerError ? (
                  <p className="mt-2 text-xs text-destructive" role="alert">
                    {mediaPickerError}
                  </p>
                ) : null}
              </div>
            ) : null}
            {resourceLessonKind(lesson.lesson_kind) ? (
              <section className="rounded-lg border border-primary/20 bg-primary/5 p-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 text-sm font-semibold">
                      {lesson.lesson_kind === 'audio' ? (
                        <FileAudio className="size-4 text-primary" />
                      ) : (
                        <FileText className="size-4 text-primary" />
                      )}
                      Archivo único de la lección
                    </div>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">
                      Esta modalidad no muestra documento académico, texto
                      adicional ni otros recursos.
                    </p>
                  </div>
                  {bindDeliveryResource.isPending ||
                  removeDeliveryResource.isPending ? (
                    <LoaderCircle className="size-4 animate-spin text-primary" />
                  ) : null}
                </div>
                {deliveryResource.isLoading ? (
                  <p className="mt-3 text-sm text-muted-foreground">
                    Consultando archivo vinculado…
                  </p>
                ) : deliveryResource.error ? (
                  <p className="mt-3 text-sm text-destructive">
                    {deliveryResource.error instanceof Error
                      ? deliveryResource.error.message
                      : 'No fue posible consultar el archivo vinculado.'}
                  </p>
                ) : deliveryResource.data?.resource ? (
                  <div className="mt-3 rounded-md border bg-background p-3 text-sm">
                    <strong className="break-all">
                      {deliveryResource.data.resource.original_filename}
                    </strong>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      {deliveryResource.data.resource.detected_mime_type} ·{' '}
                      {deliveryResource.data.resource.asset_version_id}
                    </p>
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-amber-700">
                    Aún no hay archivo. La revisión no podrá publicarse hasta
                    seleccionar uno.
                  </p>
                )}
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <AssetPickerDialog
                    allowedKinds={
                      lesson.lesson_kind === 'audio' ? ['audio'] : ['document']
                    }
                    onInsert={(node) => {
                      const attrs = record(node.attrs) ? node.attrs : null;
                      const assetVersionId = attrs?.assetVersionId;
                      if (typeof assetVersionId === 'string') {
                        bindDeliveryResource.mutate(assetVersionId);
                      }
                    }}
                    resourceOnly
                    slug={organizationSlug}
                    triggerLabel="Seleccionar o subir archivo"
                  />
                  {deliveryResource.data?.resource ? (
                    <Button
                      disabled={removeDeliveryResource.isPending}
                      onClick={() => removeDeliveryResource.mutate()}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      <Link2 data-icon="inline-start" />
                      Desvincular
                    </Button>
                  ) : null}
                  {deliveryResourceMutationError ? (
                    <p className="basis-full text-sm text-destructive">
                      {deliveryResourceMutationError instanceof Error
                        ? deliveryResourceMutationError.message
                        : 'No fue posible actualizar el archivo de la lección.'}
                    </p>
                  ) : null}
                </div>
              </section>
            ) : null}
          </div>
        </section>

        <section className="min-w-0 p-4 sm:p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <GraduationCap className="size-4 text-primary" />
                <h6 className="font-semibold">Alineación curricular</h6>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Solo se muestran referencias válidas para esta revisión.
              </p>
            </div>
            <div
              className="flex flex-wrap gap-1.5"
              aria-label="Asignaturas alineadas"
            >
              {alignedSubjects.map((item) => (
                <Button
                  aria-pressed={activeSubjectId === item.subject.id}
                  className="h-7 rounded-full px-2.5 text-xs"
                  key={item.subject.id}
                  onClick={() => {
                    setActiveSubjectId(item.subject.id);
                    setQuery('');
                  }}
                  size="sm"
                  type="button"
                  variant={
                    activeSubjectId === item.subject.id
                      ? 'secondary'
                      : 'outline'
                  }
                >
                  {item.subject.name}
                  {item.alignment_type === 'primary' ? ' · principal' : ''}
                </Button>
              ))}
            </div>
          </div>

          {isLoadingTopics ? (
            <div className="mt-4 rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
              Cargando la taxonomía complementaria…
            </div>
          ) : didTopicsFail ? (
            <div className="mt-4 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-5 text-sm text-destructive">
              No fue posible cargar los temas de esta asignatura. Intenta
              abrirla de nuevo antes de guardar.
            </div>
          ) : hasCurriculumOptions ? (
            <>
              <div className="relative mt-4">
                <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  aria-label="Buscar temas u objetivos"
                  className="pl-9"
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Buscar por tema, código, objetivo o asignatura"
                  type="search"
                  value={query}
                />
              </div>
              <div className="mt-4 grid min-w-0 gap-4 2xl:grid-cols-2">
                <AlignmentGroup
                  emptyLabel={
                    normalizedQuery
                      ? 'Ningún tema coincide con la búsqueda.'
                      : 'Las asignaturas alineadas aún no tienen temas.'
                  }
                  icon={BookOpenCheck}
                  label="Temas"
                  selectedCount={
                    activeTopics.filter((topic) =>
                      selectedTopicIds.includes(topic.id),
                    ).length
                  }
                >
                  {visibleTopics.map((topic) => (
                    <AlignmentOption
                      checked={selectedTopicIds.includes(topic.id)}
                      key={topic.id}
                      label={topic.title}
                      onChange={(checked) =>
                        setSelectedTopicIds((ids) =>
                          toggle(ids, topic.id, checked),
                        )
                      }
                      context={topic.ancestor_titles.join(' › ')}
                      subject={topic.subject_name}
                    />
                  ))}
                </AlignmentGroup>
                <AlignmentGroup
                  emptyLabel={
                    normalizedQuery
                      ? 'Ningún objetivo coincide con la búsqueda.'
                      : 'La revisión aún no tiene objetivos seleccionados.'
                  }
                  icon={Target}
                  label="Objetivos de la revisión"
                  selectedCount={
                    activeObjectives.filter((objective) =>
                      selectedObjectiveIds.includes(objective.id),
                    ).length
                  }
                >
                  {visibleObjectives.map((objective) => (
                    <AlignmentOption
                      checked={selectedObjectiveIds.includes(objective.id)}
                      code={objective.code}
                      key={objective.id}
                      label={objective.statement}
                      onChange={(checked) =>
                        setSelectedObjectiveIds((ids) =>
                          toggle(ids, objective.id, checked),
                        )
                      }
                      subject={
                        subjectById.get(objective.subject_id)?.subject.name
                      }
                    />
                  ))}
                </AlignmentGroup>
              </div>
            </>
          ) : (
            <div className="mt-4 rounded-xl border border-dashed bg-muted/10 px-5 py-7 text-center">
              <Target className="mx-auto size-5 text-muted-foreground" />
              <p className="mt-3 text-sm font-semibold">
                Esta asignatura aún no tiene currículo utilizable
              </p>
              <p className="mx-auto mt-1 max-w-md text-xs leading-5 text-muted-foreground">
                Agrega temas a {activeSubject?.subject.name ?? 'la asignatura'}{' '}
                y selecciona sus objetivos en la alineación de la revisión. Las
                complementarias se consultan solo cuando las abres.
              </p>
              <Button asChild className="mt-4" size="sm" variant="outline">
                <Link
                  href={
                    activeSubject
                      ? `/organizaciones/${organizationSlug}/curriculo/asignaturas/${activeSubject.subject.id}`
                      : `/organizaciones/${organizationSlug}/curriculo`
                  }
                >
                  Abrir currículo institucional
                  <ExternalLink data-icon="inline-end" />
                </Link>
              </Button>
            </div>
          )}
        </section>
      </div>

      <footer className="flex flex-col-reverse gap-3 border-t bg-muted/10 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <Button onClick={onArchive} type="button" variant="ghost">
          <Archive /> Archivar lección
        </Button>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <p className="text-xs text-muted-foreground">
            Un guardado · una versión · sin cambios parciales
          </p>
          <Button disabled={isSaving} type="submit">
            <Save /> {isSaving ? 'Guardando…' : 'Guardar configuración'}
          </Button>
        </div>
      </footer>
    </form>
  );
}

function AlignmentGroup({
  children,
  emptyLabel,
  icon: Icon,
  label,
  selectedCount,
}: Readonly<{
  children: React.ReactNode;
  emptyLabel: string;
  icon: typeof Target;
  label: string;
  selectedCount: number;
}>) {
  const hasItems = Array.isArray(children)
    ? children.length > 0
    : Boolean(children);
  return (
    <fieldset className="min-w-0 overflow-hidden rounded-lg border bg-background">
      <legend className="sr-only">{label}</legend>
      <div className="flex items-center justify-between gap-3 border-b bg-muted/15 px-3 py-2.5">
        <span className="flex items-center gap-2 text-sm font-semibold">
          <Icon className="size-4 text-primary" /> {label}
        </span>
        <Badge variant="outline">{selectedCount} seleccionados</Badge>
      </div>
      <div className="max-h-64 overflow-y-auto p-2">
        {hasItems ? (
          <div className="grid gap-1">{children}</div>
        ) : (
          <p className="px-2 py-6 text-center text-xs text-muted-foreground">
            {emptyLabel}
          </p>
        )}
      </div>
    </fieldset>
  );
}

function AlignmentOption({
  checked,
  code,
  context,
  label,
  onChange,
  subject,
}: Readonly<{
  checked: boolean;
  code?: string;
  context?: string | undefined;
  label: string;
  onChange: (checked: boolean) => void;
  subject?: string | undefined;
}>) {
  return (
    <label
      className={cn(
        'flex cursor-pointer gap-3 rounded-md border border-transparent px-2.5 py-2 text-sm transition-colors hover:bg-muted/40',
        checked && 'border-primary/20 bg-primary/[0.035]',
      )}
    >
      <input
        checked={checked}
        className="mt-0.5 size-4 shrink-0 accent-primary"
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
      <span className="min-w-0">
        <span className="block leading-5">
          {code ? <strong className="font-mono text-xs">{code}</strong> : null}
          {code ? ' — ' : null}
          {label}
        </span>
        {context ? (
          <span className="mt-0.5 block truncate text-[0.6875rem] text-muted-foreground">
            {context}
          </span>
        ) : null}
        {subject ? (
          <span className="mt-0.5 block text-[0.6875rem] text-muted-foreground">
            {subject}
          </span>
        ) : null}
      </span>
    </label>
  );
}
