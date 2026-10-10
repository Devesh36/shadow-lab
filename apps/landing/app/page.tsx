'use client';

import Link from 'next/link';
import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import {
  ArrowDown,
  ArrowRight,
  BookOpen,
  Check,
  CheckCheck,
  ChevronRight,
  Clipboard,
  Code2,
  FileCode2,
  Fingerprint,
  GitBranch,
  GitPullRequest,
  Github,
  LockKeyhole,
  Pause,
  Play,
  RotateCcw,
  Shield,
  Sparkles,
  Terminal,
  X,
} from 'lucide-react';
import './marketing.css';

const installs = {
  uv: 'uv tool install --python 3.12 "git+https://github.com/Devesh36/shadow-lab.git@main"\nshadow repl',
  Homebrew:
    'brew tap devesh36/shadowlab https://github.com/Devesh36/shadow-lab.git\nbrew install --HEAD devesh36/shadowlab/shadowlab\nshadow repl',
};
const previews = ['Source', 'Validate', 'Review'] as const;
const installers = ['uv', 'Homebrew'] as const;
type Preview = (typeof previews)[number];

function changeTab<T extends string>(
  event: KeyboardEvent<HTMLButtonElement>,
  options: readonly T[],
  active: T,
  select: (value: T) => void,
  prefix: string,
) {
  let index = options.indexOf(active);
  if (event.key === 'ArrowRight') index = (index + 1) % options.length;
  else if (event.key === 'ArrowLeft')
    index = (index + options.length - 1) % options.length;
  else if (event.key === 'Home') index = 0;
  else if (event.key === 'End') index = options.length - 1;
  else return;
  event.preventDefault();
  select(options[index]);
  document.getElementById(`${prefix}-${options[index]}`)?.focus();
}

export default function Landing() {
  const [installer, setInstaller] = useState<(typeof installers)[number]>('uv');
  const [preview, setPreview] = useState<Preview>('Validate');
  const [replay, setReplay] = useState(0);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const [paused, setPaused] = useState(false);
  const [motionReady, setMotionReady] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!('IntersectionObserver' in window)) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            (entry.target as HTMLElement).dataset.revealed = 'true';
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08 },
    );
    root.current
      ?.querySelectorAll('[data-reveal]')
      .forEach((element) => observer.observe(element));
    setMotionReady(true);
    return () => observer.disconnect();
  }, []);

  async function copy() {
    try {
      await navigator.clipboard.writeText(installs[installer]);
      setCopied(true);
      setCopyError(false);
    } catch {
      setCopyError(true);
    }
  }
  function selectInstaller(value: (typeof installers)[number]) {
    setInstaller(value);
    setCopied(false);
    setCopyError(false);
  }

  return (
    <div
      ref={root}
      className={`marketing${motionReady ? ' motion-ready' : ''}${paused ? ' motion-paused' : ''}`}
    >
      <a className="m-skip" href="#main">
        Skip to content
      </a>
      <header className="m-header">
        <div className="m-header-inner">
          <Link href="/" className="m-brand">
            <span className="m-brand-icon">
              <Shield size={23} strokeWidth={2} />
            </span>
            ShadowLab<span className="m-version">V1</span>
          </Link>
          <nav aria-label="Main navigation">
            <a className="m-nav-simple" href="#how-it-works">
              How it works
            </a>
            <Link className="m-nav-docs" href="/docs/">
              <BookOpen size={15} /> Docs <ArrowRight size={13} />
            </Link>
            <a
              className="m-nav-github"
              href="https://github.com/Devesh36/shadow-lab"
              aria-label="GitHub repository"
            >
              <Github size={18} />
            </a>
            <a
              className="m-nav-install"
              href="#install"
              aria-label="Get ShadowLab"
            >
              <span className="m-wide-label">Get ShadowLab</span>
              <span className="m-short-label" aria-hidden="true">
                Install
              </span>
              <ArrowRight size={15} />
            </a>
          </nav>
        </div>
      </header>
      <main id="main">
        <section className="m-hero m-container" aria-labelledby="hero-title">
          <div className="m-hero-copy">
            <div className="m-eyebrow m-intro">
              <span className="m-status-dot" /> SECURITY THAT SHOWS ITS WORK
            </div>
            <h1 id="hero-title">
              <span>Find the bug.</span>
              <span>
                Keep the{' '}
                <em>
                  proof.
                  <svg viewBox="0 0 330 20" aria-hidden="true">
                    <path d="M4 14C82 2 220 2 325 10" />
                  </svg>
                </em>
              </span>
            </h1>
            <p className="m-hero-description">
              From a suspicious line of code to evidence you can inspect.
              Investigate the behavior, check the impact, and review the fix —
              right on your machine.
            </p>
            <div className="m-hero-actions">
              <a className="m-button m-button-dark" href="#install">
                Run the demo locally <ArrowRight size={18} />
              </a>
              <Link className="m-button m-button-outline" href="/docs/">
                <BookOpen size={18} /> Read the docs
              </Link>
            </div>
            <div className="m-hero-notes">
              <span>
                <Check size={14} /> Open source
              </span>
              <span>
                <Check size={14} /> Local first
              </span>
              <span>
                <Check size={14} /> No LLM key needed
              </span>
            </div>
            <a className="m-scroll-hint" href="#how-it-works">
              <span>
                <ArrowDown size={15} />
              </span>{' '}
              Follow the evidence
            </a>
          </div>
          <div className="m-hero-art">
            <div className="m-orbit m-orbit-one" aria-hidden="true" />
            <div className="m-orbit m-orbit-two" aria-hidden="true" />
            <div className="m-floating-label m-floating-top">
              <span>
                <Shield size={15} />
              </span>{' '}
              YOUR CODE. YOUR CONTROL.
            </div>
            <div className="m-workbench">
              <div className="m-workbench-title">
                <span className="m-window-dots" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </span>
                <span>
                  <Terminal size={13} /> shadow repl
                </span>
                <span className="m-preview-badge">ILLUSTRATION</span>
              </div>
              <div className="m-workbench-heading">
                <div>
                  <span className="m-console-eyebrow">THE INVESTIGATION</span>
                  <h2>Proof, before patch.</h2>
                </div>
                <span className="m-local-badge">
                  <span /> Local demo
                </span>
              </div>
              <div
                className="m-preview-tabs"
                role="tablist"
                aria-label="Demo preview"
              >
                {previews.map((name, i) => (
                  <button
                    key={name}
                    id={`preview-tab-${name}`}
                    role="tab"
                    aria-selected={preview === name}
                    aria-controls="preview-panel"
                    tabIndex={preview === name ? 0 : -1}
                    onClick={() => setPreview(name)}
                    onKeyDown={(event) =>
                      changeTab(
                        event,
                        previews,
                        preview,
                        setPreview,
                        'preview-tab',
                      )
                    }
                  >
                    <span aria-hidden="true">0{i + 1}</span>
                    {name}
                  </button>
                ))}
              </div>
              <div
                id="preview-panel"
                role="tabpanel"
                aria-labelledby={`preview-tab-${preview}`}
                className="m-preview-panel"
              >
                <div className="m-panel-content" key={`${preview}-${replay}`}>
                  {preview === 'Source' && (
                    <>
                      <div className="m-panel-label">
                        <FileCode2 size={14} />
                        <span>app/api/records/[id]/route.ts</span>
                      </div>
                      <pre className="m-source-code">
                        <code>
                          <span className="m-code-comment">
                            {'// Simplified illustration of a demo route\n'}
                          </span>
                          {
                            'export async function GET(request) {\n  const user = await authenticate(request);\n  const record = await findRecord(id);\n'
                          }
                          <span className="m-code-highlight">
                            {'  return Response.json(record);'}
                          </span>
                          {'\n}'}
                        </code>
                      </pre>
                      <div className="m-source-note">
                        <span className="m-warning-dot" />
                        <div>
                          <strong>Who owns this record?</strong>
                          <p>
                            Authentication alone does not verify ownership. This
                            is a hypothesis until the behavior is tested.
                          </p>
                        </div>
                      </div>
                    </>
                  )}
                  {preview === 'Validate' && (
                    <>
                      <div className="m-command-line">
                        <span>$</span>
                        <code className="m-typed-command">shadow repl</code>
                        <span className="m-terminal-caret" aria-hidden="true" />
                      </div>
                      <div className="m-case-heading">
                        <span>
                          <Fingerprint size={16} /> Object authorization
                        </span>
                        <span className="m-confirmed">CONFIRMED</span>
                      </div>
                      <div className="m-identity-flow">
                        <span className="m-avatar">B</span>
                        <div>
                          <strong>Bob</strong>
                          <span>Different user</span>
                        </div>
                        <span className="m-flow-track" aria-hidden="true">
                          <i />
                          <ArrowRight size={16} />
                        </span>
                        <span className="m-record-icon">
                          <LockKeyhole size={19} />
                        </span>
                        <div>
                          <strong>Alice&apos;s record</strong>
                          <span>/api/records/alice-record</span>
                        </div>
                      </div>
                      <div className="m-check-list">
                        <div className="m-result m-result-one">
                          <span>
                            <Check size={13} /> Owner reads own record
                          </span>
                          <b className="m-status-ok">200 OK</b>
                        </div>
                        <div className="m-result m-result-two">
                          <span>
                            <X size={13} /> Bob reads Alice&apos;s record
                          </span>
                          <b className="m-status-alert">200 EXPOSED</b>
                        </div>
                        <div className="m-result m-result-three">
                          <span>
                            <Check size={13} /> Anonymous access blocked
                          </span>
                          <b className="m-status-ok">401 DENIED</b>
                        </div>
                      </div>
                      <div className="m-evidence-tag">
                        <Fingerprint size={13} /> Same record. Separate
                        identities. Inspectable evidence.
                      </div>
                    </>
                  )}
                  {preview === 'Review' && (
                    <>
                      <div className="m-panel-label">
                        <GitPullRequest size={15} />
                        <span>Disposable demo patch</span>
                        <span className="m-review-badge">YOUR APPROVAL</span>
                      </div>
                      <div className="m-diff">
                        <code>
                          <span className="m-diff-context">
                            {' '}
                            const record = await findRecord(id);
                          </span>
                          <span className="m-diff-added">
                            + if (record.ownerId !== user.id) {'{'}
                          </span>
                          <span className="m-diff-added">
                            + return denied(403);
                          </span>
                          <span className="m-diff-added">+ {'}'}</span>
                          <span className="m-diff-context">
                            {' '}
                            return Response.json(record);
                          </span>
                        </code>
                      </div>
                      <div className="m-patch-results">
                        <span>
                          <Check size={14} /> Owner access preserved <b>200</b>
                        </span>
                        <span>
                          <Check size={14} /> Cross-user access blocked{' '}
                          <b>403</b>
                        </span>
                      </div>
                      <div className="m-awaiting">
                        <GitPullRequest size={14} /> Verification passed.
                        Awaiting your review.
                      </div>
                    </>
                  )}
                </div>
              </div>
              <div className="m-workbench-footer">
                <span>
                  <span /> Synthetic accounts only
                </span>
                <button
                  onClick={() => setReplay((value) => value + 1)}
                  aria-label="Replay demo preview"
                >
                  <RotateCcw size={13} /> Replay
                </button>
              </div>
            </div>
            <div className="m-floating-label m-floating-bottom">
              <span>
                <CheckCheck size={18} />
              </span>
              <div>
                <strong>Evidence you can inspect</strong>
                <small>Every finding has a paper trail.</small>
              </div>
            </div>
            <div className="m-preview-caption">
              <Link href="/docs/#screenshots">
                See the real terminal walkthrough <ArrowRight size={13} />
              </Link>
              <button
                className="m-motion-toggle"
                aria-pressed={paused}
                onClick={() => setPaused((value) => !value)}
                aria-label={paused ? 'Resume animations' : 'Pause animations'}
              >
                {paused ? <Play size={12} /> : <Pause size={12} />}{' '}
                {paused ? 'Resume' : 'Pause'}
              </button>
            </div>
          </div>
        </section>

        <div className="m-principles m-container">
          <span>BUILT FOR A QUESTIONING MIND.</span>
          <div>
            <span>
              <Code2 size={18} /> Read the source
            </span>
            <span>
              <Fingerprint size={18} /> Reproduce the behavior
            </span>
            <span>
              <GitPullRequest size={18} /> Review the change
            </span>
          </div>
        </div>

        <section
          id="how-it-works"
          className="m-workflow m-container"
          aria-labelledby="workflow-title"
        >
          <div className="m-section-heading" data-reveal>
            <div>
              <span className="m-eyebrow">01 / THE WORKFLOW</span>
              <h2 id="workflow-title">
                A finding should come
                <br />
                with <em>receipts.</em>
              </h2>
            </div>
            <p>
              Less guessing. More checking. Follow an investigation from the
              first source signal to a fix you can review.
            </p>
          </div>
          <div className="m-workflow-grid">
            <article className="m-workflow-card m-source-card" data-reveal>
              <div className="m-card-top">
                <span>01 / UNDERSTAND</span>
                <Code2 size={21} />
              </div>
              <div className="m-mini-source" aria-hidden="true">
                <span>
                  <FileCode2 size={14} /> route.ts
                </span>
                <i />
                <i />
                <i />
                <b>
                  <span /> source signal
                </b>
              </div>
              <h3>Start with the source.</h3>
              <p>
                Discover Next.js routes and source locations. Build inspectable
                hypotheses from local analysis and available Semgrep results.
              </p>
              <span className="m-card-bottom">
                SOURCE → HYPOTHESIS <ChevronRight size={15} />
              </span>
            </article>
            <article className="m-workflow-card m-validate-card" data-reveal>
              <div className="m-card-top">
                <span>02 / REPRODUCE</span>
                <Fingerprint size={21} />
              </div>
              <div className="m-mini-identities" aria-hidden="true">
                <span>
                  A<small>Alice</small>
                </span>
                <i />
                <span>
                  B<small>Bob</small>
                </span>
                <i />
                <span>
                  ?<small>Anon</small>
                </span>
                <b>
                  <Check size={12} /> isolated sessions
                </b>
              </div>
              <h3>Test the actual behavior.</h3>
              <p>
                The trusted demo checks authentication, ownership and sensitive
                responses. Browser validation separates anonymous, Alice and Bob
                sessions.
              </p>
              <span className="m-card-bottom">
                HYPOTHESIS → EVIDENCE <ChevronRight size={15} />
              </span>
            </article>
            <article className="m-workflow-card m-review-card" data-reveal>
              <div className="m-card-top">
                <span>03 / VERIFY</span>
                <GitPullRequest size={21} />
              </div>
              <div className="m-mini-patch" aria-hidden="true">
                <span>
                  <GitBranch size={14} /> disposable patch
                </span>
                <i>− missing ownership check</i>
                <b>+ explicit owner check</b>
                <small>
                  <CheckCheck size={12} /> regression verified
                </small>
              </div>
              <h3>Make the fix earn trust.</h3>
              <p>
                Approve a demo patch experiment, repeat the original test, and
                check normal owner access still works. Then review the diff.
              </p>
              <span className="m-card-bottom">
                EVIDENCE → REVIEW <ChevronRight size={15} />
              </span>
            </article>
          </div>
        </section>

        <section
          className="m-guide m-container"
          data-reveal
          aria-labelledby="guide-title"
        >
          <div className="m-guide-symbol" aria-hidden="true">
            <BookOpen size={58} strokeWidth={1.3} />
            <span className="m-guide-star">
              <Sparkles size={22} />
            </span>
          </div>
          <div className="m-guide-copy">
            <span className="m-eyebrow">THE FIELD GUIDE</span>
            <h2 id="guide-title">Your first finding starts here.</h2>
            <p>
              Installation, the guided demo, your own project, and real terminal
              screenshots. Every step in one place.
            </p>
            <div>
              <Link className="m-button m-button-dark" href="/docs/">
                Explore the docs <ArrowRight size={16} />
              </Link>
              <Link className="m-guide-text-link" href="/docs/#screenshots">
                View terminal screenshots <ArrowRight size={15} />
              </Link>
            </div>
          </div>
          <span className="m-guide-index" aria-hidden="true">
            READ.
            <br />
            RUN.
            <br />
            REVIEW.
          </span>
        </section>

        <section
          id="install"
          className="m-install m-container"
          aria-labelledby="install-title"
        >
          <div className="m-install-copy" data-reveal>
            <span className="m-eyebrow">02 / TAKE IT FOR A SPIN</span>
            <h2 id="install-title">
              One command.
              <br />A real investigation.
            </h2>
            <p>
              Open the console. Choose <code>demo</code>. ShadowLab prepares a
              disposable local app and takes you from source to evidence.
            </p>
            <div className="m-install-prerequisites">
              <span>
                <Terminal size={16} /> macOS or Linux
              </span>
              <span>Python 3.12+ · Node.js 22+ · npm · Git</span>
            </div>
            <p className="m-install-detail">
              uv can install Python; Homebrew installs the runtime dependencies.
              The first demo needs internet access for locked Node packages.
            </p>
          </div>
          <div className="m-install-box" data-reveal>
            <div className="m-install-box-title">
              <Terminal size={15} />
              <span>YOUR TERMINAL</span>
              <span>LOCAL FIRST</span>
            </div>
            <div
              className="m-installer-tabs"
              role="tablist"
              aria-label="Installer"
            >
              {installers.map((name) => (
                <button
                  key={name}
                  id={`installer-tab-${name}`}
                  aria-controls="install-command"
                  role="tab"
                  aria-selected={installer === name}
                  tabIndex={installer === name ? 0 : -1}
                  onClick={() => selectInstaller(name)}
                  onKeyDown={(event) =>
                    changeTab(
                      event,
                      installers,
                      installer,
                      selectInstaller,
                      'installer-tab',
                    )
                  }
                >
                  {name}
                </button>
              ))}
              <button
                className="m-copy-install"
                aria-label="Copy install commands"
                onClick={copy}
              >
                {copied ? <Check size={16} /> : <Clipboard size={16} />}
              </button>
            </div>
            <pre
              id="install-command"
              role="tabpanel"
              aria-labelledby={`installer-tab-${installer}`}
            >
              <code>{installs[installer]}</code>
            </pre>
            <p className="m-install-feedback" aria-live="polite">
              {copyError
                ? 'Copy unavailable. Select the commands above to copy them manually.'
                : copied
                  ? 'Commands copied.'
                  : installer === 'Homebrew'
                    ? 'Custom tap · HEAD install from the main branch'
                    : 'Install from GitHub main · no PyPI release required'}
            </p>
            <div className="m-install-next">
              <span>
                <span>THEN TYPE</span>
                <code>
                  shadow&gt; demo
                  <span className="m-terminal-caret" aria-hidden="true" />
                </code>
              </span>
              <Link href="/docs/">
                Read setup instructions <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </section>

        <section className="m-scope m-container" data-reveal>
          <div className="m-scope-icon">
            <Shield size={25} />
          </div>
          <div>
            <h2>A focused V1. Clear boundaries.</h2>
            <p>
              Browser identity scenarios and verified patches cover the shipped
              synthetic demo. Your other repositories support source analysis.
              Reports distinguish confirmed findings, incomplete coverage, and
              failed checks.
            </p>
          </div>
          <Link href="/docs/#project">
            Understand the scope <ArrowRight size={15} />
          </Link>
        </section>
      </main>
      <footer className="m-footer m-container">
        <div>
          <Link href="/" className="m-brand">
            <span className="m-brand-icon">
              <Shield size={21} />
            </span>
            ShadowLab
          </Link>
          <p>Good security work leaves evidence.</p>
        </div>
        <nav aria-label="Footer navigation">
          <Link href="/docs/">Documentation</Link>
          <a href="https://github.com/Devesh36/shadow-lab">
            GitHub <ArrowRight size={13} />
          </a>
          <a href="https://github.com/Devesh36/shadow-lab/blob/main/LICENSE">
            MIT license
          </a>
        </nav>
        <span className="m-footer-note">
          <span /> Built to run on your machine.
        </span>
      </footer>
    </div>
  );
}
