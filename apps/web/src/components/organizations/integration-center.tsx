'use client';

import {
  Cable,
  CheckCircle2,
  CircleAlert,
  ExternalLink,
  KeyRound,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  Video,
  XCircle,
} from 'lucide-react';
import { useState } from 'react';

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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { components } from '@/lib/api/generated/platform';
import {
  useConnectApiKey,
  useCreateGoogleTestMeeting,
  useDisconnectIntegration,
  useIntegrationHealthChecks,
  useIntegrations,
  useQueueIntegrationHealthCheck,
  useRotateIntegrationApiKey,
  useStartGoogleOAuth,
} from '@/lib/organizations/hooks';

type Connection = components['schemas']['IntegrationConnection'];
type Provider = 'openai' | 'gemini' | 'deepseek';
type GoogleCapability = 'calendar' | 'meet' | 'drive' | 'youtube';

const providers: Array<{
  helper: string;
  name: string;
  provider: Provider;
}> = [
  {
    provider: 'openai',
    name: 'OpenAI',
    helper:
      'Conecta una API key de proyecto y valida el acceso consultando modelos.',
  },
  {
    provider: 'gemini',
    name: 'Google AI Gemini',
    helper:
      'Conecta una API key de Google AI; es independiente de Google Workspace OAuth.',
  },
  {
    provider: 'deepseek',
    name: 'DeepSeek',
    helper: 'Conecta una API key y valida el listado de modelos permitido.',
  },
];

const googleCapabilities: Array<{
  capability: GoogleCapability;
  description: string;
  label: string;
}> = [
  {
    capability: 'calendar',
    label: 'Calendar',
    description: 'Crear y consultar eventos académicos autorizados.',
  },
  {
    capability: 'meet',
    label: 'Google Meet',
    description: 'Crear una reunión de prueba mediante Calendar.',
  },
  {
    capability: 'drive',
    label: 'Drive',
    description: 'Acceder únicamente a los archivos que autorice la cuenta.',
  },
  {
    capability: 'youtube',
    label: 'YouTube',
    description: 'Consultar recursos y canales autorizados.',
  },
];

function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : 'No fue posible completar la operación.';
}

function connectionStatus(status: string) {
  const labels: Record<string, string> = {
    connected: 'Conectada',
    connecting: 'Verificación pendiente',
    degraded: 'Requiere atención',
    disconnected: 'Desconectada',
    revoked: 'Revocada',
  };
  return labels[status] ?? status;
}

function healthStatus(status: string) {
  const labels: Record<string, string> = {
    failed: 'Fallida',
    queued: 'En cola',
    running: 'En ejecución',
    succeeded: 'Correcta',
  };
  return labels[status] ?? status;
}

export function IntegrationCenter({
  connections,
  slug,
}: Readonly<{
  connections: readonly Connection[];
  slug: string;
}>) {
  const google = useStartGoogleOAuth(slug);
  const integrations = useIntegrations(slug);
  const currentConnections = integrations.data ?? connections;
  const [capabilities, setCapabilities] = useState<GoogleCapability[]>([
    'calendar',
  ]);
  const googleConnection = currentConnections.find(
    (connection) => connection.provider === 'google_workspace',
  );

  async function startGoogleAuthorization() {
    try {
      const result = await google.mutateAsync(capabilities);
      window.location.assign(result.authorization_url);
    } catch {
      // The server response explains exactly which configuration is missing.
    }
  }

  return (
    <section className="space-y-6" aria-labelledby="integrations-title">
      <div>
        <h2 className="text-lg font-semibold" id="integrations-title">
          Conexiones externas
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          Cada conexión se guarda cifrada en el servidor, se prueba de forma
          explícita y conserva un historial de salud. Guardar una clave no
          afirma que esté funcionando: la prueba muestra su resultado real.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        {providers.map((provider) => {
          const connection = currentConnections.find(
            (candidate) => candidate.provider === provider.provider,
          );
          return connection ? (
            <ConnectedApiProviderCard
              connection={connection}
              key={provider.provider}
              name={provider.name}
              slug={slug}
            />
          ) : (
            <ApiProviderConnectCard
              helper={provider.helper}
              key={provider.provider}
              name={provider.name}
              provider={provider.provider}
              slug={slug}
            />
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cable className="size-4 text-primary" />
            Google Workspace
          </CardTitle>
          <CardDescription>
            Esta es una conexión OAuth institucional para Calendar, Meet, Drive
            y YouTube. No usa la API key de Gemini ni comparte secretos con
            ella.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {googleConnection ? (
            <GoogleConnectionCard connection={googleConnection} slug={slug} />
          ) : (
            <>
              <div className="rounded-lg border bg-muted/20 p-4 text-sm">
                <p className="font-medium">Antes de autorizar</p>
                <p className="mt-1 text-muted-foreground">
                  El administrador de despliegue debe registrar el redirect URI
                  de esta aplicación en Google Cloud y configurar
                  <code className="mx-1">GOOGLE_OAUTH_CLIENT_ID</code>,
                  <code className="mx-1">GOOGLE_OAUTH_CLIENT_SECRET</code> y
                  <code className="ml-1">GOOGLE_OAUTH_REDIRECT_URI</code> en el
                  servidor. Esta pantalla nunca solicita ni revela esos valores.
                </p>
              </div>
              <fieldset className="grid gap-3 md:grid-cols-2">
                <legend className="text-sm font-medium">
                  Capacidades que se pedirán a Google
                </legend>
                {googleCapabilities.map(
                  ({ capability, description, label }) => (
                    <label
                      className="flex cursor-pointer gap-3 rounded-lg border p-3 text-sm"
                      key={capability}
                    >
                      <input
                        checked={capabilities.includes(capability)}
                        className="mt-0.5 size-4 accent-primary"
                        onChange={(event) => {
                          setCapabilities((current) =>
                            event.target.checked
                              ? current.includes(capability)
                                ? current
                                : [...current, capability]
                              : current.filter((value) => value !== capability),
                          );
                        }}
                        type="checkbox"
                      />
                      <span>
                        <span className="block font-medium">{label}</span>
                        <span className="mt-0.5 block text-xs leading-5 text-muted-foreground">
                          {description}
                        </span>
                      </span>
                    </label>
                  ),
                )}
              </fieldset>
              {google.error ? (
                <Alert variant="destructive">
                  <CircleAlert />
                  <AlertTitle>No se pudo iniciar OAuth</AlertTitle>
                  <AlertDescription>
                    {errorMessage(google.error)}
                  </AlertDescription>
                </Alert>
              ) : null}
              <Button
                disabled={google.isPending || capabilities.length === 0}
                onClick={() => void startGoogleAuthorization()}
                type="button"
              >
                {google.isPending ? (
                  <LoaderCircle className="animate-spin" />
                ) : (
                  <ExternalLink />
                )}
                Autorizar Google Workspace
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function ApiProviderConnectCard({
  helper,
  name,
  provider,
  slug,
}: Readonly<{
  helper: string;
  name: string;
  provider: Provider;
  slug: string;
}>) {
  const connect = useConnectApiKey(slug);
  const [apiKey, setApiKey] = useState('');
  const id = `key-${provider}`;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <KeyRound className="size-4 text-primary" />
          {name}
        </CardTitle>
        <CardDescription>{helper}</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            void connect
              .mutateAsync({ provider, api_key: apiKey })
              .then(() => setApiKey(''));
          }}
        >
          <div className="space-y-2">
            <Label htmlFor={id}>API key</Label>
            <Input
              autoComplete="off"
              id={id}
              onChange={(event) => setApiKey(event.target.value)}
              required
              type="password"
              value={apiKey}
            />
          </div>
          {connect.error ? (
            <p className="text-sm text-destructive">
              {errorMessage(connect.error)}
            </p>
          ) : null}
          <Button disabled={connect.isPending || !apiKey.trim()} type="submit">
            {connect.isPending ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <KeyRound />
            )}
            Guardar y preparar prueba
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function ConnectedApiProviderCard({
  connection,
  name,
  slug,
}: Readonly<{
  connection: Connection;
  name: string;
  slug: string;
}>) {
  const [rotating, setRotating] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const health = useIntegrationHealthChecks(slug, connection.id);
  const queue = useQueueIntegrationHealthCheck(slug);
  const rotate = useRotateIntegrationApiKey(slug);
  const disconnect = useDisconnectIntegration(slug);
  const latest = health.data?.[0];
  const id = `rotate-${connection.id}`;

  async function rotateKey(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await rotate.mutateAsync({
        connectionId: connection.id,
        apiKey,
        expectedVersion: connection.lock_version,
      });
      setApiKey('');
      setRotating(false);
    } catch {
      // The API conflict or validation error is rendered below.
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">{name}</CardTitle>
            <CardDescription className="mt-1">
              {connection.last_four
                ? `Clave cifrada terminada en ${connection.last_four}`
                : 'Credencial cifrada en el servidor'}
            </CardDescription>
          </div>
          <Badge
            className="rounded"
            variant={
              connection.status === 'connected' ? 'secondary' : 'outline'
            }
          >
            {connectionStatus(connection.status)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <HealthSummary latest={latest} loading={health.isLoading} />
        {health.error ? (
          <p className="text-sm text-destructive">
            {errorMessage(health.error)}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button
            disabled={queue.isPending}
            onClick={() => void queue.mutateAsync(connection.id)}
            size="sm"
            type="button"
          >
            {queue.isPending ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <RefreshCw />
            )}
            Probar conexión
          </Button>
          <Button
            onClick={() => setRotating((current) => !current)}
            size="sm"
            type="button"
            variant="outline"
          >
            <RotateCcw />
            Rotar clave
          </Button>
          <Button
            disabled={disconnect.isPending}
            onClick={() => void disconnect.mutateAsync(connection.id)}
            size="sm"
            type="button"
            variant="outline"
          >
            <XCircle />
            Desconectar
          </Button>
        </div>
        {queue.error || rotate.error || disconnect.error ? (
          <p className="text-sm text-destructive">
            {errorMessage(queue.error ?? rotate.error ?? disconnect.error)}
          </p>
        ) : null}
        {rotating ? (
          <form
            className="space-y-3 border-t pt-3"
            onSubmit={(event) => void rotateKey(event)}
          >
            <Label htmlFor={id}>Nueva API key</Label>
            <Input
              autoComplete="off"
              id={id}
              onChange={(event) => setApiKey(event.target.value)}
              required
              type="password"
              value={apiKey}
            />
            <Button
              disabled={rotate.isPending || !apiKey.trim()}
              size="sm"
              type="submit"
            >
              {rotate.isPending ? (
                <LoaderCircle className="animate-spin" />
              ) : (
                <RotateCcw />
              )}
              Guardar nueva clave
            </Button>
          </form>
        ) : null}
      </CardContent>
    </Card>
  );
}

function GoogleConnectionCard({
  connection,
  slug,
}: Readonly<{
  connection: Connection;
  slug: string;
}>) {
  const health = useIntegrationHealthChecks(slug, connection.id);
  const queue = useQueueIntegrationHealthCheck(slug);
  const meeting = useCreateGoogleTestMeeting(slug);
  const disconnect = useDisconnectIntegration(slug);
  const latest = health.data?.[0];
  const capabilities = Array.isArray(connection.capabilities)
    ? connection.capabilities.filter(
        (capability): capability is string => typeof capability === 'string',
      )
    : [];
  const supportsMeet = capabilities.includes('meet');
  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold">
            {connection.account_label || 'Cuenta autorizada'}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Capacidades: {capabilities.join(', ') || 'ninguna'}
          </p>
        </div>
        <Badge
          className="rounded"
          variant={connection.status === 'connected' ? 'secondary' : 'outline'}
        >
          {connectionStatus(connection.status)}
        </Badge>
      </div>
      <HealthSummary latest={latest} loading={health.isLoading} />
      <div className="flex flex-wrap gap-2">
        <Button
          disabled={queue.isPending}
          onClick={() => void queue.mutateAsync(connection.id)}
          size="sm"
          type="button"
        >
          {queue.isPending ? (
            <LoaderCircle className="animate-spin" />
          ) : (
            <RefreshCw />
          )}
          Probar conexión
        </Button>
        {supportsMeet ? (
          <Button
            disabled={meeting.isPending}
            onClick={() => void meeting.mutateAsync(connection.id)}
            size="sm"
            type="button"
            variant="outline"
          >
            {meeting.isPending ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <Video />
            )}
            Crear reunión de prueba
          </Button>
        ) : null}
        <Button
          disabled={disconnect.isPending}
          onClick={() => void disconnect.mutateAsync(connection.id)}
          size="sm"
          type="button"
          variant="outline"
        >
          <XCircle />
          Desconectar
        </Button>
      </div>
      {queue.error || meeting.error || disconnect.error ? (
        <p className="text-sm text-destructive">
          {errorMessage(queue.error ?? meeting.error ?? disconnect.error)}
        </p>
      ) : null}
      {meeting.data ? (
        <Alert className="border-emerald-600/20 bg-emerald-500/5">
          <CheckCircle2 className="text-emerald-700" />
          <AlertTitle>Reunión de prueba creada</AlertTitle>
          <AlertDescription>
            La respuesta de Google fue recibida y registrada por el servicio.
          </AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}

function HealthSummary({
  latest,
  loading,
}: Readonly<{
  latest: components['schemas']['HealthCheck'] | undefined;
  loading: boolean;
}>) {
  if (loading) {
    return (
      <p className="text-xs text-muted-foreground">Consultando historial…</p>
    );
  }
  if (!latest) {
    return (
      <p className="text-xs leading-5 text-muted-foreground">
        Aún no se ha ejecutado una prueba. Usa “Probar conexión” para validar
        contra el proveedor sin generar contenido de IA.
      </p>
    );
  }
  return (
    <div className="rounded-md bg-muted/40 p-3 text-xs">
      <p className="font-medium">
        Última prueba: {healthStatus(latest.status)}
      </p>
      <p className="mt-1 text-muted-foreground">
        {new Date(latest.created_at).toLocaleString('es-CO')}
        {latest.error_code ? ` · Código: ${latest.error_code}` : ''}
      </p>
    </div>
  );
}
