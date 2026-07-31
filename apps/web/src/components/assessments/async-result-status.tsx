'use client';

import { useQuery } from '@tanstack/react-query';
import { LoaderCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useRef } from 'react';

import { getAssessmentResultBrowser } from '@/lib/assessments/api';

export function AsyncResultStatus({
  attemptId,
  slug,
}: Readonly<{ attemptId: string; slug: string }>) {
  const router = useRouter();
  const polls = useRef(0);
  const query = useQuery({
    queryFn: () => getAssessmentResultBrowser(slug, attemptId),
    queryKey: ['assessment-result', slug, attemptId],
    refetchInterval: (state) => {
      const result = state.state.data;
      if (result?.status !== 'grading_pending' || polls.current >= 30)
        return false;
      polls.current += 1;
      return 2000;
    },
    refetchIntervalInBackground: false,
    retry: false,
  });

  useEffect(() => {
    if (query.data && query.data.status !== 'grading_pending') {
      router.refresh();
    }
  }, [query.data, router]);

  return (
    <section aria-live="polite" className="assessment-result-detail">
      <header>
        <div>
          <p className="assessment-rail-kicker">Calificación asíncrona</p>
          <h2 className="flex items-center gap-2">
            <LoaderCircle className="size-5 animate-spin" />
            Procesando expresión matemática
          </h2>
        </div>
      </header>
      <p>
        La evaluación fue enviada y la calificación matemática está en proceso.
      </p>
      {query.isError ? (
        <p className="mt-3 text-sm text-muted-foreground">
          El procesamiento continúa de forma segura. Puedes volver más tarde; no
          es necesario enviar el intento de nuevo.
        </p>
      ) : null}
    </section>
  );
}
