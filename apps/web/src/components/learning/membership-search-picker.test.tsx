import { act, fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { platformBrowserClient } from '@/lib/api/platform-browser-client';

import {
  MembershipSearchPicker,
  type MembershipOption,
} from './membership-search-picker';

vi.mock('@/lib/api/platform-browser-client', () => ({
  platformBrowserClient: { GET: vi.fn() },
}));

const getMock = vi.mocked(platformBrowserClient.GET);

function response(
  membershipId: string,
  email: string,
  pagination: { next: string | null; previous: string | null },
) {
  return Promise.resolve({
    data: {
      count: 2,
      next: pagination.next,
      previous: pagination.previous,
      results: [
        {
          membership_id: membershipId,
          user: { email },
        },
      ],
    },
    response: { ok: true },
  } as never);
}

function Harness() {
  const [selected, setSelected] = useState<MembershipOption[]>([]);
  return (
    <>
      <MembershipSearchPicker
        ariaLabel="Buscar persona"
        excludeIds={selected.map((member) => member.id)}
        onSelect={(member) => setSelected((current) => [...current, member])}
        slug="institucion"
      />
      <output aria-label="Selección persistente">
        {selected.map((member) => member.email).join(', ')}
      </output>
    </>
  );
}

describe('MembershipSearchPicker', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('uses remote pagination and preserves selected memberships between pages', async () => {
    vi.useFakeTimers();
    getMock
      .mockImplementationOnce(() =>
        response('membership-1', 'ana@example.test', {
          next: 'page-2',
          previous: null,
        }),
      )
      .mockImplementationOnce(() =>
        response('membership-2', 'bruno@example.test', {
          next: null,
          previous: 'page-1',
        }),
      );
    render(<Harness />);

    fireEvent.change(
      screen.getByRole('searchbox', { name: 'Buscar persona' }),
      {
        target: { value: 'an' },
      },
    );
    await act(async () => vi.advanceTimersByTimeAsync(300));
    expect(screen.getByText('ana@example.test')).toBeInTheDocument();
    expect(getMock).toHaveBeenLastCalledWith(
      '/api/v1/organizations/{slug}/memberships/',
      expect.objectContaining({
        params: expect.objectContaining({
          query: expect.objectContaining({ page: 1, page_size: 10, q: 'an' }),
        }),
      }),
    );

    fireEvent.click(screen.getByRole('button', { name: 'Añadir' }));
    expect(screen.getByLabelText('Selección persistente')).toHaveTextContent(
      'ana@example.test',
    );
    expect(screen.getByRole('button', { name: 'Seleccionada' })).toBeDisabled();

    fireEvent.click(
      screen.getByRole('button', { name: 'Página siguiente de personas' }),
    );
    await act(async () => vi.advanceTimersByTimeAsync(300));
    expect(screen.getByText('bruno@example.test')).toBeInTheDocument();
    expect(screen.getByLabelText('Selección persistente')).toHaveTextContent(
      'ana@example.test',
    );
    expect(getMock).toHaveBeenLastCalledWith(
      '/api/v1/organizations/{slug}/memberships/',
      expect.objectContaining({
        params: expect.objectContaining({
          query: expect.objectContaining({ page: 2, page_size: 10, q: 'an' }),
        }),
      }),
    );
  });
});
