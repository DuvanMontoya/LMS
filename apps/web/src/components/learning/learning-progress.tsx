import type { components } from '@/lib/api/generated/platform';
import { percentLabel, progressStatusLabel } from '@/lib/learning/labels';

export function learningProgressSummary(
  progress: components['schemas']['Progress'],
) {
  const hasActivityProgress = progress.completion.total_required > 0;
  return {
    completed: hasActivityProgress
      ? progress.completion.completed_required
      : progress.completed_units,
    noun: hasActivityProgress ? 'actividades obligatorias' : 'lecciones',
    total: hasActivityProgress
      ? progress.completion.total_required
      : progress.total_units,
  };
}

export function LearningProgress({
  progress,
}: Readonly<{ progress: components['schemas']['Progress'] }>) {
  const { completed, noun, total } = learningProgressSummary(progress);
  const description = `${completed} de ${total} ${noun} completadas, ${percentLabel(progress.percent_basis_points)} %`;
  const compactDescription = `${completed}/${total} ${noun} · ${percentLabel(progress.percent_basis_points)} %`;
  return (
    <div>
      <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between sm:gap-3">
        <span className="text-sm font-medium">
          {progressStatusLabel(progress.status)}
        </span>
        <span className="text-xs leading-5 whitespace-nowrap text-muted-foreground tabular-nums">
          {compactDescription}
        </span>
      </div>
      <progress
        aria-label={description}
        className="mt-2 block h-2 w-full overflow-hidden rounded-full accent-primary"
        max={Math.max(1, total)}
        value={completed}
      >
        {progress.percent_basis_points / 100} %
      </progress>
    </div>
  );
}
