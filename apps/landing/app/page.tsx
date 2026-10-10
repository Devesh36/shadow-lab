'use client';

import Link from 'next/link';
import { useState } from 'react';
import { ArrowRight, Check, Clipboard, Code2, Fingerprint, GitPullRequest, Shield, Terminal } from 'lucide-react';

const installs = {
  uv: 'uv tool install --python 3.12 "git+https://github.com/Devesh36/shadow-lab.git@main"\nshadow repl',
  Homebrew: 'brew tap devesh36/shadowlab https://github.com/Devesh36/shadow-lab.git\nbrew install --HEAD devesh36/shadowlab/shadowlab\nshadow repl',
};

export default function Landing() {
  const [installer, setInstaller] = useState<'uv' | 'Homebrew'>('uv');
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  async function copy() {
    try { await navigator.clipboard.writeText(installs[installer]); setCopied(true); setCopyError(false); }
    catch { setCopyError(true); }
  }
  return <div className="landing">
    <header className="landing-nav">
      <Link href="/" className="landing-brand"><Shield size={25} /> ShadowLab <span>V1</span></Link>
      <nav aria-label="Main navigation"><a href="#how-it-works">How it works</a><a href="#install">Install</a><Link href="/docs/">Docs</Link><a href="https://github.com/Devesh36/shadow-lab">GitHub ↗</a><a className="landing-nav-cta" href="#install">Get ShadowLab <ArrowRight size={14} /></a></nav>
    </header>
    <main>
      <section className="landing-hero">
        <div className="landing-hero-copy">
          <div className="landing-kicker"><span /> YOUR LOCAL SECURITY WORKSPACE</div>
          <h1>Find the bug.<br />Prove the impact.<br /><em>Review the fix.</em></h1>
          <p>Turn application security questions into investigations you can inspect. ShadowLab connects source analysis, scoped tests, and evidence — with you in control of every fix.</p>
          <div className="landing-actions"><a className="landing-primary" href="#install">Run the demo locally <ArrowRight size={17} /></a><a className="landing-secondary" href="#install"><Terminal size={17} /> Install ShadowLab</a></div>
          <div className="landing-footnote">Open source · Local first · No LLM key required for the demo</div>
        </div>
        <div className="landing-terminal" aria-label="Illustrative demo console">
          <div className="terminal-bar"><div><i /><i /><i /></div><span>shadow repl</span><span>ILLUSTRATION</span></div>
          <div className="terminal-body"><p><span className="terminal-prompt">$</span> shadow repl</p><p className="terminal-bright">ShadowLab</p><p className="terminal-muted">1 Demo &nbsp; 2 Check setup &nbsp; help &nbsp; quit</p><p><span className="terminal-prompt">shadow&gt;</span> demo</p><div className="terminal-separator" /><p className="terminal-muted">source → hypotheses → bounded tests</p><p><span className="terminal-verdict">CONFIRMED</span> Missing authentication</p><p><span className="terminal-verdict">CONFIRMED</span> Broken object authorization</p><p><span className="terminal-verdict">CONFIRMED</span> Sensitive response fields</p><div className="terminal-separator" /><p className="terminal-muted">Runtime evidence. Sanitized report. Reviewable diff.</p><p><span className="terminal-prompt">shadow&gt;</span> <span className="terminal-cursor">▌</span></p></div>
          <div className="terminal-caption"><Fingerprint size={15} /> Synthetic accounts. Disposable demo. Real checks.</div>
        </div>
      </section>
      <div className="landing-divider"><span>FROM A SUSPICION TO SOMETHING YOU CAN VERIFY</span></div>
      <section id="how-it-works" className="landing-section">
        <div className="landing-section-heading"><div><span className="landing-kicker">AN INVESTIGATION, WITH A PAPER TRAIL</span><h2>Evidence at every step.</h2></div><p>A hypothesis is a starting point. A finding needs a reproduced result. A fix needs a regression check and your review.</p></div>
        <div className="landing-cards">
          <article><span className="landing-step">01 / UNDERSTAND</span><Code2 size={27} /><h3>Read the application</h3><p>Discover Next.js routes and source locations. Combine local Semgrep results with bounded, inspectable hypotheses.</p></article>
          <article><span className="landing-step">02 / VERIFY</span><Fingerprint size={27} /><h3>Test the actual behavior</h3><p>The trusted demo checks authentication, ownership and response exposure. Optional browser validation uses separate anonymous, Alice and Bob sessions.</p></article>
          <article><span className="landing-step">03 / REVIEW</span><GitPullRequest size={27} /><h3>Check the fix</h3><p>Approve a disposable demo patch, repeat the original test, and check owner access still works. Inspect the diff before deciding what comes next.</p></article>
        </div>
      </section>
      <section id="install" className="landing-install landing-section">
        <div><span className="landing-kicker">ONE CONSOLE. A GUIDED START.</span><h2>Your first investigation<br />starts with <code>demo</code>.</h2><p>Install the CLI, open the REPL, then choose Demo. It prepares the bundled apps, runs an investigation, and opens your local workspace.</p><p className="landing-prerequisites">macOS or Linux · Python 3.12+ · Node.js 22+ and npm · Git<br />uv installs Python when needed. Homebrew installs the runtime dependencies. The first demo needs internet access to install locked Node packages.</p></div>
        <div className="install-box"><div className="install-tabs" role="tablist" aria-label="Installer">{(['uv', 'Homebrew'] as const).map(name => <button id={`tab-${name}`} aria-controls="install-command" role="tab" aria-selected={installer === name} key={name} onClick={() => { setInstaller(name); setCopied(false); setCopyError(false); }}>{name}</button>)}<button className="copy-install" aria-label="Copy install commands" onClick={copy}>{copied ? <Check size={16} /> : <Clipboard size={16} />}</button></div><pre id="install-command" role="tabpanel" aria-labelledby={`tab-${installer}`}><code>{installs[installer]}</code></pre><p aria-live="polite">{copyError ? 'Copy unavailable. Select the commands above to copy them manually.' : copied ? 'Commands copied.' : installer === 'Homebrew' ? 'Custom tap · HEAD install from the main branch' : 'Install with uv from GitHub · no PyPI release required'}</p><Link href="/docs/">Read setup instructions <ArrowRight size={14} /></Link></div>
      </section>
      <section className="landing-scope"><Shield size={23} /><div><h3>A focused V1 you can inspect.</h3><p>Verified automatic fixes and browser identity scenarios currently cover the shipped synthetic demo. Other repositories support static analysis; arbitrary untrusted code execution stays disabled. Reports distinguish confirmed findings, incomplete coverage, and failed checks.</p></div><a href="#install">Run it locally <ArrowRight size={16} /></a></section>
    </main>
    <footer className="landing-footer"><Link href="/" className="landing-brand"><Shield size={20} /> ShadowLab</Link><span>Application security, with evidence.</span><a href="https://github.com/Devesh36/shadow-lab/blob/main/LICENSE">MIT licensed ↗</a></footer>
  </div>;
}
