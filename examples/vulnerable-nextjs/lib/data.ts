export const records: Record<string, { id: string; ownerId: string; title: string; content: string }> = {
  'alice-record': { id: 'alice-record', ownerId: 'alice', title: 'Alice private record', content: 'Synthetic Alice data' },
  'bob-record': { id: 'bob-record', ownerId: 'bob', title: 'Bob private record', content: 'Synthetic Bob data' },
};
export function requireAuth(request: Request): { id: string } | null {
  const cookie = request.headers.get('cookie')?.split(';').map(value => value.trim()).find(value => value.startsWith('shadowlab-demo-session='))?.split('=')[1];
  const authorization = request.headers.get('authorization') ?? (cookie ? `Bearer ${cookie}` : null);
  if (authorization === 'Bearer demo-alice') return { id: 'alice' };
  if (authorization === 'Bearer demo-bob') return { id: 'bob' };
  return null;
}
