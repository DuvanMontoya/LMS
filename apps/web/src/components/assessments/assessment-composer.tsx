'use client';

import {
  CircleAlert,
  FileCheck2,
  ListChecks,
  Save,
  Search,
  Settings2,
  ShieldCheck,
  Target,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { MutationError } from '@/components/assessments/authoring-forms';
import {
  addAssessmentItem,
  createAssessmentPool,
  addAssessmentSection,
  replaceAssessmentObjectives,
  reorderAssessmentItems,
  reorderAssessmentSections,
  replaceAssessmentPoolCandidates,
  transitionAssessmentRevision,
  updateAssessmentPool,
  updateAssessmentItem,
  updateAssessmentRevision,
  useAssessmentMutation,
} from '@/lib/assessments/hooks';
import type {
  AssessmentOutline,
  AssessmentPool,
  AssessmentReadiness,
  CatalogSubject,
  LearningObjective,
  QuestionVersion,
} from '@/lib/assessments/server';

type OutlineItem = {
  id: string;
  objective_ids: string[];
  points: string;
  position: number;
  question_code: string;
  question_type: string;
  question_version_id: string;
  required: boolean;
};
type OutlineSection = {
  id: string;
  instructions: string;
  items: OutlineItem[];
  position: number;
  title: string;
};
type QuestionOption = Pick<
  QuestionVersion,
  'id' | 'number' | 'public' | 'type'
> & {
  bankName: string;
  code: string;
};

export function AssessmentComposer({
  assessmentSlug,
  canApprove,
  canManage,
  canReview,
  canSubmit,
  objectives,
  outline,
  pools,
  questions,
  readiness,
  slug,
  subjects,
}: Readonly<{
  assessmentSlug: string;
  canApprove: boolean;
  canManage: boolean;
  canReview: boolean;
  canSubmit: boolean;
  objectives: LearningObjective[];
  outline: AssessmentOutline;
  pools: AssessmentPool[];
  questions: QuestionOption[];
  readiness: AssessmentReadiness;
  slug: string;
  subjects: CatalogSubject[];
}>) {
  const router = useRouter();
  const revision = outline.revision;
  const path = {
    assessmentSlug,
    revisionId: revision.id,
    slug,
  };
  const editable =
    canManage &&
    (revision.status === 'draft' || revision.status === 'changes_requested');
  const [title, setTitle] = useState(revision.title);
  const [description, setDescription] = useState(revision.description);
  const [instructions, setInstructions] = useState(revision.instructions);
  const [timeLimit, setTimeLimit] = useState(
    revision.time_limit_minutes?.toString() ?? '',
  );
  const [attemptLimit, setAttemptLimit] = useState(
    revision.attempt_limit?.toString() ?? '',
  );
  const [passPercent, setPassPercent] = useState(
    (revision.pass_basis_points / 100).toString(),
  );
  const [shuffleSections, setShuffleSections] = useState(
    revision.shuffle_sections,
  );
  const [shuffleItems, setShuffleItems] = useState(revision.shuffle_items);
  const [feedbackMode, setFeedbackMode] = useState(revision.feedback_mode);
  const [selectedObjectives, setSelectedObjectives] = useState<string[]>(
    outline.objective_ids,
  );
  const selectedObjectiveSubjects = new Set(
    objectives
      .filter((objective) => selectedObjectives.includes(objective.id))
      .map((objective) => objective.subject_id),
  );
  const [objectiveSubjectId, setObjectiveSubjectId] = useState(
    selectedObjectiveSubjects.size === 1
      ? ([...selectedObjectiveSubjects][0] ?? '')
      : '',
  );
  const [includeOtherSubjects, setIncludeOtherSubjects] = useState(
    selectedObjectiveSubjects.size > 1,
  );
  const [objectiveQuery, setObjectiveQuery] = useState('');
  const [sectionTitle, setSectionTitle] = useState('');
  const [note, setNote] = useState('');
  const metadata = useAssessmentMutation(() =>
    updateAssessmentRevision(path, {
      description,
      expected_version: revision.lock_version,
      feedback_mode: feedbackMode,
      instructions,
      attempt_limit: attemptLimit ? Number(attemptLimit) : null,
      pass_basis_points: Math.round(Number(passPercent) * 100),
      shuffle_items: shuffleItems,
      shuffle_sections: shuffleSections,
      time_limit_minutes: timeLimit ? Number(timeLimit) : null,
      title,
    }),
  );
  const objectiveMutation = useAssessmentMutation(() =>
    replaceAssessmentObjectives(path, {
      expected_version: revision.lock_version,
      objective_ids: selectedObjectives,
    }),
  );
  const sectionMutation = useAssessmentMutation(() =>
    addAssessmentSection(path, {
      expected_version: revision.lock_version,
      instructions: '',
      title: sectionTitle,
    }),
  );
  const sectionOrderMutation = useAssessmentMutation((ids: string[]) =>
    reorderAssessmentSections(path, {
      expected_version: revision.lock_version,
      ids,
    }),
  );
  const transition = useAssessmentMutation(
    (action: 'approve' | 'request-changes' | 'submit-review') =>
      transitionAssessmentRevision(path, action, {
        expected_version: revision.lock_version,
        note,
      }),
  );
  async function refresh(operation: Promise<unknown>) {
    try {
      await operation;
      router.refresh();
    } catch {
      // Cada mutación mantiene su error para presentarlo sin activar el overlay.
    }
  }
  const sections = outline.sections as OutlineSection[];
  const itemCount = sections.reduce(
    (count, section) => count + section.items.length,
    0,
  );
  const selectedPoolItemCount = pools.reduce(
    (count, pool) => count + pool.selection_count,
    0,
  );
  const maximumScore =
    sections
      .flatMap((section) => section.items)
      .reduce((total, item) => total + Number(item.points), 0) +
    pools.reduce(
      (total, pool) =>
        total + pool.selection_count * Number(pool.points_per_item),
      0,
    );
  const normalizedObjectiveQuery = objectiveQuery.trim().toLocaleLowerCase();
  const objectiveSubjects = subjects.filter((subject) =>
    objectives.some((objective) => objective.subject_id === subject.id),
  );
  const visibleObjectives = objectives.filter((objective) => {
    if (!objectiveSubjectId && !includeOtherSubjects) return false;
    if (
      objectiveSubjectId &&
      !includeOtherSubjects &&
      objective.subject_id !== objectiveSubjectId
    ) {
      return false;
    }
    if (!normalizedObjectiveQuery) return true;
    return `${objective.code} ${objective.statement}`
      .toLocaleLowerCase()
      .includes(normalizedObjectiveQuery);
  });
  const assessmentObjectives = objectives.filter((objective) =>
    selectedObjectives.includes(objective.id),
  );
  return (
    <>
      <section className="assessment-composer-summary">
        <div>
          <p>Revisión {revision.number}</p>
          <h2>{revision.title}</h2>
        </div>
        <dl>
          <div>
            <dt>Secciones</dt>
            <dd>{sections.length}</dd>
          </div>
          <div>
            <dt>Preguntas</dt>
            <dd>{itemCount + selectedPoolItemCount}</dd>
          </div>
          <div>
            <dt>Puntaje</dt>
            <dd>{maximumScore.toFixed(3)}</dd>
          </div>
          <div>
            <dt>Estado</dt>
            <dd>{revisionStatusLabel(revision.status)}</dd>
          </div>
        </dl>
      </section>
      <div className="mt-4 space-y-4">
        <div className="space-y-5">
          <details className="assessment-composer-card assessment-composer-settings">
            <summary className="assessment-composer-card__header">
              <div>
                <span className="assessment-icon-box">
                  <Settings2 />
                </span>
                <div>
                  <h2>Configuración y políticas</h2>
                  <p>Identidad, límites y comportamiento del intento.</p>
                </div>
              </div>
              <Badge
                className="assessment-status"
                data-status={revision.status}
                variant="outline"
              >
                {revisionStatusLabel(revision.status)}
              </Badge>
            </summary>
            <div className="assessment-composer-card__body">
              <Label htmlFor="assessment-editor-title">Título</Label>
              <Input
                disabled={!editable}
                id="assessment-editor-title"
                onChange={(event) => setTitle(event.target.value)}
                value={title}
              />
              <Label htmlFor="assessment-editor-description">Descripción</Label>
              <Textarea
                disabled={!editable}
                id="assessment-editor-description"
                onChange={(event) => setDescription(event.target.value)}
                value={description}
              />
              <Label htmlFor="assessment-editor-instructions">
                Instrucciones
              </Label>
              <Textarea
                disabled={!editable}
                id="assessment-editor-instructions"
                onChange={(event) => setInstructions(event.target.value)}
                value={instructions}
              />
              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <Label htmlFor="assessment-editor-time">
                    Tiempo límite (min)
                  </Label>
                  <Input
                    disabled={!editable}
                    id="assessment-editor-time"
                    min="1"
                    onChange={(event) => setTimeLimit(event.target.value)}
                    type="number"
                    value={timeLimit}
                  />
                </div>
                <div>
                  <Label htmlFor="assessment-editor-attempts">
                    Intentos permitidos
                  </Label>
                  <Input
                    disabled={!editable}
                    id="assessment-editor-attempts"
                    min="1"
                    onChange={(event) => setAttemptLimit(event.target.value)}
                    type="number"
                    value={attemptLimit}
                  />
                </div>
                <div>
                  <Label htmlFor="assessment-editor-pass">
                    Umbral de aprobación
                  </Label>
                  <Input
                    disabled={!editable}
                    id="assessment-editor-pass"
                    max="100"
                    min="0"
                    onChange={(event) => setPassPercent(event.target.value)}
                    step="0.01"
                    type="number"
                    value={passPercent}
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    Porcentaje mínimo para aprobar.
                  </p>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    checked={shuffleSections}
                    disabled={!editable}
                    onChange={(event) =>
                      setShuffleSections(event.target.checked)
                    }
                    type="checkbox"
                  />
                  Barajar secciones
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    checked={shuffleItems}
                    disabled={!editable}
                    onChange={(event) => setShuffleItems(event.target.checked)}
                    type="checkbox"
                  />
                  Barajar preguntas
                </label>
              </div>
              <Label htmlFor="assessment-editor-feedback">
                Política de feedback
              </Label>
              <select
                className="academic-control"
                disabled={!editable}
                id="assessment-editor-feedback"
                onChange={(event) =>
                  setFeedbackMode(
                    event.target.value as typeof revision.feedback_mode,
                  )
                }
                value={feedbackMode}
              >
                <option value="none">Sin feedback</option>
                <option value="score_only">
                  Sólo puntaje después de calificar
                </option>
                <option value="full_after_grading">
                  Feedback completo después de calificar
                </option>
              </select>
              {editable ? (
                <Button
                  disabled={metadata.isPending}
                  onClick={() => refresh(metadata.mutateAsync(undefined))}
                  type="button"
                >
                  <Save data-icon="inline-start" /> Guardar configuración
                </Button>
              ) : null}
              <MutationError error={metadata.error} />
            </div>
          </details>

          <section className="assessment-composer-card">
            <div className="assessment-composer-card__header">
              <div>
                <span className="assessment-icon-box">
                  <Target />
                </span>
                <div>
                  <h2>Objetivos de aprendizaje</h2>
                  <p>
                    Define la evidencia curricular que debe cubrir el
                    instrumento.
                  </p>
                </div>
              </div>
              <span className="assessment-composer-card__count">
                {selectedObjectives.length}{' '}
                {selectedObjectives.length === 1
                  ? 'seleccionado'
                  : 'seleccionados'}
              </span>
            </div>
            <div className="assessment-composer-card__body">
              <div className="grid gap-4 rounded-xl border bg-muted/20 p-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                <div>
                  <Label htmlFor="assessment-objective-subject">
                    Asignatura evaluada
                  </Label>
                  <select
                    className="academic-control mt-1.5"
                    disabled={!editable}
                    id="assessment-objective-subject"
                    onChange={(event) => {
                      const nextSubjectId = event.target.value;
                      setObjectiveSubjectId(nextSubjectId);
                      if (!includeOtherSubjects) {
                        setSelectedObjectives((current) =>
                          current.filter((objectiveId) =>
                            objectives.some(
                              (objective) =>
                                objective.id === objectiveId &&
                                objective.subject_id === nextSubjectId,
                            ),
                          ),
                        );
                      }
                    }}
                    value={objectiveSubjectId}
                  >
                    <option value="">Selecciona una asignatura</option>
                    {objectiveSubjects.map((subject) => (
                      <option key={subject.id} value={subject.id}>
                        {subject.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label htmlFor="assessment-objective-search">
                    Buscar objetivo
                  </Label>
                  <Input
                    className="mt-1.5"
                    id="assessment-objective-search"
                    onChange={(event) => setObjectiveQuery(event.target.value)}
                    placeholder="Código o descripción"
                    value={objectiveQuery}
                  />
                </div>
                <label className="flex items-start gap-2 text-sm sm:col-span-2">
                  <input
                    checked={includeOtherSubjects}
                    disabled={!editable || !objectiveSubjectId}
                    onChange={(event) =>
                      setIncludeOtherSubjects(event.target.checked)
                    }
                    type="checkbox"
                  />
                  <span>
                    Incluir objetivos de otras asignaturas
                    <span className="block text-xs text-muted-foreground">
                      Úsalo sólo para instrumentos interdisciplinarios.
                    </span>
                  </span>
                </label>
              </div>
              <fieldset className="assessment-objective-grid">
                <legend className="sr-only">Objetivos vinculados</legend>
                {visibleObjectives.map((objective) => (
                  <label
                    data-selected={selectedObjectives.includes(objective.id)}
                    key={objective.id}
                  >
                    <input
                      checked={selectedObjectives.includes(objective.id)}
                      disabled={!editable}
                      onChange={(event) =>
                        setSelectedObjectives((current) =>
                          event.target.checked
                            ? [...current, objective.id]
                            : current.filter((id) => id !== objective.id),
                        )
                      }
                      type="checkbox"
                    />
                    <span className="min-w-0">
                      <strong>{objective.code}</strong>
                      <span>{objective.statement}</span>
                    </span>
                  </label>
                ))}
              </fieldset>
              {!objectiveSubjectId ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  Selecciona la asignatura para trabajar con un conjunto breve y
                  pertinente de objetivos.
                </p>
              ) : null}
              {editable ? (
                <Button
                  className="mt-4"
                  disabled={objectiveMutation.isPending}
                  onClick={() =>
                    refresh(objectiveMutation.mutateAsync(undefined))
                  }
                  type="button"
                  variant="outline"
                >
                  Guardar objetivos
                </Button>
              ) : null}
              <MutationError error={objectiveMutation.error} />
            </div>
          </section>

          <section className="assessment-composer-card">
            <header className="assessment-composer-card__header">
              <div>
                <span className="assessment-icon-box">
                  <ListChecks />
                </span>
                <div>
                  <h2>Mapa de composición</h2>
                  <p>
                    {sections.length}{' '}
                    {sections.length === 1 ? 'sección' : 'secciones'} ·{' '}
                    {itemCount}{' '}
                    {itemCount === 1 ? 'pregunta fija' : 'preguntas fijas'} ·{' '}
                    {pools.length} {pools.length === 1 ? 'pool' : 'pools'}
                  </p>
                </div>
              </div>
            </header>
            <ol className="assessment-section-list">
              {sections.map((section, sectionIndex) => (
                <li key={section.id}>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold">
                      {section.position}. {section.title}
                    </h3>
                    {editable ? (
                      <OrderButtons
                        disabled={sectionOrderMutation.isPending}
                        index={sectionIndex}
                        label="sección"
                        length={sections.length}
                        onMove={(direction) =>
                          refresh(
                            sectionOrderMutation.mutateAsync(
                              movedIds(sections, sectionIndex, direction),
                            ),
                          )
                        }
                      />
                    ) : null}
                  </div>
                  {section.instructions ? (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {section.instructions}
                    </p>
                  ) : null}
                  <ol className="assessment-item-list">
                    {section.items.map((item, itemIndex) => (
                      <AssessmentItemRow
                        editable={editable}
                        index={itemIndex}
                        item={item}
                        items={section.items}
                        key={item.id}
                        length={section.items.length}
                        lockVersion={revision.lock_version}
                        objectives={assessmentObjectives}
                        path={{ ...path, sectionId: section.id }}
                      />
                    ))}
                  </ol>
                  {editable ? (
                    <AssessmentItemForm
                      lockVersion={revision.lock_version}
                      objectives={assessmentObjectives}
                      path={{ ...path, sectionId: section.id }}
                      questions={questions}
                    />
                  ) : null}
                </li>
              ))}
            </ol>
            {editable ? (
              <div className="assessment-add-section">
                <Label className="sr-only" htmlFor="new-section-title">
                  Título de la nueva sección
                </Label>
                <Input
                  id="new-section-title"
                  onChange={(event) => setSectionTitle(event.target.value)}
                  placeholder="Nueva sección"
                  value={sectionTitle}
                />
                <Button
                  disabled={!sectionTitle.trim() || sectionMutation.isPending}
                  onClick={async () => {
                    try {
                      await sectionMutation.mutateAsync(undefined);
                      setSectionTitle('');
                      router.refresh();
                    } catch {
                      // React Query conserva el error junto al mapa.
                    }
                  }}
                  type="button"
                  variant="outline"
                >
                  Añadir sección
                </Button>
              </div>
            ) : null}
            <div className="px-5 pb-5 sm:px-6">
              <MutationError
                error={sectionMutation.error ?? sectionOrderMutation.error}
              />
            </div>
          </section>
          <AssessmentPoolComposer
            editable={editable}
            lockVersion={revision.lock_version}
            path={path}
            pools={pools}
            questions={questions}
          />
        </div>

        <aside className="assessment-governance-rail">
          <section>
            <div className="assessment-governance-rail__title">
              {readiness.ready ? <FileCheck2 /> : <CircleAlert />}
              <div>
                <p>Control de preparación</p>
                <h2>
                  {readiness.ready
                    ? 'Lista para revisión'
                    : 'Requiere atención'}
                </h2>
              </div>
            </div>
            {readiness.issues.length ? (
              <ul className="assessment-readiness-list">
                {readiness.issues.map((issue) => (
                  <li key={issue}>{readinessIssueLabel(issue)}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">
                La revisión satisface las invariantes de composición.
              </p>
            )}
          </section>
          <section className="assessment-governance-rail__workflow">
            <div className="assessment-governance-rail__title">
              <ShieldCheck />
              <div>
                <p>Gobierno editorial</p>
                <h2>Flujo de revisión</h2>
              </div>
            </div>
            <Label htmlFor="assessment-review-note">Nota</Label>
            <Textarea
              id="assessment-review-note"
              onChange={(event) => setNote(event.target.value)}
              value={note}
            />
            {canSubmit && editable ? (
              <Button
                className="w-full"
                disabled={!readiness.ready || transition.isPending}
                onClick={() => refresh(transition.mutateAsync('submit-review'))}
                type="button"
              >
                Enviar a revisión
              </Button>
            ) : null}
            {canReview && revision.status === 'in_review' ? (
              <Button
                className="w-full"
                onClick={() =>
                  refresh(transition.mutateAsync('request-changes'))
                }
                type="button"
                variant="outline"
              >
                Solicitar cambios
              </Button>
            ) : null}
            {canApprove && revision.status === 'in_review' ? (
              <Button
                className="w-full"
                disabled={!readiness.ready}
                onClick={() => refresh(transition.mutateAsync('approve'))}
                type="button"
              >
                Aprobar y crear versión
              </Button>
            ) : null}
            <MutationError error={transition.error} />
          </section>
        </aside>
      </div>
    </>
  );
}

function AssessmentPoolComposer({
  editable,
  lockVersion,
  path,
  pools,
  questions,
}: Readonly<{
  editable: boolean;
  lockVersion: number;
  path: {
    assessmentSlug: string;
    revisionId: string;
    slug: string;
  };
  pools: AssessmentPool[];
  questions: QuestionOption[];
}>) {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [points, setPoints] = useState('1.000');
  const [selectionCount, setSelectionCount] = useState(1);
  const [candidateIds, setCandidateIds] = useState<string[]>([]);
  const createMutation = useAssessmentMutation(() =>
    createAssessmentPool(path, {
      expected_version: lockVersion,
      points_per_item: points,
      question_version_ids: candidateIds,
      selection_count: selectionCount,
      shuffle_selected: true,
      title,
    }),
  );
  return (
    <section className="assessment-composer-card">
      <header className="assessment-composer-card__header">
        <div>
          <span className="assessment-icon-box">
            <ListChecks />
          </span>
          <div>
            <h2>Pools aleatorios</h2>
            <p>
              Selección determinista sin reemplazo a partir de versiones
              aprobadas.
            </p>
          </div>
        </div>
        <span className="assessment-composer-card__count">
          {pools.length} {pools.length === 1 ? 'pool' : 'pools'}
        </span>
      </header>
      <div className="assessment-composer-card__body space-y-5">
        {pools.map((pool) => (
          <AssessmentPoolEditor
            editable={editable}
            key={pool.id}
            lockVersion={lockVersion}
            pool={pool}
            questions={questions}
            slug={path.slug}
          />
        ))}
        {!pools.length ? (
          <p className="text-sm text-muted-foreground">
            No hay pools configurados. Las preguntas fijas continúan funcionando
            sin cambios.
          </p>
        ) : null}
        {editable ? (
          <div className="space-y-4 border-t pt-5">
            <h3 className="font-semibold">Crear pool</h3>
            <div className="grid gap-4 sm:grid-cols-3">
              <label className="space-y-1.5 sm:col-span-3">
                <span className="text-sm font-medium">Título</span>
                <Input
                  maxLength={200}
                  onChange={(event) => setTitle(event.target.value)}
                  value={title}
                />
              </label>
              <label className="space-y-1.5">
                <span className="text-sm font-medium">Preguntas a elegir</span>
                <Input
                  max={Math.max(1, candidateIds.length)}
                  min="1"
                  onChange={(event) =>
                    setSelectionCount(Number(event.target.value))
                  }
                  type="number"
                  value={selectionCount}
                />
              </label>
              <label className="space-y-1.5">
                <span className="text-sm font-medium">Puntos por pregunta</span>
                <Input
                  min="0.001"
                  onChange={(event) => setPoints(event.target.value)}
                  step="0.001"
                  type="number"
                  value={points}
                />
              </label>
              <div className="flex items-end text-sm text-muted-foreground">
                Estrategia: random_without_replacement
              </div>
            </div>
            <QuestionCandidatePicker
              candidateIds={candidateIds}
              onChange={setCandidateIds}
              questions={questions}
            />
            <Button
              disabled={
                createMutation.isPending ||
                !title.trim() ||
                candidateIds.length < 2 ||
                selectionCount < 1 ||
                selectionCount > candidateIds.length
              }
              onClick={async () => {
                try {
                  await createMutation.mutateAsync(undefined);
                  setTitle('');
                  setCandidateIds([]);
                  setSelectionCount(1);
                  router.refresh();
                } catch {
                  // React Query conserva el error para presentación local.
                }
              }}
              type="button"
            >
              Crear pool
            </Button>
            <MutationError error={createMutation.error} />
          </div>
        ) : null}
      </div>
    </section>
  );
}

function AssessmentPoolEditor({
  editable,
  lockVersion,
  pool,
  questions,
  slug,
}: Readonly<{
  editable: boolean;
  lockVersion: number;
  pool: AssessmentPool;
  questions: QuestionOption[];
  slug: string;
}>) {
  const router = useRouter();
  const [title, setTitle] = useState(pool.title);
  const [instructions, setInstructions] = useState(pool.instructions);
  const [points, setPoints] = useState(pool.points_per_item);
  const [selectionCount, setSelectionCount] = useState(pool.selection_count);
  const [shuffleSelected, setShuffleSelected] = useState(pool.shuffle_selected);
  const [candidateIds, setCandidateIds] = useState(
    pool.candidates.map((candidate) => candidate.question_version_id),
  );
  const updateMutation = useAssessmentMutation(() =>
    updateAssessmentPool(slug, pool.id, {
      expected_version: lockVersion,
      instructions,
      points_per_item: points,
      selection_count: selectionCount,
      shuffle_selected: shuffleSelected,
      title,
    }),
  );
  const candidateMutation = useAssessmentMutation(() =>
    replaceAssessmentPoolCandidates(slug, pool.id, {
      expected_version: lockVersion,
      question_version_ids: candidateIds,
    }),
  );
  return (
    <article className="space-y-4 border p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">
            {pool.position}. {pool.title}
          </h3>
          <p className="text-sm text-muted-foreground">
            Elige {pool.selection_count} de {pool.candidates.length} preguntas ·{' '}
            {pool.points_per_item} puntos cada una
          </p>
        </div>
        <Badge variant="outline">Sin reemplazo</Badge>
      </div>
      {editable ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1.5">
              <span className="text-sm font-medium">Título</span>
              <Input
                onChange={(event) => setTitle(event.target.value)}
                value={title}
              />
            </label>
            <label className="space-y-1.5">
              <span className="text-sm font-medium">Instrucciones</span>
              <Input
                onChange={(event) => setInstructions(event.target.value)}
                value={instructions}
              />
            </label>
            <label className="space-y-1.5">
              <span className="text-sm font-medium">Selección</span>
              <Input
                max={candidateIds.length}
                min="1"
                onChange={(event) =>
                  setSelectionCount(Number(event.target.value))
                }
                type="number"
                value={selectionCount}
              />
            </label>
            <label className="space-y-1.5">
              <span className="text-sm font-medium">Puntos por pregunta</span>
              <Input
                min="0.001"
                onChange={(event) => setPoints(event.target.value)}
                step="0.001"
                type="number"
                value={points}
              />
            </label>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              checked={shuffleSelected}
              onChange={(event) => setShuffleSelected(event.target.checked)}
              type="checkbox"
            />
            Barajar las preguntas elegidas
          </label>
          <QuestionCandidatePicker
            candidateIds={candidateIds}
            lockedIds={pool.candidates.map(
              (candidate) => candidate.question_version_id,
            )}
            onChange={setCandidateIds}
            questions={questions}
          />
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={
                updateMutation.isPending ||
                selectionCount < 1 ||
                selectionCount > candidateIds.length
              }
              onClick={() =>
                void updateMutation
                  .mutateAsync(undefined)
                  .then(() => router.refresh())
              }
              type="button"
              variant="outline"
            >
              Guardar configuración
            </Button>
            <Button
              disabled={
                candidateMutation.isPending ||
                candidateIds.length < 2 ||
                selectionCount > candidateIds.length
              }
              onClick={() =>
                void candidateMutation
                  .mutateAsync(undefined)
                  .then(() => router.refresh())
              }
              type="button"
              variant="outline"
            >
              Guardar candidatos
            </Button>
          </div>
          <MutationError
            error={updateMutation.error ?? candidateMutation.error}
          />
        </>
      ) : (
        <ul className="space-y-1 text-sm">
          {pool.candidates.map((candidate) => (
            <li key={candidate.id}>
              {questionTypeLabel(candidate.type)} · versión{' '}
              {candidate.question_version_id.slice(0, 8)}
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

function QuestionCandidatePicker({
  candidateIds,
  lockedIds = [],
  onChange,
  questions,
}: Readonly<{
  candidateIds: string[];
  lockedIds?: string[];
  onChange: (ids: string[]) => void;
  questions: QuestionOption[];
}>) {
  const [query, setQuery] = useState('');
  const [type, setType] = useState('all');
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const types = useMemo(
    () => [...new Set(questions.map((question) => question.type))].sort(),
    [questions],
  );
  const visibleQuestions = useMemo(
    () =>
      questions.filter((question) => {
        if (type !== 'all' && question.type !== type) return false;
        if (!normalizedQuery) return true;
        return `${question.code} ${question.bankName} ${question.type} ${publicQuestionExcerpt(question.public)}`
          .toLocaleLowerCase()
          .includes(normalizedQuery);
      }),
    [normalizedQuery, questions, type],
  );
  return (
    <fieldset className="assessment-candidate-picker">
      <legend>Preguntas candidatas</legend>
      <div className="assessment-candidate-picker__toolbar">
        <label>
          <Search aria-hidden="true" />
          <Input
            aria-label="Buscar pregunta candidata"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Código, banco o contenido…"
            value={query}
          />
        </label>
        <select
          aria-label="Filtrar por tipo de pregunta"
          className="academic-control"
          onChange={(event) => setType(event.target.value)}
          value={type}
        >
          <option value="all">Todos los tipos</option>
          {types.map((candidateType) => (
            <option key={candidateType} value={candidateType}>
              {questionTypeLabel(candidateType)}
            </option>
          ))}
        </select>
        <span>{candidateIds.length} seleccionadas</span>
      </div>
      <div className="assessment-candidate-picker__list">
        {visibleQuestions.map((question) => {
          const checked = candidateIds.includes(question.id);
          const excerpt = publicQuestionExcerpt(question.public);
          return (
            <label data-selected={checked} key={question.id}>
              <input
                checked={checked}
                disabled={lockedIds.includes(question.id)}
                onChange={(event) =>
                  onChange(
                    event.target.checked
                      ? [...candidateIds, question.id]
                      : candidateIds.filter((id) => id !== question.id),
                  )
                }
                type="checkbox"
              />
              <span className="min-w-0">
                <strong>{question.code}</strong>
                <span>
                  {questionTypeLabel(question.type)} · {question.bankName} · v
                  {question.number}
                </span>
                {excerpt ? <small>{excerpt}</small> : null}
              </span>
            </label>
          );
        })}
        {!visibleQuestions.length ? (
          <p>No hay preguntas aprobadas que coincidan con el filtro.</p>
        ) : null}
      </div>
    </fieldset>
  );
}

function publicQuestionExcerpt(value: unknown) {
  const root =
    value && typeof value === 'object'
      ? (value as Record<string, unknown>)
      : {};
  const prompt = root.prompt;
  const pieces: string[] = [];
  const stack: unknown[] = [prompt];
  while (stack.length && pieces.join(' ').length < 220) {
    const current = stack.pop();
    if (!current || typeof current !== 'object' || Array.isArray(current))
      continue;
    const node = current as Record<string, unknown>;
    if (typeof node.text === 'string') pieces.push(node.text);
    if (node.attrs && typeof node.attrs === 'object') {
      const attrs = node.attrs as Record<string, unknown>;
      if (typeof attrs.latex === 'string') pieces.push(attrs.latex);
      if (typeof attrs.altText === 'string') pieces.push(attrs.altText);
    }
    if (Array.isArray(node.content)) stack.push(...node.content.toReversed());
  }
  const text = pieces.join(' ').replace(/\s+/g, ' ').trim();
  return text.length > 180 ? `${text.slice(0, 177)}…` : text;
}

function revisionStatusLabel(status: string) {
  const labels: Record<string, string> = {
    approved: 'Aprobada',
    changes_requested: 'Cambios solicitados',
    draft: 'Borrador',
    in_review: 'En revisión',
  };
  return labels[status] ?? status;
}

function readinessIssueLabel(issue: string) {
  const [code] = issue.split(':');
  const labels: Record<string, string> = {
    assessment_objectives_required:
      'Vincula al menos un objetivo de aprendizaje.',
    item_objectives_outside_assessment:
      'Un ítem usa objetivos que no pertenecen a la evaluación.',
    item_objectives_required: 'Cada ítem debe evidenciar al menos un objetivo.',
    question_version_repeated:
      'Una versión de pregunta está repetida en la composición.',
    section_empty: 'Cada sección debe incluir al menos una pregunta.',
    section_required: 'Añade al menos una sección al instrumento.',
    title_required: 'Completa el título de la evaluación.',
  };
  return labels[code ?? ''] ?? 'Revisa la composición antes de continuar.';
}

function AssessmentItemForm({
  lockVersion,
  objectives,
  path,
  questions,
}: Readonly<{
  lockVersion: number;
  objectives: LearningObjective[];
  path: {
    assessmentSlug: string;
    revisionId: string;
    sectionId: string;
    slug: string;
  };
  questions: QuestionOption[];
}>) {
  const router = useRouter();
  const bankNames = [
    ...new Set(questions.map((question) => question.bankName)),
  ].sort((left, right) => left.localeCompare(right, 'es'));
  const [bankName, setBankName] = useState(
    bankNames.length === 1 ? (bankNames[0] ?? '') : '',
  );
  const [questionQuery, setQuestionQuery] = useState('');
  const [questionVersionId, setQuestionVersionId] = useState('');
  const [points, setPoints] = useState('1.000');
  const [objectiveIds, setObjectiveIds] = useState<string[]>([]);
  const mutation = useAssessmentMutation(() =>
    addAssessmentItem(path, {
      expected_version: lockVersion,
      objective_ids: objectiveIds,
      points,
      question_version_id: questionVersionId,
      required: true,
    }),
  );
  const normalizedQuestionQuery = questionQuery.trim().toLocaleLowerCase();
  const visibleQuestions = questions.filter(
    (question) =>
      question.bankName === bankName &&
      (!normalizedQuestionQuery ||
        question.code.toLocaleLowerCase().includes(normalizedQuestionQuery)),
  );
  return (
    <div className="mt-4 grid gap-3 border-t pt-4 sm:grid-cols-[minmax(0,.75fr)_minmax(0,.75fr)_minmax(0,1.25fr)_7rem]">
      <Label className="sr-only" htmlFor={`bank-${path.sectionId}`}>
        Banco de preguntas
      </Label>
      <select
        className="h-9 min-w-0 border bg-background px-3 text-sm"
        id={`bank-${path.sectionId}`}
        onChange={(event) => {
          setBankName(event.target.value);
          setQuestionVersionId('');
        }}
        value={bankName}
      >
        <option value="">Selecciona un banco</option>
        {bankNames.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
      <Label className="sr-only" htmlFor={`question-search-${path.sectionId}`}>
        Buscar pregunta por código
      </Label>
      <Input
        id={`question-search-${path.sectionId}`}
        onChange={(event) => setQuestionQuery(event.target.value)}
        placeholder="Buscar código"
        value={questionQuery}
      />
      <Label className="sr-only" htmlFor={`question-${path.sectionId}`}>
        Pregunta aprobada
      </Label>
      <select
        className="h-9 min-w-0 border bg-background px-3 text-sm"
        id={`question-${path.sectionId}`}
        onChange={(event) => setQuestionVersionId(event.target.value)}
        value={questionVersionId}
      >
        <option value="">
          {bankName
            ? 'Selecciona una pregunta aprobada'
            : 'Primero selecciona un banco'}
        </option>
        {visibleQuestions.map((question) => (
          <option key={question.id} value={question.id}>
            {question.code} · v{question.number}
          </option>
        ))}
      </select>
      <Label className="sr-only" htmlFor={`points-${path.sectionId}`}>
        Puntos
      </Label>
      <Input
        id={`points-${path.sectionId}`}
        min="0.001"
        onChange={(event) => setPoints(event.target.value)}
        step="0.001"
        type="number"
        value={points}
      />
      <fieldset className="sm:col-span-4">
        <legend className="text-xs font-semibold text-muted-foreground">
          Objetivos del ítem
        </legend>
        <div className="mt-2 flex flex-wrap gap-3">
          {objectives.map((objective) => (
            <label
              className="flex items-center gap-2 text-xs"
              key={objective.id}
            >
              <input
                checked={objectiveIds.includes(objective.id)}
                onChange={(event) =>
                  setObjectiveIds((current) =>
                    event.target.checked
                      ? [...current, objective.id]
                      : current.filter((id) => id !== objective.id),
                  )
                }
                type="checkbox"
              />
              {objective.code}
            </label>
          ))}
        </div>
      </fieldset>
      <Button
        className="sm:col-start-4"
        disabled={
          !questionVersionId || !objectiveIds.length || mutation.isPending
        }
        onClick={async () => {
          try {
            await mutation.mutateAsync(undefined);
            setQuestionVersionId('');
            setPoints('1.000');
            setObjectiveIds([]);
            router.refresh();
          } catch {
            // React Query mantiene el error en el formulario.
          }
        }}
        type="button"
        variant="outline"
      >
        Añadir
      </Button>
      <div className="sm:col-span-4">
        <MutationError error={mutation.error} />
      </div>
    </div>
  );
}

function AssessmentItemRow({
  editable,
  index,
  item,
  items,
  length,
  lockVersion,
  objectives,
  path,
}: Readonly<{
  editable: boolean;
  index: number;
  item: OutlineItem;
  items: OutlineItem[];
  length: number;
  lockVersion: number;
  objectives: LearningObjective[];
  path: {
    assessmentSlug: string;
    revisionId: string;
    sectionId: string;
    slug: string;
  };
}>) {
  const router = useRouter();
  const [points, setPoints] = useState(item.points);
  const [required, setRequired] = useState(item.required);
  const [objectiveIds, setObjectiveIds] = useState(item.objective_ids);
  const order = useAssessmentMutation((ids: string[]) =>
    reorderAssessmentItems(path, {
      expected_version: lockVersion,
      ids,
    }),
  );
  const update = useAssessmentMutation(() =>
    updateAssessmentItem(
      { ...path, itemId: item.id },
      {
        expected_version: lockVersion,
        objective_ids: objectiveIds,
        points,
        required,
      },
    ),
  );
  return (
    <li className="py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{item.question_code}</span>
        <Badge variant="outline">{questionTypeLabel(item.question_type)}</Badge>
        <span className="ml-auto">{item.points} puntos</span>
        {editable ? (
          <OrderButtons
            disabled={order.isPending}
            index={index}
            label="pregunta"
            length={length}
            onMove={async (direction) => {
              try {
                await order.mutateAsync(movedIds(items, index, direction));
                router.refresh();
              } catch {
                // React Query mantiene el error en el ítem.
              }
            }}
          />
        ) : null}
      </div>
      {editable ? (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs font-medium text-primary">
            Editar puntos y objetivos
          </summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-[8rem_minmax(0,1fr)_auto]">
            <Label htmlFor={`item-points-${item.id}`}>Puntos</Label>
            <Input
              id={`item-points-${item.id}`}
              min="0.001"
              onChange={(event) => setPoints(event.target.value)}
              step="0.001"
              type="number"
              value={points}
            />
            <label className="flex items-center gap-2 text-xs">
              <input
                checked={required}
                onChange={(event) => setRequired(event.target.checked)}
                type="checkbox"
              />
              Obligatoria
            </label>
            <fieldset className="sm:col-span-3">
              <legend className="text-xs font-semibold">
                Objetivos alineados
              </legend>
              <div className="mt-2 flex flex-wrap gap-3">
                {objectives.map((objective) => (
                  <label
                    className="flex items-center gap-2 text-xs"
                    key={objective.id}
                  >
                    <input
                      checked={objectiveIds.includes(objective.id)}
                      onChange={(event) =>
                        setObjectiveIds((current) =>
                          event.target.checked
                            ? [...current, objective.id]
                            : current.filter((id) => id !== objective.id),
                        )
                      }
                      type="checkbox"
                    />
                    {objective.code}
                  </label>
                ))}
              </div>
            </fieldset>
            <Button
              className="sm:col-start-3"
              disabled={!objectiveIds.length || update.isPending}
              onClick={async () => {
                try {
                  await update.mutateAsync(undefined);
                  router.refresh();
                } catch {
                  // React Query mantiene el error en el ítem.
                }
              }}
              size="sm"
              type="button"
              variant="outline"
            >
              Guardar ítem
            </Button>
            <div className="sm:col-span-3">
              <MutationError error={order.error ?? update.error} />
            </div>
          </div>
        </details>
      ) : null}
    </li>
  );
}

function OrderButtons({
  disabled,
  index,
  label,
  length,
  onMove,
}: Readonly<{
  disabled: boolean;
  index: number;
  label: string;
  length: number;
  onMove: (direction: -1 | 1) => void | Promise<void>;
}>) {
  return (
    <span className="flex gap-1">
      <Button
        aria-label={`Subir ${label}`}
        disabled={disabled || index === 0}
        onClick={() => onMove(-1)}
        size="sm"
        type="button"
        variant="ghost"
      >
        Subir
      </Button>
      <Button
        aria-label={`Bajar ${label}`}
        disabled={disabled || index === length - 1}
        onClick={() => onMove(1)}
        size="sm"
        type="button"
        variant="ghost"
      >
        Bajar
      </Button>
    </span>
  );
}

function questionTypeLabel(type: string) {
  return (
    {
      long_text: 'Respuesta extensa',
      matching: 'Emparejamiento',
      mathematical_expression: 'Expresión matemática',
      multiple_choice: 'Selección múltiple',
      numeric: 'Respuesta numérica',
      ordering: 'Ordenamiento',
      short_text: 'Respuesta corta',
      single_choice: 'Selección única',
      true_false: 'Verdadero o falso',
    }[type] ?? type
  );
}

function movedIds<T extends { id: string }>(
  values: T[],
  index: number,
  direction: -1 | 1,
) {
  const target = index + direction;
  if (target < 0 || target >= values.length) {
    return values.map((value) => value.id);
  }
  const reordered = [...values];
  const current = reordered[index];
  const replacement = reordered[target];
  if (current === undefined || replacement === undefined) {
    return values.map((value) => value.id);
  }
  reordered[index] = replacement;
  reordered[target] = current;
  return reordered.map((value) => value.id);
}
