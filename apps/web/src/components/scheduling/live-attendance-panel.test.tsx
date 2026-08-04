import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getLiveAttendance } from '@/lib/scheduling/api';

import { LiveAttendancePanel } from './live-attendance-panel';

vi.mock('@/lib/scheduling/api', () => ({ getLiveAttendance: vi.fn() }));

describe('LiveAttendancePanel', () => {
  beforeEach(() => vi.mocked(getLiveAttendance).mockReset());

  it('shows consolidated duration and the configured threshold', async () => {
    vi.mocked(getLiveAttendance).mockResolvedValue([
      {
        display_name: 'Laura Estudiante',
        duration_seconds: 2_910,
        participant_identity: 'student:laura@example.test',
        role: 'student',
        user_id: '694dcff0-f63b-4c17-8969-a9159c3a1049',
      },
      {
        display_name: 'Diana Docente',
        duration_seconds: 3_000,
        participant_identity: 'host:docente@example.test',
        role: 'host',
        user_id: '444dcff0-f63b-4c17-8969-a9159c3a1049',
      },
    ]);
    render(
      <LiveAttendancePanel
        sessionId="session-id"
        sessionStatus="ended"
        slug="institucion"
        thresholdMinutes={48}
      />,
    );

    expect(await screen.findByText('Laura Estudiante')).toBeInTheDocument();
    expect(screen.getByText('48 min 30 s')).toBeInTheDocument();
    expect(screen.getByText('Mínimo cumplido')).toBeInTheDocument();
    expect(screen.queryByText('Diana Docente')).not.toBeInTheDocument();
  });

  it('identifies an open segment without inventing a final duration', async () => {
    vi.mocked(getLiveAttendance).mockResolvedValue([
      {
        display_name: '',
        duration_seconds: null,
        participant_identity: 'student:laura@example.test',
        role: 'student',
        user_id: null,
      },
    ]);
    render(
      <LiveAttendancePanel
        sessionId="session-id"
        sessionStatus="live"
        slug="institucion"
        thresholdMinutes={48}
      />,
    );

    expect(await screen.findByText('En sala')).toBeInTheDocument();
    expect(screen.getByText('Se consolidará al salir')).toBeInTheDocument();
    await waitFor(() => expect(getLiveAttendance).toHaveBeenCalledTimes(1));
  });
});
