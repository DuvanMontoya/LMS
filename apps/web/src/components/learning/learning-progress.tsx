import type { components } from '@/lib/api/generated/platform';
import { percentLabel, progressStatusLabel } from '@/lib/learning/labels';

export function LearningProgress({
  progress,
}: Readonly<{ progress: components['schemas']['Progress'] }>) {
  const completedActivities =
    progress.completed_units + progress.completed_required_activities;
  const totalActivities =
    progress.total_units + progress.total_required_activities;
  const noun = progress.total_required_activities ? 'actividades' : 'unidades';
  const description = `${completedActivities} de ${totalActivities} ${noun} completadas, ${percentLabel(progress.percent_basis_points)} %`;
  const compactDescription = `${completedActivities}/${totalActivities} ${noun} · ${percentLabel(progress.percent_basis_points)} %`;
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
        max={totalActivities}
        value={completedActivities}
      >
        {progress.percent_basis_points / 100} %
      </progress>
    </div>
  );
}
