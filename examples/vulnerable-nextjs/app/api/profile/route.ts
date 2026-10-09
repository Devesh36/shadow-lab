import { requireAuth } from '../../../lib/data';

export async function GET(request: Request) {
  const user = requireAuth(request);
  if (!user) return Response.json({ error: 'Unauthorized' }, { status: 401 });
  const profile = { id: user.id, name: user.id, passwordHash: 'synthetic-not-a-real-hash', apiKey: 'synthetic-not-a-real-key' };
  // SHADOWLAB_FIX: exposure
  return Response.json(profile);
}
