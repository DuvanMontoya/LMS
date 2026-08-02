'use client';

import { useSyncExternalStore } from 'react';

const subscribe = () => () => {};

/**
 * Keeps controlled fields inert until React owns the hydrated DOM. This avoids
 * losing text typed into server-rendered inputs before their event handlers
 * are attached.
 */
export function useHydrated() {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
