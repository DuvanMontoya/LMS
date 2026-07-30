import type { components } from '@/lib/api/generated/platform';
import { percentLabel, progressStatusLabel } from '@/lib/learning/labels';

export function LearningProgress({
  progress,
}: Readonly<{ progress: components['schemas']['Progress'] }>) {
  const description = `${progress.completed_units} de ${progress.total_units} unidades completadas, ${percentLabel(progress.percent_basis_points)} %`;
  const compactDescription = `${progress.completed_units}/${progress.total_units} unidades · ${percentLabel(progress.percent_basis_points)} %`;
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
        max={progress.total_units}
        value={progress.completed_units}
      >
        {progress.percent_basis_points / 100} %
      </progress>
    </div>
  );
}
