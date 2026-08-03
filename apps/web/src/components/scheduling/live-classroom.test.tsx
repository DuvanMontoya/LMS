import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { LiveSessionDetail } from '@/lib/scheduling/server';

import {
  LiveClassroom,
  RecordingControl,
  reconcileRecordingStatus,
} from './live-classroom';

const enterLiveSession = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock('@/lib/scheduling/api', () => ({
  endLiveSession: vi.fn(),
  enterLiveSession: (...args: unknown[]) => enterLiveSession(...args),
  changeParticipantPermissions: vi.fn(),
  muteParticipantAudio: vi.fn(),
  removeParticipant: vi.fn(),
  startLiveRecording: vi.fn(),
  stopLiveRecording: vi.fn(),
}));

const detail: LiveSessionDetail = {
  activity_required: false,
  attendanceThresholdMinutes: null,
  canDelete: false,
  canEdit: false,
  canJoin: true,
  canModerate: false,
  canPublishAudio: true,
  canPublishVideo: true,
  canShareScreen: false,
  canStart: false,
  countsTowardProgress: false,
  course: { slug: 'algebra' },
  course_group_id: null,
  course_group_activity_id: null,
  course_group_name: null,
  description: 'Sesión de práctica',
  hostName: 'Docente Demo',
  chatEnabled: true,
  id: '00000000-0000-0000-0000-000000000001',
  liveStatus: 'live',
  recordingLayout: 'speaker',
  recordingMode: 'off',
  recordingResolution: '1080p',
  recordingStatus: 'disabled',
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
    expect(screen.getByText('Álgebra en vivo')).toBeInTheDocument();
    expect(screen.getByText('1 h')).toBeInTheDocument();
    expect(screen.getByText('Docente Demo')).toBeInTheDocument();
    expect(
      screen.getByText(/cámara, micrófono y pantalla se activan/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /probar dispositivos/i }),
    ).not.toBeInTheDocument();
    expect(
      document.querySelector('[data-state="briefing"]'),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /entrar a clase/i }));
    await waitFor(() =>
      expect(enterLiveSession).toHaveBeenCalledWith(
        'institucion',
        detail.id,
        'join',
        false,
      ),
    );
    expect(screen.getByText('Proveedor no disponible')).toBeInTheDocument();
  });
});

describe('RecordingControl', () => {
  it('requires an explicit composition and resolution before starting', async () => {
    const onStart = vi.fn().mockResolvedValue(true);
    render(
      <RecordingControl
        busy={false}
        hasCamera
        hasScreenShare={false}
        layout="screen_share"
        onLayoutChange={vi.fn()}
        onResolutionChange={vi.fn()}
        onStart={onStart}
        onStop={vi.fn()}
        resolution="1080p"
        status="idle"
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Grabar' }));
    expect(
      screen.getByRole('radio', { name: /pantalla compartida sola/i }),
    ).toBeDisabled();
    expect(
      screen.getByRole('radio', { name: /mosaico de participantes/i }),
    ).toBeChecked();
    fireEvent.click(screen.getByRole('radio', { name: /720p/i }));
    fireEvent.click(
      screen.getByRole('button', { name: 'Iniciar grabación' }),
    );
    await waitFor(() => expect(onStart).toHaveBeenCalledWith('grid', '720p'));
  });

  it('offers screen-only recording only while a screen is being shared', async () => {
    const onStart = vi.fn().mockResolvedValue(true);
    render(
      <RecordingControl
        busy={false}
        hasCamera={false}
        hasScreenShare
        layout="grid"
        onLayoutChange={vi.fn()}
        onResolutionChange={vi.fn()}
        onStart={onStart}
        onStop={vi.fn()}
        resolution="1080p"
        status="idle"
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Grabar' }));
    fireEvent.click(
      screen.getByRole('radio', { name: /pantalla compartida sola/i }),
    );
    fireEvent.click(
      screen.getByRole('button', { name: 'Iniciar grabación' }),
    );
    await waitFor(() =>
      expect(onStart).toHaveBeenCalledWith('screen_share', '1080p'),
    );
  });
});

describe('reconcileRecordingStatus', () => {
  it('keeps a requested recording in starting until LiveKit confirms it', () => {
    expect(reconcileRecordingStatus('starting', false, false)).toEqual({
      observed: false,
      status: 'starting',
    });
    expect(reconcileRecordingStatus('starting', true, false)).toEqual({
      observed: true,
      status: 'active',
    });
  });

  it('ends only after an observed provider recording disappears', () => {
    expect(reconcileRecordingStatus('active', false, true)).toEqual({
      observed: false,
      status: 'ended',
    });
  });
});
