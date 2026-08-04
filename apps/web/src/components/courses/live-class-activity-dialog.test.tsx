import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { LiveClassActivityDialog } from './live-class-activity-dialog';

describe('LiveClassActivityDialog', () => {
  it('submits the selected learning objectives with the live-class form', async () => {
    const onSubmit = vi.fn().mockResolvedValue(true);

    render(
      <LiveClassActivityDialog
        isSaving={false}
        objectives={[
          {
            code: 'OBJ-001',
            id: 'objective-one',
            statement: 'Interpretar funciones y sus representaciones.',
            status: 'active',
            subject_id: 'subject-one',
          },
        ]}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Clase en vivoSala LiveKit, participación y asistencia',
      }),
    );
    fireEvent.click(
      screen.getByRole('checkbox', {
        name: 'OBJ-001: Interpretar funciones y sus representaciones.',
      }),
    );
    const dialog = screen.getByRole('dialog');
    const form = dialog.querySelector('form');
    expect(form).not.toBeNull();
    fireEvent.submit(form!);

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const submitted = onSubmit.mock.calls[0]?.[0] as FormData;
    expect(submitted.getAll('live-objective')).toEqual(['objective-one']);
  });
});
