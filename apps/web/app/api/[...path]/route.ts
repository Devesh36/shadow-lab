import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';
type Context = { params: Promise<{ path: string[] }> };
async function proxy(request: NextRequest, context: Context) {
  const host = request.headers.get('host')?.split(':')[0];
  // This is a local single-user dashboard, not a public authenticated portal.
  if (!host || !['localhost', '127.0.0.1', 'web'].includes(host)) return Response.json({ detail: 'Local dashboard only' }, { status: 403 });
  const origin = request.headers.get('origin');
  if (origin && new URL(origin).host !== request.headers.get('host')) return Response.json({ detail: 'Cross-origin access denied' }, { status: 403 });
  const segments = (await context.params).path;
  if (segments.some(p => !/^[a-zA-Z0-9_-]+$/.test(p)) || segments[0] !== 'v1') return new Response('Not found', { status: 404 });
  try {
    const token = process.env.SHADOWLAB_API_TOKEN || (await readFile(process.env.SHADOWLAB_TOKEN_FILE || path.resolve(process.cwd(), '../../.shadowlab/api-token'), 'utf8')).trim();
    const api = process.env.SHADOWLAB_API_URL || 'http://127.0.0.1:8000';
    const body = request.method === 'GET' ? undefined : await request.text();
    if (body && body.length > 65536) return new Response('Request too large', { status: 413 });
    const result = await fetch(`${api}/api/${segments.join('/')}${request.nextUrl.search}`, {
      method: request.method, headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
      body, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(180000),
    });
    return new Response(result.body, { status: result.status, headers: { 'Content-Type': result.headers.get('content-type') || 'application/json', 'Cache-Control': 'no-store' } });
  } catch {
    return Response.json({ detail: 'Backend unavailable. Start the API and check the server token configuration.' }, { status: 503 });
  }
}
export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
