export async function POST() {
  return Response.json({ identity: 'anonymous' }, {
    headers: { 'Set-Cookie': 'shadowlab-demo-session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0', 'Cache-Control': 'no-store' },
  });
}
