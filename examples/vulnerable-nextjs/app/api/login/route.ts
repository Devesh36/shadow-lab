export async function POST(request: Request) {
  const { user } = await request.json();
  if (user !== 'alice' && user !== 'bob') return Response.json({ error: 'Unknown fixture' }, { status: 401 });
  return Response.json({ token: `demo-${user}`, note: 'Synthetic fixture authentication only' });
}
