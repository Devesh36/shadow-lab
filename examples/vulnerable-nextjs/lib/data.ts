export const records: Record<string, { id: string; ownerId: string; title: string; content: string }> = {
  'alice-record': { id: 'alice-record', ownerId: 'alice', title: 'Alice private record', content: 'Synthetic Alice data' },
  'bob-record': { id: 'bob-record', ownerId: 'bob', title: 'Bob private record', content: 'Synthetic Bob data' },
};
export function requireAuth(request: Request): { id: string } | null {
  const authorization = request.headers.get('authorization');
  if (authorization === 'Bearer demo-alice') return { id: 'alice' };
  if (authorization === 'Bearer demo-bob') return { id: 'bob' };
  return null;
}
