'use client';

import { useEffect, useState } from 'react';

export default function Page() {
  const [identity, setIdentity] = useState('checking');
  const [record, setRecord] = useState('alice-record');
  const [result, setResult] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function activeIdentity() {
    const response = await fetch('/api/session', { cache: 'no-store', credentials: 'same-origin' });
    if (!response.ok) throw new Error('Session check failed');
    const body = await response.json();
    setIdentity(body.identity);
    return body.identity;
  }
  useEffect(() => { activeIdentity().catch(() => setError('Session check failed')); }, []);
  async function action(work: () => Promise<void>) {
    setBusy(true); setError(''); setResult(undefined);
    try { await work(); } catch { setError('Request failed; coverage incomplete'); }
    finally { setBusy(false); }
  }
  async function login(user: string) {
    const response = await fetch('/api/login', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user }) });
    if (!response.ok) throw new Error('Login failed');
    sessionStorage.setItem('fixture-label', user);
    await activeIdentity();
  }
  async function logout() {
    const response = await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' });
    if (!response.ok) throw new Error('Logout failed');
    sessionStorage.clear(); localStorage.clear();
    await activeIdentity();
  }
  async function inspect(path: string) {
    const response = await fetch(path, { cache: 'no-store', credentials: 'same-origin' });
    const body = await response.json();
    // Display identifiers and field names, never sensitive response values.
    setResult({ status: response.status, id: body.id ?? null, ownerId: body.ownerId ?? null,
      sensitive_fields: Object.keys(body).filter(key => /password|secret|token|authorization|cookie|api[_-]?key/i.test(key)).sort() });
  }
  return <main><p style={{ color: '#67e8f9' }}>SHADOWLAB / DISPOSABLE TARGET</p>
    <h1>Authorization test laboratory</h1><p>Two synthetic accounts and two seeded, disposable records. No real data.</p>
    <p>This application intentionally contains security defects. Bind to loopback only.</p>
    <p>Active identity: <strong data-testid="identity">{identity}</strong></p>
    <div><button disabled={busy} onClick={() => action(() => login('alice'))}>Log in as Alice</button>{' '}
      <button disabled={busy} onClick={() => action(() => login('bob'))}>Log in as Bob</button>{' '}
      <button disabled={busy} onClick={() => action(logout)}>Log out</button>{' '}
      <button disabled={busy} onClick={() => action(async () => { await activeIdentity(); })}>Check identity</button></div>
    <p><label>Record ID <input aria-label="Record ID" value={record} onChange={event => setRecord(event.target.value)} /></label>{' '}
      <button disabled={busy} onClick={() => action(() => inspect(`/api/records/${encodeURIComponent(record)}`))}>Open record</button></p>
    <p><button disabled={busy} onClick={() => action(() => inspect('/api/unprotected'))}>Open protected resource</button>{' '}
      <button disabled={busy} onClick={() => action(() => inspect('/api/profile'))}>Open profile</button></p>
    {error && <p role="alert">{error}</p>}<pre data-testid="result">{result ? JSON.stringify(result, null, 2) : ''}</pre>
  </main>;
}
