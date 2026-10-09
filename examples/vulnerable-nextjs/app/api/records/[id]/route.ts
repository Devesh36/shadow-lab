import { records, requireAuth } from '../../../../lib/data';

export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  const user = requireAuth(request);
  if (!user) return Response.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await context.params;
  const record = records[id];
  if (!record) return Response.json({ error: 'Not found' }, { status: 404 });
  // SHADOWLAB_FIX: ownership
  return Response.json(record);
}
