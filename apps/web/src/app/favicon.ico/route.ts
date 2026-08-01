const FAVICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#12263f"/><path d="M14 18.5c7.8-2.6 13.8-.9 18 3.4v26.6c-4.2-4.3-10.2-6-18-3.4V18.5Z" fill="#f8fafc"/><path d="M50 18.5c-7.8-2.6-13.8-.9-18 3.4v26.6c4.2-4.3 10.2-6 18-3.4V18.5Z" fill="#dbeafe"/><path d="M32 21.9v26.6" stroke="#60a5fa" stroke-width="2"/></svg>`;

export function GET() {
  return new Response(FAVICON, {
    headers: {
      'Cache-Control': 'public, max-age=86400',
      'Content-Type': 'image/svg+xml',
    },
  });
}
