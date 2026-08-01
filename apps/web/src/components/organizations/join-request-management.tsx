'use client';

import { Check, CircleX, Inbox, LoaderCircle } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import type { components } from '@/lib/api/generated/platform';
import {
  useOrganizationJoinRequests,
  useReviewJoinRequest,
} from '@/lib/organizations/hooks';

type JoinRequestList = components['schemas']['PaginatedJoinRequestList'];

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    approved: 'Aprobada',
    pending: 'Pendiente',
    rejected: 'Rechazada',
  };
  return labels[status] ?? status;
}

export function JoinRequestManagement({
  initial,
  slug,
}: Readonly<{
  initial: JoinRequestList;
  slug: string;
}>) {
  const query = useOrganizationJoinRequests(slug);
  const review = useReviewJoinRequest(slug);
  const requests = query.data ?? initial;

  return (
    <section className="space-y-5" aria-labelledby="join-requests-title">
      <div>
        <h2 className="text-lg font-semibold" id="join-requests-title">
          Solicitudes de ingreso
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Aprueba o rechaza personas que completaron el flujo público. Al
          aprobar, el servidor crea la membresía con la regla institucional
          vigente y la registra en el historial.
        </p>
      </div>
      {review.error ? (
        <Alert variant="destructive">
          <AlertTitle>No se pudo revisar la solicitud</AlertTitle>
          <AlertDescription>
            {review.error instanceof Error
              ? review.error.message
              : 'No fue posible completar la acción.'}
          </AlertDescription>
        </Alert>
      ) : null}
      {requests.results.length ? (
        <div className="grid gap-4">
          {requests.results.map((request) => {
            const pending = request.status === 'pending';
            return (
              <Card key={request.id}>
                <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <CardTitle className="text-base">
                      {request.user.display}
                    </CardTitle>
                    <CardDescription className="mt-1 break-all">
                      {request.email}
                    </CardDescription>
                  </div>
                  <Badge
                    className="rounded"
                    variant={pending ? 'secondary' : 'outline'}
                  >
                    {statusLabel(request.status)}
                  </Badge>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Recibida{' '}
                    {new Date(request.created_at).toLocaleString('es-CO')}
                  </p>
                  {pending ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        disabled={review.isPending}
                        onClick={() =>
                          void review.mutateAsync({
                            joinRequestId: request.id,
                            action: 'approve',
                          })
                        }
                        size="sm"
                        type="button"
                      >
                        {review.isPending ? (
                          <LoaderCircle className="animate-spin" />
                        ) : (
                          <Check />
                        )}
                        Aprobar
                      </Button>
                      <Button
                        disabled={review.isPending}
                        onClick={() =>
                          void review.mutateAsync({
                            joinRequestId: request.id,
                            action: 'reject',
                          })
                        }
                        size="sm"
                        type="button"
                        variant="outline"
                      >
                        <CircleX />
                        Rechazar
                      </Button>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <Inbox className="mx-auto size-7 text-muted-foreground" />
            <p className="mt-3 font-medium">No hay solicitudes pendientes</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Cuando alguien complete el ingreso público, aparecerá aquí para su
              revisión.
            </p>
          </CardContent>
        </Card>
      )}
    </section>
  );
}
