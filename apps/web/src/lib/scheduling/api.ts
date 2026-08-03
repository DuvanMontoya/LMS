'use client';

import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

export type CalendarEvent = components['schemas']['CalendarEvent'];
export type EventCreate = components['schemas']['EventCreate'];
export type LiveConnection = components['schemas']['LiveConnection'];

export class SchedulingApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function required<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await request;
  if (response.ok && data !== undefined) return data;
  const payload =
    error && typeof error === 'object'
      ? (error as Record<string, unknown>)
      : {};
  throw new SchedulingApiError(
    typeof payload.detail === 'string'
      ? payload.detail
      : 'No fue posible completar la operación de agenda.',
    typeof payload.code === 'string' ? payload.code : 'scheduling_invalid',
    response.status,
  );
}

export function getCalendarEvents(
  slug: string,
  range: { start: string; end: string; timeZone: string },
  signal?: AbortSignal,
) {
  return required(
    platformBrowserClient.GET(
      '/api/v1/organizations/{slug}/scheduling/calendar/events/',
      {
        params: { path: { slug }, query: range },
        ...(signal ? { signal } : {}),
      },
    ),
  );
}

export function createCalendarEvent(slug: string, body: EventCreate) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/scheduling/calendar/events/',
      { body, params: { path: { slug } } },
    ),
  );
}

export function rescheduleCalendarEvent(
  slug: string,
  occurrenceId: string,
  body: components['schemas']['EventReschedule'],
) {
  return required(
    platformBrowserClient.PATCH(
      '/api/v1/organizations/{slug}/scheduling/events/{occurrence_id}/',
      { body, params: { path: { slug, occurrence_id: occurrenceId } } },
    ),
  );
}

export function cancelCalendarEvent(
  slug: string,
  occurrenceId: string,
  body: components['schemas']['EventCancel'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/scheduling/events/{occurrence_id}/cancel/',
      { body, params: { path: { slug, occurrence_id: occurrenceId } } },
    ),
  );
}

function liveAction(
  slug: string,
  sessionId: string,
  action: 'join' | 'start',
  recordingAcknowledged: boolean,
): Promise<LiveConnection> {
  const path =
    action === 'start'
      ? '/api/v1/organizations/{slug}/scheduling/live-sessions/{session_id}/start/'
      : '/api/v1/organizations/{slug}/scheduling/live-sessions/{session_id}/join/';
  return required(
    platformBrowserClient.POST(path, {
      body: { recording_acknowledged: recordingAcknowledged },
      params: { path: { slug, session_id: sessionId } },
    }),
  ) as Promise<LiveConnection>;
}

export function enterLiveSession(
  slug: string,
  sessionId: string,
  action: 'join' | 'start',
  recordingAcknowledged = false,
) {
  return liveAction(slug, sessionId, action, recordingAcknowledged);
}

export function endLiveSession(slug: string, sessionId: string) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/scheduling/live-sessions/{session_id}/end/',
      { params: { path: { slug, session_id: sessionId } } },
    ),
  );
}

export function startLiveRecording(
  slug: string,
  sessionId: string,
  recordingLayout: 'grid' | 'screen_share' | 'speaker',
  recordingResolution: '720p' | '1080p',
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/scheduling/live-sessions/{session_id}/recording/start/',
      {
        params: { path: { slug, session_id: sessionId } },
        body: {
          recording_layout: recordingLayout,
          recording_resolution: recordingResolution,
        },
      },
    ),
  );
}

export function stopLiveRecording(slug: string, sessionId: string) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/scheduling/live-sessions/{session_id}/recording/stop/',
      { params: { path: { slug, session_id: sessionId } } },
    ),
  );
}

export function changeParticipantPermissions(
  slug: string,
  sessionId: string,
  identity: string,
  body: components['schemas']['ParticipantPermission'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/scheduling/live-sessions/{session_id}/participants/{identity}/permissions/',
      { body, params: { path: { slug, session_id: sessionId, identity } } },
    ),
  );
}

export function removeParticipant(
  slug: string,
  sessionId: string,
  identity: string,
) {
  return required(
    platformBrowserClient.DELETE(
      '/api/v1/organizations/{slug}/scheduling/live-sessions/{session_id}/participants/{identity}/',
      { params: { path: { slug, session_id: sessionId, identity } } },
    ),
  );
}
