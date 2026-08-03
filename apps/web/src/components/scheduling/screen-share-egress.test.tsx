import { fireEvent, render, screen } from '@testing-library/react';
import { ConnectionState, Track, type Room } from 'livekit-client';
import type { ReactNode, VideoHTMLAttributes } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

type MockTrackReference = {
  participant: { identity: string };
  publication: { trackSid: string };
  source: Track.Source;
};

let visibleTracks: MockTrackReference[] = [];

vi.mock('@livekit/components-react', () => ({
  RoomAudioRenderer: () => <div data-testid="room-audio" />,
  RoomContext: {
    Provider: ({ children }: Readonly<{ children: ReactNode }>) => children,
  },
  VideoTrack: ({
    trackRef,
    ...props
  }: VideoHTMLAttributes<HTMLVideoElement> & {
    trackRef: unknown;
  }) => (
    <video
      data-testid="screen-video"
      data-track={String(Boolean(trackRef))}
      {...props}
    />
  ),
  isTrackReference: (value: unknown) =>
    Boolean(
      value &&
      typeof value === 'object' &&
      'publication' in value &&
      value.publication,
    ),
  useTracks: () => visibleTracks,
}));

import { ScreenShareRecordingSurface } from './screen-share-egress';

function screenTrack(): MockTrackReference {
  return {
    participant: { identity: 'presenter' },
    publication: { trackSid: 'TR_screen' },
    source: Track.Source.ScreenShare,
  };
}

describe('ScreenShareRecordingSurface', () => {
  beforeEach(() => {
    visibleTracks = [];
  });

  it('signals recording only after the screen video is playing and ends when it disappears', () => {
    const onPlaying = vi.fn();
    const onEnded = vi.fn();
    const room = { state: ConnectionState.Connected } as Room;
    const view = render(
      <ScreenShareRecordingSurface
        onEnded={onEnded}
        onPlaying={onPlaying}
        room={room}
      />,
    );

    expect(
      screen.getByText('Esperando una pantalla compartida…'),
    ).toBeVisible();
    expect(onPlaying).not.toHaveBeenCalled();

    visibleTracks = [screenTrack()];
    view.rerender(
      <ScreenShareRecordingSurface
        onEnded={onEnded}
        onPlaying={onPlaying}
        room={room}
      />,
    );
    fireEvent.playing(screen.getByTestId('screen-video'));
    expect(onPlaying).toHaveBeenCalledOnce();

    visibleTracks = [];
    view.rerender(
      <ScreenShareRecordingSurface
        onEnded={onEnded}
        onPlaying={onPlaying}
        room={room}
      />,
    );
    expect(onEnded).toHaveBeenCalledOnce();
  });
});
