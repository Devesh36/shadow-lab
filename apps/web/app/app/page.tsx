'use client';

import { useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from '@tanstack/react-query';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { Activity, ArrowLeft, ArrowRight, CheckCircle2, ChevronRight, CircleDot, Download, FileCode2, FolderGit2, LayoutDashboard, LockKeyhole, Play, Plus, Radar, Settings2, Shield, ShieldCheck, Square, Terminal, Wrench } from 'lucide-react';
import { Button } from '@/components/ui/button';

type View = 'Overview' | 'Repositories' | 'Scan workspace' | 'Findings' | 'Settings';
type Repository = { id: string; name: string; path: string };
type Route = { path: string; methods: string[]; source: { file: string; line: number }; authentication_observed: boolean };
type Scan = { id: string; repository_id: string; status: string; stage: string; target?: string; commit?: string; created_at: string; surface?: { routes: Route[]; analysis_limitations: string }; scanners?: Record<string, { status: string; reason?: string }>; engine?: string; error?: string };
type Evidence = { status: number; path: string; identity: string; body: unknown; sensitive_fields: string[] };
type Finding = { id: string; parent_id: string; title: string; severity: string; category: string; cwe?: string; endpoint: string; state: string; validation: string; root_cause: string; remediation: string; observations: string[]; conditions: string[]; expected: string; sources: { file: string; line: number }[]; evidence: Evidence[]; browser?: { status: string; verdict: string; validation: string; evidence: unknown[]; evidence_path?: string; screenshot_path?: string; artifact_id?: string } };
type Event = { id: string; stage: string; message: string; created_at: string; decision?: string; state?: string };
type Patch = { diff: string; verification: { passed: boolean; validation: string; test_count: number; browser?: unknown }; regression_plan: unknown; review_required: boolean };
type Configuration = { targets: { url: string; authorized: boolean; approved: boolean; allow_loopback: boolean }[]; request_budget: number; timeout_seconds: number; max_hypotheses: number; fixture?: { endpoint: string }; llm_enabled: boolean; llm_model: string; llm_base_url?: string; llm_key_configured: boolean; sandbox_mode: string };

const confirmedStates = ['CONFIRMED', 'FIX_PROPOSED', 'FIX_TESTED', 'AWAITING_REVIEW'];
const colors: Record<string, string> = { critical: '#fb7185', high: '#f18d94', medium: '#e7bb77', low: '#7aaae4', info: '#8793a4' };
async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`/api/v1/${path}`, { method, headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  const payload = await response.json();
  if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Request rejected. Check configuration and input values.');
  return payload;
}
function Badge({ value }: { value: string }) { return <span className={`badge ${value}`}>{value.replaceAll('_', ' ')}</span>; }
function Empty({ title, text }: { title: string; text: string }) { return <div className="empty"><Radar size={30} /><h3>{title}</h3><p>{text}</p></div>; }
function date(value: string) { return new Date(value).toLocaleString(); }

export default function Page() {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: 1 } } }));
  return <QueryClientProvider client={client}><Dashboard /></QueryClientProvider>;
}

function Dashboard() {
  const cache = useQueryClient();
  const [view, setView] = useState<View>('Overview');
  useEffect(() => { const scan = new URLSearchParams(window.location.search).get('scan'); if (scan) { setSelectedScan(scan); setView('Scan workspace'); } }, []);
  const [selectedFinding, setSelectedFinding] = useState<string>();
  const [selectedScan, setSelectedScan] = useState<string>();
  const [events, setEvents] = useState<Event[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [repoPath, setRepoPath] = useState('examples/vulnerable-nextjs');
  const [repoChoice, setRepoChoice] = useState('');
  const [target, setTarget] = useState('');
  const [browserValidation, setBrowserValidation] = useState(false);
  const [filter, setFilter] = useState('all');
  const repositoriesQuery = useQuery({ queryKey: ['repositories'], queryFn: () => api<Repository[]>('repositories'), refetchInterval: 5000 });
  const scansQuery = useQuery({ queryKey: ['scans'], queryFn: () => api<Scan[]>('scans'), refetchInterval: 2000 });
  const findingsQuery = useQuery({ queryKey: ['findings'], queryFn: () => api<Finding[]>('findings'), refetchInterval: 2000 });
  const settingsQuery = useQuery({ queryKey: ['settings'], queryFn: () => api<Configuration>('settings') });
  const health = useQuery({ queryKey: ['health'], queryFn: () => api<{ status: string }>('health'), refetchInterval: 10000 });
  const repos = repositoriesQuery.data || [];
  const scans = scansQuery.data || [];
  const findings = findingsQuery.data || [];
  const scanId = selectedScan || scans.at(-1)?.id;
  const scanQuery = useQuery({ queryKey: ['scan', scanId], queryFn: () => api<Scan>(`scans/${scanId}`), enabled: !!scanId, refetchInterval: 2000 });
  const currentScan = scanQuery.data;
  const finding = findings.find(f => f.id === selectedFinding);
  const patchQuery = useQuery({ queryKey: ['patch', selectedFinding], queryFn: () => api<Patch>(`findings/${selectedFinding}/patch`), enabled: !!finding && ['FIX_PROPOSED', 'FIX_TESTED', 'AWAITING_REVIEW'].includes(finding.state), retry: false });
  const confirmed = findings.filter(f => confirmedStates.includes(f.state));
  const active = scans.filter(s => ['running', 'queued'].includes(s.status));
  const severity = Object.keys(colors).map(name => ({ name, value: confirmed.filter(f => f.severity === name).length })).filter(d => d.value > 0);

  useEffect(() => {
    setEvents([]);
    if (!scanId) return;
    const stream = new EventSource(`/api/v1/scans/${scanId}/events`);
    stream.onmessage = event => setEvents(previous => {
      const next = JSON.parse(event.data) as Event;
      return previous.some(e => e.id === next.id) ? previous : [...previous, next];
    });
    stream.addEventListener('done', () => { stream.close(); cache.invalidateQueries(); });
    stream.onerror = () => stream.close();
    return () => stream.close();
  }, [scanId, cache]);

  async function act(work: () => Promise<void>) {
    setBusy(true); setError('');
    try { await work(); await cache.invalidateQueries(); return true; }
    catch (e) { setError(e instanceof Error ? e.message : 'Operation failed'); return false; }
    finally { setBusy(false); }
  }
  function navigate(next: View) { setView(next); setSelectedFinding(undefined); setError(''); }
  async function startScan() {
    const id = repoChoice || repos[0]?.id;
    if (!id) throw new Error('Register a repository first.');
    const result = await api<Scan>('scans', 'POST', { repository_id: id, dynamic: !!target.trim(), target: target.trim() || null, browser: browserValidation });
    setSelectedScan(result.id); navigate('Scan workspace');
  }
  const queryError = repositoriesQuery.error || scansQuery.error || findingsQuery.error;
  const nav = [{ title: 'Overview' as View, icon: LayoutDashboard }, { title: 'Repositories' as View, icon: FolderGit2 }, { title: 'Scan workspace' as View, icon: Radar }, { title: 'Findings' as View, icon: ShieldCheck }, { title: 'Settings' as View, icon: Settings2 }];

  function findingTable(items: Finding[]) {
    if (!items.length) return <Empty title="No findings in this view" text="Run an investigation to collect source hypotheses and runtime evidence." />;
    return <table><thead><tr><th>Severity</th><th>Finding / component</th><th>Validation</th><th></th></tr></thead><tbody>{items.map(f => <tr key={f.id} className="clickable"><td><Badge value={f.severity} /></td><td><button className="button button-ghost" style={{ padding: 0, textAlign: 'left', whiteSpace: 'normal' }} onClick={() => { setSelectedFinding(f.id); setView('Findings'); }}>{f.title}</button><p className="muted mono" style={{ marginTop: 6 }}>{f.endpoint}</p></td><td><Badge value={f.state} /></td><td><Button variant="ghost" aria-label={`Inspect ${f.title}`} onClick={() => { setSelectedFinding(f.id); setView('Findings'); }}><ChevronRight size={15} /></Button></td></tr>)}</tbody></table>;
  }

  return <div className="shell">
    <aside className="sidebar"><div className="brand"><Shield size={25} />shadowlab<small>V1</small></div><div><div className="navlabel">Workspace</div><nav className="nav" aria-label="Main navigation">{nav.map(({ title, icon: Icon }) => <button key={title} className={view === title ? 'active' : ''} onClick={() => navigate(title)}><Icon size={17} />{title}</button>)}</nav></div><div className="sidebar-footer"><p><span className="dot" />Local-first workspace</p><p>Bounded tests. Inspectable evidence.</p><p className="mono" style={{ marginTop: 10 }}>RULES + LANGGRAPH</p></div></aside>
    <main className="main"><header className="topbar"><span>Workspace <span style={{ margin: '0 10px' }}>/</span> <strong>{view}</strong></span><span className="row"><CircleDot size={13} color={health.data ? '#65ded7' : '#e7bb77'} />API {health.data ? 'connected' : 'connecting'}</span></header>
      <div className="content"><div className="heading"><div><p className="eyebrow" style={{ margin: '0 0 10px' }}>Application security / investigation engine</p><h1>{finding ? 'Finding detail' : view === 'Overview' ? 'Security overview' : view}</h1><p>{finding ? 'Inspect the evidence. Verify the fix. Keep the final decision.' : { Overview: 'Your application security posture, grounded in observed evidence.', Repositories: 'Register source code and define the scope of your investigation.', 'Scan workspace': 'Follow the investigation from source discovery to validation.', Findings: 'Source hypotheses and confirmed results, with clear validation states.', Settings: 'Explicit permissions, bounded execution, and provider configuration.' }[view]}</p></div>{view === 'Overview' && <Button onClick={() => navigate('Scan workspace')}><Plus size={15} />New investigation</Button>}{finding && <Button variant="outline" onClick={() => setSelectedFinding(undefined)}><ArrowLeft size={14} />All findings</Button>}</div>
      {(error || queryError) && <div className="notice error" role="alert">{error || (queryError instanceof Error ? queryError.message : 'Backend request failed')}</div>}

      {view === 'Overview' && <>
        <div className="stats">{[{ label: 'Repositories', value: repos.length, note: 'Registered source directories', icon: FolderGit2 }, { label: 'Completed scans', value: scans.filter(s => s.status === 'completed').length, note: 'Persisted investigations', icon: CheckCircle2 }, { label: 'Active scans', value: active.length, note: 'Running or queued', icon: Activity }, { label: 'Confirmed findings', value: confirmed.length, note: 'Supported by runtime evidence', icon: ShieldCheck }].map(({ label, value, note, icon: Icon }) => <div className="stat" key={label}><div className="stat-label">{label}<Icon size={16} /></div><div className="stat-number">{value}</div><div className="stat-note">{note}</div></div>)}</div>
        <div className="grid"><section className="panel"><div className="panel-heading"><h2>Investigation activity</h2><Button variant="ghost" onClick={() => navigate('Scan workspace')}>Open workspace<ArrowRight size={13} /></Button></div>{scans.length ? <table><thead><tr><th>Repository</th><th>Stage</th><th>Status</th></tr></thead><tbody>{scans.slice(-4).reverse().map(s => <tr key={s.id}><td><button className="button button-ghost" style={{ padding: 0 }} onClick={() => { setSelectedScan(s.id); navigate('Scan workspace'); }}>{repos.find(r => r.id === s.repository_id)?.name || 'Repository'}</button><p className="mono muted" style={{ marginTop: 6 }}>{s.id.slice(0, 8)}</p></td><td>{s.stage}</td><td><Badge value={s.status} /></td></tr>)}</tbody></table> : <Empty title="Your first investigation starts here" text="Register a repository, then analyze its routes and security boundaries." />}</section>
        <section className="panel"><div className="panel-heading"><h2>Severity distribution</h2><span className="mono muted">CONFIRMED</span></div>{severity.length ? <><div className="chart"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={severity} dataKey="value" nameKey="name" innerRadius={52} outerRadius={72} paddingAngle={4} stroke="none" isAnimationActive={false}>{severity.map(d => <Cell key={d.name} fill={colors[d.name]} />)}</Pie><Tooltip contentStyle={{ background: '#111c28', border: '1px solid #344454', color: '#e5edf4' }} /></PieChart></ResponsiveContainer></div><div className="legend">{severity.map(d => <span key={d.name}><i style={{ background: colors[d.name] }} />{d.name} · {d.value}</span>)}</div></> : <Empty title="No confirmed results yet" text="Only evidence-backed findings appear in this chart." />}</section></div>
        <section className="panel"><div className="panel-heading"><h2>Recent findings</h2><Button variant="ghost" onClick={() => navigate('Findings')}>View all<ArrowRight size={13} /></Button></div>{findingTable(findings.slice(-5).reverse())}</section>
      </>}

      {view === 'Repositories' && <div className="stack"><section className="panel"><div className="panel-heading"><h2>Register a local repository</h2><FileCode2 size={16} className="muted" /></div><div className="panel-body stack"><p className="muted small">Paths must be inside the configured repository root. Source analysis does not execute repository code.</p><label>Repository path<input value={repoPath} onChange={e => setRepoPath(e.target.value)} placeholder="examples/vulnerable-nextjs" /></label><div><Button disabled={busy || !repoPath} onClick={() => act(async () => { const result = await api<Repository>('repositories', 'POST', { path: repoPath }); setRepoChoice(result.id); })}><Plus size={14} />Register repository</Button></div></div></section><section className="panel"><div className="panel-heading"><h2>Registered repositories</h2><span className="badge">{repos.length} TOTAL</span></div>{repos.length ? <table><thead><tr><th>Repository</th><th>Local path</th><th></th></tr></thead><tbody>{repos.map(r => <tr key={r.id}><td><div className="row"><FolderGit2 size={15} color="#65ded7" />{r.name}</div></td><td className="mono muted">{r.path}</td><td><Button variant="outline" onClick={() => { setRepoChoice(r.id); navigate('Scan workspace'); }}>Investigate<ArrowRight size={12} /></Button></td></tr>)}</tbody></table> : <Empty title="No repositories registered" text="The included vulnerable-nextjs application is a disposable synthetic fixture." />}</section></div>}

      {view === 'Scan workspace' && <div className="stack"><section className="panel"><div className="panel-heading"><h2>Start an investigation</h2><span className="mono muted">BOUNDED DYNAMIC TOOLS</span></div><div className="panel-body stack"><div className="formgrid"><label>Source repository<select value={repoChoice || repos[0]?.id || ''} onChange={e => setRepoChoice(e.target.value)}><option value="" disabled>Select a repository</option>{repos.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select></label><label>Authorized target origin (optional)<input value={target} onChange={e => setTarget(e.target.value)} placeholder="http://127.0.0.1:3001" /></label></div><p className="small muted">Leave the target empty for static analysis. Runtime tests require authorization, execution approval, and synthetic fixtures in Settings.</p><label className="checkbox"><input type="checkbox" checked={browserValidation} onChange={e => setBrowserValidation(e.target.checked)} />Validate the trusted local demo UI with three isolated browser identities (fixed synthetic login/logout POSTs).</label><p className="small muted">Browser assets and identity checks count toward the saved request budget. A full browser scan typically needs 150 requests and a 180-second scan timeout; incomplete coverage is inconclusive.</p><div className="row"><Button disabled={busy || !repos.length} onClick={() => act(startScan)}><Play size={14} />{busy ? 'Starting…' : 'Run investigation'}</Button><Button variant="ghost" onClick={() => navigate('Settings')}><LockKeyhole size={14} />Configure permissions</Button></div></div></section>
        {scans.length > 0 && <label>Investigation<select value={scanId || ''} onChange={e => setSelectedScan(e.target.value)}>{[...scans].reverse().map(s => <option key={s.id} value={s.id}>{s.id.slice(0, 8)} · {repos.find(r => r.id === s.repository_id)?.name} · {s.status}</option>)}</select></label>}
        {currentScan && <><section className="panel"><div className="panel-heading"><div className="row"><h2>Investigation {currentScan.id.slice(0, 8)}</h2><Badge value={currentScan.status} /></div><div className="row"><a className="button button-outline" href={`/api/v1/reports/${currentScan.id}`} download={`shadowlab-${currentScan.id.slice(0, 8)}.md`}><Download size={13} />Report</a>{['queued', 'running'].includes(currentScan.status) && <Button variant="destructive" disabled={busy} onClick={() => act(async () => { await api(`scans/${currentScan.id}/cancel`, 'POST'); })}><Square size={12} />Stop scan</Button>}</div></div><div className="flow">{['reconnaissance', 'hypotheses', 'planning', 'validation', 'reporting', 'completed'].map(stage => <span key={stage} className={stage === currentScan.stage ? 'active' : ''}>{stage}</span>)}</div><div className="panel-body" style={{ paddingTop: 0 }}><p className="mono muted">{currentScan.target || 'Static analysis only'} · {currentScan.engine || 'Preparing engine'} · commit {currentScan.commit?.slice(0, 12) || 'uncommitted'}</p>{currentScan.error && <p className="notice error">Scan failed: {currentScan.error}. Inspect the event timeline and server logs.</p>}{currentScan.scanners && <div className="row" style={{ marginTop: 12 }}>{Object.entries(currentScan.scanners).map(([name, tool]) => <span key={name} className="small muted" title={tool.reason}>{name}: <Badge value={tool.status} /></span>)}</div>}</div></section>
        <div className="grid"><section className="panel"><div className="panel-heading"><h2>Discovered attack surface</h2><span className="badge">{currentScan.surface?.routes.length || 0} ROUTES</span></div>{currentScan.surface?.routes.length ? <table><thead><tr><th>Route</th><th>Methods</th><th>Auth pattern</th></tr></thead><tbody>{currentScan.surface.routes.map(r => <tr key={r.source.file}><td className="mono">{r.path}<p className="muted small" style={{ marginTop: 5 }}>{r.source.file}:{r.source.line}</p></td><td className="mono muted">{r.methods.join(', ')}</td><td>{r.authentication_observed ? 'Observed' : 'Not observed'}</td></tr>)}</tbody></table> : <Empty title="Awaiting source discovery" text="Routes appear here after reconnaissance." />}</section><section className="panel"><div className="panel-heading"><h2>Agent activity</h2><Activity size={15} color="#65ded7" /></div><div className="panel-body" style={{ maxHeight: 450, overflowY: 'auto' }}>{events.length ? events.map(e => <div className="event" key={e.id}><div className="row space"><span className="eyebrow">{e.stage}{e.decision ? ` / ${e.decision}` : ''}</span><time>{new Date(e.created_at).toLocaleTimeString()}</time></div><p>{e.message}</p></div>) : <p className="muted small">Waiting for events…</p>}</div></section></div><section className="panel"><div className="panel-heading"><h2>Hypotheses & validation</h2></div>{findingTable(findings.filter(f => f.parent_id === currentScan.id))}</section><p className="small muted">{currentScan.surface?.analysis_limitations}</p></>}
      </div>}

      {view === 'Findings' && !finding && <section className="panel"><div className="panel-heading"><h2>Finding register</h2><label className="row"><span className="small muted">Filter</span><select aria-label="Filter findings" style={{ width: 'auto' }} value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All states</option><option value="confirmed">Evidence-backed</option><option value="INCONCLUSIVE">Inconclusive</option><option value="NOT_REPRODUCED">Not reproduced</option><option value="AWAITING_REVIEW">Awaiting review</option></select></label></div>{findingTable([...findings].reverse().filter(f => filter === 'all' || (filter === 'confirmed' ? confirmedStates.includes(f.state) : f.state === filter)))}</section>}
      {view === 'Findings' && finding && <><div className="notice"><div className="row" style={{ flexWrap: 'wrap' }}><Badge value={finding.severity} /><Badge value={finding.state} /><span>{finding.cwe || 'Security observation'} · {finding.category}</span></div><h2 style={{ marginTop: 12 }}>{finding.title}</h2></div><div className="detail"><section className="panel"><div className="panel-heading"><h2>Technical assessment</h2></div><div className="panel-body"><section><h3>Validation result</h3><p>{finding.validation}</p></section><section><h3>Root cause</h3><p>{finding.root_cause}</p></section><section><h3>Affected component</h3><p className="mono">{finding.endpoint}</p>{finding.sources.map(s => <p className="mono" key={s.file}>{s.file}:{s.line}</p>)}</section><section><h3>Reproduction conditions</h3>{finding.conditions.map(c => <p key={c}>• {c}</p>)}</section><section><h3>Expected secure behavior</h3><p>{finding.expected}</p></section><section><h3>Suggested remediation</h3><p>{finding.remediation}</p></section></div></section><section className="panel"><div className="panel-heading"><h2>Sanitized execution evidence</h2><span className="badge">{finding.evidence.length} REQUESTS</span></div><div className="panel-body">{finding.evidence.length ? finding.evidence.map((e, i) => <section key={i}><div className="row space"><span className="mono">GET {e.path}</span><Badge value={String(e.status)} /></div><p className="small muted" style={{ marginTop: 8 }}>Identity: {e.identity}</p><pre>{JSON.stringify(e, null, 2)}</pre></section>) : <p className="muted">This hypothesis has no runtime evidence.</p>}</div></section></div>
        {finding.browser && <section className="panel"><div className="panel-heading"><h2>Browser authorization evidence</h2><Badge value={finding.browser.status} /></div><div className="panel-body"><p>{finding.browser.validation} · {finding.browser.verdict}</p>{finding.browser.artifact_id && <a href={`/api/v1/browser-evidence/${finding.browser.artifact_id}`} target="_blank" rel="noreferrer">View sanitized demo UI screenshot</a>}<pre>{JSON.stringify(finding.browser, null, 2)}</pre></div></section>}<section className="panel"><div className="panel-heading"><h2>Patch proposal & regression verification</h2><Button disabled={busy || !confirmedStates.includes(finding.state)} onClick={() => act(async () => { await api(`findings/${finding.id}/propose-fix`, 'POST'); })}><Wrench size={14} />{busy ? 'Verifying…' : 'Propose & verify fix'}</Button></div><div className="panel-body">{patchQuery.data ? <><div className={`notice ${patchQuery.data.verification.passed ? '' : 'error'}`}><strong>{patchQuery.data.verification.passed ? 'Regression passed · awaiting developer review' : 'Patch is unverified'}</strong><p>{patchQuery.data.verification.validation} · {patchQuery.data.verification.test_count} checks</p></div><pre>{patchQuery.data.diff}</pre>{patchQuery.data.verification.browser && <><h3>Browser regression evidence</h3><pre>{JSON.stringify(patchQuery.data.verification.browser, null, 2)}</pre></>}<h3>Generated regression plan</h3><pre>{JSON.stringify(patchQuery.data.regression_plan, null, 2)}</pre></> : <p className="muted small">Verified patch generation supports the shipped demo&apos;s ownership, authentication, and sensitive-field defects. Proposed patches live in a separate Git worktree and always require developer review.</p>}</div></section></>}

      {view === 'Settings' && settingsQuery.data && <SettingsForm configuration={settingsQuery.data} busy={busy} save={values => act(async () => { await api('settings', 'PATCH', values); })} />}
      <div className="footer-note"><Shield size={12} />Explicit scope · Bounded testing · Redacted evidence · No automatic merges</div>
      </div>
    </main>
  </div>;
}

function SettingsForm({ configuration, busy, save }: { configuration: Configuration; busy: boolean; save: (values: unknown) => Promise<boolean> }) {
  const [url, setUrl] = useState(configuration.targets[0]?.url || 'http://127.0.0.1:3001');
  const [authorized, setAuthorized] = useState(configuration.targets[0]?.authorized || false);
  const [approved, setApproved] = useState(configuration.targets[0]?.approved || false);
  const [loopback, setLoopback] = useState(configuration.targets[0]?.allow_loopback || false);
  const [fixtures, setFixtures] = useState(!!configuration.fixture);
  const [budget, setBudget] = useState(configuration.request_budget);
  const [timeout, setTimeoutValue] = useState(configuration.timeout_seconds);
  const [llm, setLlm] = useState(configuration.llm_enabled);
  const [model, setModel] = useState(configuration.llm_model);
  const [baseUrl, setBaseUrl] = useState(configuration.llm_base_url || '');
  const [saved, setSaved] = useState(false);
  return <form className="stack" onSubmit={async e => { e.preventDefault(); setSaved(false); const success = await save({ targets: url.trim() ? [{ url: url.trim(), authorized, approved, allow_loopback: loopback }, ...configuration.targets.filter(t => t.url.replace(/\/$/, '') !== url.trim().replace(/\/$/, ''))] : configuration.targets, request_budget: budget, timeout_seconds: timeout, sandbox_mode: authorized && approved ? 'trusted-local' : 'static-only', fixture: fixtures ? { endpoint: '/api/records/alice-record', owner_token: 'demo-alice', other_token: 'demo-bob' } : null, llm_enabled: llm, llm_model: model, llm_base_url: baseUrl.trim() || null }); setSaved(success); }}>
    <div className="notice">Docker Compose is for trusted development. Arbitrary untrusted repositories need VM-grade isolation; this version does not execute them.</div>
    <section className="panel"><div className="panel-heading"><h2>Target scope & execution approval</h2><LockKeyhole size={16} color="#65ded7" /></div><div className="panel-body stack"><label>Exact HTTP(S) origin<input type="url" value={url} onChange={e => { setUrl(e.target.value); setAuthorized(false); setApproved(false); }} placeholder="http://127.0.0.1:3001" /></label><label className="checkbox"><input type="checkbox" checked={authorized} onChange={e => setAuthorized(e.target.checked)} />I am authorized to test this application and its synthetic data.</label><label className="checkbox"><input type="checkbox" checked={approved} onChange={e => setApproved(e.target.checked)} />I approve bounded execution against this trusted target, including fixed synthetic demo login/logout when browser validation is selected.</label><label className="checkbox"><input type="checkbox" checked={loopback} onChange={e => setLoopback(e.target.checked)} />Allow this exact target to resolve to loopback. Other private destinations remain denied.</label><label className="checkbox"><input type="checkbox" checked={fixtures} onChange={e => setFixtures(e.target.checked)} />Use the shipped disposable demo&apos;s Alice/Bob synthetic identities and seeded record.</label><p className="muted small">Fixture tokens are synthetic. Configure custom fixture identities through the authenticated API or local database configuration. Never use production credentials.</p><p className="mono muted">{configuration.targets.length} saved target(s) · current mode: {configuration.sandbox_mode}</p></div></section>
    <section className="panel"><div className="panel-heading"><h2>Execution budgets</h2></div><div className="panel-body formgrid"><label>Maximum requests per scan<input type="number" min={1} max={200} value={budget} onChange={e => setBudget(Number(e.target.value))} /></label><label>Request timeout (seconds)<input type="number" min={0.1} max={30} step={0.1} value={timeout} onChange={e => setTimeoutValue(Number(e.target.value))} /></label></div></section>
    <section className="panel"><div className="panel-heading"><h2>Optional AI prioritization</h2><Terminal size={16} className="muted" /></div><div className="panel-body stack"><label className="checkbox"><input type="checkbox" checked={llm} onChange={e => setLlm(e.target.checked)} />Use a provider to prioritize existing typed hypotheses. Policy remains authoritative.</label><div className="formgrid"><label>Provider / model<input value={model} onChange={e => setModel(e.target.value)} placeholder="anthropic/claude-sonnet-4-5" /></label><label>Compatible endpoint (optional)<input value={baseUrl} onChange={e => setBaseUrl(e.target.value)} placeholder="http://127.0.0.1:11434" /></label></div><p className="muted small">API key: {configuration.llm_key_configured ? 'configured on the server' : 'not configured'}. Set SHADOWLAB_LLM_API_KEY in the server environment. Keys are never sent to the browser or stored through this form. The default rule-based workflow needs no AI key.</p></div></section>
    <div className="row"><Button type="submit" disabled={busy}><CheckCircle2 size={14} />Save configuration</Button>{saved && <span className="muted small" role="status">Configuration saved.</span>}</div>
  </form>;
}
