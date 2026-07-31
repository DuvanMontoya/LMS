'use client';

import { apiErrorMessage } from '@/lib/api/api-error';
import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

export type UploadInstructions = components['schemas']['UploadInstructions'];
export type ProcessingJob = components['schemas']['ProcessingJob'];

async function required<T>(
  request: Promise<{ error?: unknown; response: Response; data?: T }>,
  fallback: string,
): Promise<T> {
  const { data, error, response } = await request;
  if (response.ok && data !== undefined) return data;
  throw new Error(apiErrorMessage(error, fallback));
}

export async function initializeUpload(
  slug: string,
  body: components['schemas']['UploadInitialize'],
): Promise<UploadInstructions> {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{organization_slug}/uploads/',
      { body, params: { path: { organization_slug: slug } } },
    ),
    'No fue posible preparar la carga.',
  );
}

export async function completeUpload(
  slug: string,
  sessionId: string,
): Promise<ProcessingJob> {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{organization_slug}/uploads/{session_id}/complete/',
      {
        params: {
          path: { organization_slug: slug, session_id: sessionId },
        },
      },
    ),
    'No fue posible completar la carga.',
  );
}

export async function abortUpload(slug: string, sessionId: string) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{organization_slug}/uploads/{session_id}/abort/',
      {
        params: {
          path: { organization_slug: slug, session_id: sessionId },
        },
      },
    ),
    'No fue posible cancelar la carga.',
  );
}

export async function processingJob(
  slug: string,
  jobId: string,
): Promise<ProcessingJob> {
  return required(
    platformBrowserClient.GET(
      '/api/v1/organizations/{organization_slug}/processing-jobs/{job_id}/',
      {
        params: { path: { job_id: jobId, organization_slug: slug } },
      },
    ),
    'No fue posible consultar el procesamiento.',
  );
}

async function sha256Base64(blob: Blob): Promise<string> {
  const digest = await crypto.subtle.digest(
    'SHA-256',
    await blob.arrayBuffer(),
  );
  let binary = '';
  for (const byte of new Uint8Array(digest))
    binary += String.fromCharCode(byte);
  return btoa(binary);
}

function xhrRequest({
  body,
  headers,
  method,
  onProgress,
  register,
  url,
}: {
  body: XMLHttpRequestBodyInit;
  headers?: Readonly<Record<string, string>>;
  method: 'POST' | 'PUT';
  onProgress: (loaded: number) => void;
  register: (xhr: XMLHttpRequest) => void;
  url: string;
}): Promise<XMLHttpRequest> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    register(xhr);
    xhr.open(method, url);
    for (const [name, value] of Object.entries(headers ?? {})) {
      xhr.setRequestHeader(name, value);
    }
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) onProgress(event.loaded);
    });
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(xhr);
      else
        reject(
          new Error(`El almacenamiento rechazó la carga (${xhr.status}).`),
        );
    });
    xhr.addEventListener('error', () =>
      reject(new Error('Se perdió la conexión durante la carga.')),
    );
    xhr.addEventListener('abort', () =>
      reject(new DOMException('Carga cancelada.', 'AbortError')),
    );
    xhr.send(body);
  });
}

export async function uploadSingle({
  file,
  instructions,
  onProgress,
  register,
}: {
  file: File;
  instructions: UploadInstructions;
  onProgress: (loaded: number) => void;
  register: (xhr: XMLHttpRequest) => void;
}) {
  if (!instructions.post)
    throw new Error('Faltan instrucciones de carga simple.');
  const body = new FormData();
  for (const [name, value] of Object.entries(instructions.post.fields)) {
    body.append(name, value);
  }
  body.append('file', file);
  await xhrRequest({
    body,
    method: 'POST',
    onProgress,
    register,
    url: instructions.post.url,
  });
}

async function retry<T>(operation: () => Promise<T>, attempts = 2): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= attempts; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      if (error instanceof DOMException && error.name === 'AbortError')
        throw error;
      if (attempt < attempts)
        await new Promise((resolve) => setTimeout(resolve, 400 * 2 ** attempt));
    }
  }
  throw lastError;
}

export async function uploadMultipart({
  file,
  instructions,
  onProgress,
  register,
  slug,
}: {
  file: File;
  instructions: UploadInstructions;
  onProgress: (loaded: number) => void;
  register: (xhr: XMLHttpRequest) => void;
  slug: string;
}) {
  const partSize = instructions.part_size_bytes;
  if (!partSize) throw new Error('Falta el tamaño de parte multipart.');
  const parts = Array.from(
    { length: Math.ceil(file.size / partSize) },
    (_, index) => ({
      blob: file.slice(
        index * partSize,
        Math.min((index + 1) * partSize, file.size),
      ),
      number: index + 1,
    }),
  );
  const loaded = new Map<number, number>();
  let cursor = 0;
  async function worker() {
    while (cursor < parts.length) {
      const part = parts[cursor++];
      if (!part) return;
      const checksum = await sha256Base64(part.blob);
      await retry(async () => {
        const signed = await required(
          platformBrowserClient.POST(
            '/api/v1/organizations/{organization_slug}/uploads/{session_id}/parts/{part_number}/sign/',
            {
              body: { checksum_sha256: checksum },
              params: {
                path: {
                  organization_slug: slug,
                  part_number: part.number,
                  session_id: instructions.session_id,
                },
              },
            },
          ),
          'No fue posible firmar una parte.',
        );
        const xhr = await xhrRequest({
          body: part.blob,
          headers: { 'x-amz-checksum-sha256': checksum },
          method: 'PUT',
          onProgress: (value) => {
            loaded.set(part.number, value);
            onProgress(
              [...loaded.values()].reduce((sum, item) => sum + item, 0),
            );
          },
          register,
          url: signed.url,
        });
        const etag = xhr.getResponseHeader('ETag')?.replaceAll('"', '');
        if (!etag) throw new Error('El almacenamiento no devolvió ETag.');
        await required(
          platformBrowserClient.POST(
            '/api/v1/organizations/{organization_slug}/uploads/{session_id}/parts/{part_number}/record/',
            {
              body: {
                checksum_sha256: checksum,
                etag,
                size_bytes: part.blob.size,
              },
              params: {
                path: {
                  organization_slug: slug,
                  part_number: part.number,
                  session_id: instructions.session_id,
                },
              },
            },
          ),
          'No fue posible registrar una parte.',
        );
      });
    }
  }
  await Promise.all([worker(), worker(), worker()]);
}
