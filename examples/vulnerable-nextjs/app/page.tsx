export default function Page() {
  return <main><p style={{ color: '#67e8f9' }}>SHADOWLAB / DISPOSABLE TARGET</p><h1>Authorization test laboratory</h1><p>Two synthetic users. Two synthetic records. No real data.</p><p>This application intentionally contains security defects. Bind to loopback only.</p><ul><li>GET /api/records/alice-record — missing ownership guard</li><li>GET /api/unprotected — missing authentication</li><li>GET /api/profile — credential-field exposure</li></ul></main>;
}
