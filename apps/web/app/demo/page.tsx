'use client';

import Link from 'next/link';
import { useState } from 'react';
import { ArrowLeft, ArrowRight, Fingerprint, Shield, Terminal } from 'lucide-react';

export default function Demo() {
  const [browser, setBrowser] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function start() {
    setBusy(true); setError('');
    try {
      const response = await fetch('/api/v1/demo/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ approved: true, browser }) });
      if (!response.ok) {
        setError(response.status === 503 ? 'The local API is unavailable. Start ShadowLab, then try again.' : `Demo setup could not start (HTTP ${response.status}). Check the local service logs and bundled demo configuration.`);
        return;
      }
      const scan = await response.json();
      if (typeof scan.id !== 'string') throw new Error('Invalid scan response');
      window.location.assign('/app?scan=' + encodeURIComponent(scan.id));
    } catch { setError('Could not connect to the local workspace. Check that ShadowLab is running, then try again.'); }
    finally { setBusy(false); }
  }
  return <main className="guided-demo">
    <Link className="demo-back" href="/"><ArrowLeft size={16} /> Back to ShadowLab</Link>
    <div className="guided-demo-card"><Shield size={36} /><span className="landing-kicker">A GUIDED FIRST INVESTIGATION</span><h1>See ShadowLab work.</h1><p>Run real security checks against the bundled demo. Every account and record is synthetic. Your existing workspace settings stay in place.</p>
      <ol><li><Terminal size={19} /><div><strong>Investigate</strong><span>Read the source and test authentication, ownership, sensitive fields and headers.</span></div></li><li><Fingerprint size={19} /><div><strong>Inspect evidence</strong><span>Follow the live investigation and open findings with sanitized responses.</span></div></li><li><Shield size={19} /><div><strong>Review a fix</strong><span>Choose a finding and explicitly approve its disposable patch verification.</span></div></li></ol>
      <label className="checkbox"><input type="checkbox" checked={browser} onChange={event => setBrowser(event.target.checked)} disabled={busy} /><span>Also validate through the browser with three isolated identities.<br /><small>Requires Playwright Chromium on the API host; unavailable setup is reported as incomplete coverage.</small></span></label>
      <p className="demo-approval">By selecting Start demo, you authorize bounded tests of the bundled synthetic local app. Patch experiments require a separate action.</p>
      {error && <div className="notice error" role="alert">{error}</div>}
      <button className="landing-primary" onClick={start} disabled={busy}>{busy ? 'Starting investigation…' : 'Start demo'}<ArrowRight size={17} /></button>
      <p className="demo-helper">If the services are not running yet, open <code>shadow repl</code> and choose <code>demo</code>, or follow the <a href="https://github.com/Devesh36/shadow-lab#readme">local setup instructions</a>.</p>
    </div>
  </main>;
}
