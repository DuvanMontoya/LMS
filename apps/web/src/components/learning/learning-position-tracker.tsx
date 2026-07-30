'use client';

import { useEffect, useRef } from 'react';

import { flushLearningPosition } from '@/lib/learning/api';
import { useUpdatePosition } from '@/lib/learning/hooks';

const NODE_FRAGMENT = /^#node-([0-9a-f-]{36})$/;
const SAVE_DELAY_MS = 5_000;

export function LearningPositionTracker({
  enrollmentId,
  slug,
  unitId,
}: Readonly<{ enrollmentId: string; slug: string; unitId: string }>) {
  const { mutate } = useUpdatePosition({ enrollmentId, slug });
  const latestNodeRef = useRef<string | undefined>(undefined);
  const savedNodeRef = useRef<string | undefined>(undefined);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    const match = window.location.hash.match(NODE_FRAGMENT);
    if (!match) return;
    const target = document.getElementById(`node-${match[1]}`);
    if (!target) return;
    const reducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches;
    target.scrollIntoView({
      behavior: reducedMotion ? 'auto' : 'smooth',
      block: 'start',
    });
    target.focus({ preventScroll: true });
  }, []);

  useEffect(() => {
    const nodes = Array.from(
      document.querySelectorAll<HTMLElement>('[data-node-id]'),
    ).filter((node) => !node.matches('input, textarea, select, button'));
    if (!nodes.length) return;

    function saveLatest() {
      const nodeId = latestNodeRef.current;
      if (!nodeId || nodeId === savedNodeRef.current) return;
      savedNodeRef.current = nodeId;
      mutate(
        { nodeId, unitId },
        {
          onError: () => {
            savedNodeRef.current = undefined;
          },
        },
      );
    }

    function schedule(nodeId: string) {
      if (nodeId === latestNodeRef.current) return;
      latestNodeRef.current = nodeId;
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(saveLatest, SAVE_DELAY_MS);
    }

    const visible = new Map<Element, number>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.35) {
            visible.set(entry.target, entry.intersectionRatio);
          } else {
            visible.delete(entry.target);
          }
        }
        const candidate = nodes.findLast((node) => visible.has(node));
        const nodeId = candidate?.dataset.nodeId;
        if (nodeId) schedule(nodeId);
      },
      { threshold: [0.35, 0.6] },
    );
    nodes.forEach((node) => observer.observe(node));

    function beforeNavigation(event: MouseEvent) {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const anchor = target.closest('a[href]');
      if (anchor) saveLatest();
    }

    function pageHide() {
      const nodeId = latestNodeRef.current;
      if (!nodeId || nodeId === savedNodeRef.current) return;
      void flushLearningPosition(
        { enrollmentId, slug },
        { node_id: nodeId, unit_id: unitId },
      );
    }

    document.addEventListener('click', beforeNavigation, true);
    window.addEventListener('pagehide', pageHide);
    return () => {
      observer.disconnect();
      document.removeEventListener('click', beforeNavigation, true);
      window.removeEventListener('pagehide', pageHide);
      if (timerRef.current) clearTimeout(timerRef.current);
      saveLatest();
    };
  }, [enrollmentId, mutate, slug, unitId]);

  return null;
}
