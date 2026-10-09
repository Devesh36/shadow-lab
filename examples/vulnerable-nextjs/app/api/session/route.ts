import { requireAuth } from '../../../lib/data';

export async function GET(request: Request) {
  return Response.json({ identity: requireAuth(request)?.id ?? 'anonymous' }, { headers: { 'Cache-Control': 'no-store' } });
}
