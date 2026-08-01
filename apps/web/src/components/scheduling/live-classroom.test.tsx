import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { LiveSessionDetail } from '@/lib/scheduling/server';

import { LiveClassroom } from './live-classroom';

const enterLiveSession = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock('@/lib/scheduling/api', () => ({
  endLiveSession: vi.fn(),
  enterLiveSession: (...args: unknown[]) => enterLiveSession(...args),
}));

const detail: LiveSessionDetail = {
  attendanceThresholdMinutes: null,
  canDelete: false,
  canEdit: false,
  canJoin: true,
  canModerate: false,
  canShareScreen: false,
  canStart: false,
  countsTowardProgress: false,
  course: { slug: 'algebra' },
  description: 'Sesión de práctica',
  hostName: 'Participante 00000000',
  id: '00000000-0000-0000-0000-000000000001',
  liveStatus: 'live',
  scheduledEnd: '2026-08-01T16:00:00Z',
  scheduledStart: '2026-08-01T15:00:00Z',
  sessionId: '00000000-0000-0000-0000-000000000001',
  status: 'live',
  title: 'Álgebra en vivo',
};

describe('LiveClassroom lobby', () => {
  it('does not request a token until the learner explicitly enters', async () => {
    enterLiveSession.mockRejectedValueOnce(
      new Error('Proveedor no disponible'),
    );
    render(<LiveClassroom detail={detail} slug="institucion" />);
    expect(enterLiveSession).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /entrar a clase/i }));
    await waitFor(() =>
      expect(enterLiveSession).toHaveBeenCalledWith(
        'institucion',
        detail.id,
        'join',
      ),
    );
    expect(screen.getByText('Proveedor no disponible')).toBeInTheDocument();
  });
});
