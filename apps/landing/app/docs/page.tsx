import type { Metadata } from 'next';
import Link from 'next/link';
import Image from 'next/image';
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Shield,
  Terminal,
} from 'lucide-react';
import Command from './command';
import captures from '../../public/docs/terminal/manifest.json';

export const metadata: Metadata = {
  title: 'ShadowLab docs · Install, demo & project guide',
  description:
    'Install ShadowLab with uv or Homebrew, run the guided terminal demo, review a fix, and analyze your Next.js project. Includes real terminal recordings.',
};

const sections = [
  ['requirements', 'Before you start'],
  ['install', 'Install ShadowLab'],
  ['demo', 'Run your first demo'],
  ['review', 'Findings, fixes & reports'],
  ['browser', 'Browser validation'],
  ['project', 'Use it in your project'],
  ['commands', 'Command reference'],
  ['screenshots', 'Terminal screenshots'],
  ['troubleshooting', 'Troubleshooting'],
];

export default function Docs() {
  return (
    <div className="landing docs">
      <header className="landing-nav">
        <Link href="/" className="landing-brand">
          <Shield size={25} /> ShadowLab <span>V1</span>
        </Link>
        <nav aria-label="Main navigation">
          <Link href="/">Home</Link>
          <Link href="/docs/" aria-current="page">
            Docs
          </Link>
          <a href="https://github.com/Devesh36/shadow-lab">GitHub ↗</a>
          <a className="landing-nav-cta" href="#install">
            Install <ArrowRight size={14} />
          </a>
        </nav>
      </header>
      <div className="docs-layout">
        <aside className="docs-sidebar">
          <span className="landing-kicker">
            <BookOpen size={14} /> DOCUMENTATION
          </span>
          <nav aria-label="On this page">
            {sections.map(([id, title]) => (
              <a key={id} href={`#${id}`}>
                {title}
              </a>
            ))}
          </nav>
          <Link className="docs-back" href="/">
            <ArrowLeft size={14} /> Back to overview
          </Link>
        </aside>
        <main className="docs-content">
          <div className="docs-intro">
            <span className="landing-kicker">
              <Terminal size={15} /> FROM YOUR TERMINAL
            </span>
            <h1>
              Run ShadowLab
              <br />
              <em>on your machine.</em>
            </h1>
            <p>
              Install the CLI, choose the guided demo, and follow an
              investigation from finding to reviewed fix. Then use source
              analysis in your own Next.js project.
            </p>
            <div className="docs-meta">
              Local first · No LLM key needed · Real terminal screenshots below
            </div>
          </div>

          <section id="requirements">
            <span className="docs-step">01 / PREPARE</span>
            <h2>Before you start</h2>
            <p>
              Use macOS or Linux with Git, Node.js 22 or newer, and npm.
              ShadowLab requires Python 3.12 or newer; uv can install it for
              you, and the Homebrew formula declares the runtime dependencies.
              On Windows, use a Linux environment such as WSL; the guided
              launcher requires POSIX.
            </p>
            <Command label="Check your tools">
              {'node --version\nnpm --version\ngit --version'}
            </Command>
            <p>
              The first demo downloads locked Node packages and builds the
              bundled apps. Allow a few minutes and internet access for
              installation. No account, LLM provider key, Docker setup, or
              hosted backend is needed for the guided demo.
            </p>
          </section>

          <section id="install">
            <span className="docs-step">02 / INSTALL</span>
            <h2>Install ShadowLab</h2>
            <h3>With uv</h3>
            <p>
              Install{' '}
              <a href="https://docs.astral.sh/uv/getting-started/installation/">
                uv
              </a>
              , then run:
            </p>
            <Command label="uv installation">
              {
                'uv tool install --python 3.12 "git+https://github.com/Devesh36/shadow-lab.git@main"\nshadow repl'
              }
            </Command>
            <p>
              If <code>shadow</code> is missing from your PATH, run{' '}
              <code>uv tool update-shell</code> and reopen your terminal. You
              can also use <code>shadow Repl</code>; both spellings open the
              same console.
            </p>
            <h3>With Homebrew</h3>
            <p>
              Use <a href="https://brew.sh/">Homebrew</a> and the
              repository&apos;s custom tap:
            </p>
            <Command label="Homebrew installation">
              {
                'brew tap devesh36/shadowlab https://github.com/Devesh36/shadow-lab.git\nbrew install --HEAD devesh36/shadowlab/shadowlab\nshadow repl'
              }
            </Command>
            <p>
              These commands install from the <code>main</code> branch. A PyPI
              package or Homebrew core release is not required. The terminal
              walkthrough below was captured using uv on Linux; it is not a
              macOS Homebrew recording.
            </p>
            <h3>Update an existing installation</h3>
            <Command label="Update with uv">
              {
                'uv tool install --reinstall --python 3.12 "git+https://github.com/Devesh36/shadow-lab.git@main"'
              }
            </Command>
            <Command label="Update with Homebrew">
              {'brew upgrade --fetch-HEAD devesh36/shadowlab/shadowlab'}
            </Command>
          </section>

          <section id="demo">
            <span className="docs-step">03 / INVESTIGATE</span>
            <h2>Run your first demo</h2>
            <p>
              From any directory, run <code>shadow repl</code>. You will see{' '}
              <code>1 Demo</code>, <code>2 Check setup</code>, <code>help</code>
              , and <code>quit</code>. Enter these commands at the{' '}
              <code>shadow&gt;</code> prompt, one at a time:
            </p>
            <Command label="REPL demo commands">{'doctor\nhelp\ndemo'}</Command>
            <p>
              Choosing <code>demo</code> authorizes bounded checks against the
              bundled synthetic local app. ShadowLab creates a private
              disposable workspace, starts its local services, and opens the
              investigation in your browser. If it does not open automatically,
              use the printed <code>http://127.0.0.1:PORT/app?scan=…</code> URL.
            </p>
            <div className="docs-note">
              <strong>Your project stays separate.</strong>
              <p>
                The REPL&apos;s Demo option always uses the reviewed bundled
                application, even when you launch it inside your project. Use
                the <a href="#project">project commands below</a> for your own
                source.
              </p>
            </div>
            <p>
              The demo checks missing authentication, object authorization,
              sensitive response fields, and response headers. A{' '}
              <code>CONFIRMED</code> result has runtime evidence.{' '}
              <code>INCONCLUSIVE</code> means more validation is needed; it does
              not mean the application is safe.
            </p>
          </section>

          <section id="review">
            <h2>Findings, fixes &amp; reports</h2>
            <p>After the demo finishes, use these REPL commands:</p>
            <Command label="Review commands">
              {'findings\nfix 1\nreport'}
            </Command>
            <p>
              <code>findings</code> lists the numbered results. Choose a
              supported authentication, object authorization, or sensitive-field
              finding and enter <code>fix NUMBER</code>. That command explicitly
              approves a patch experiment on a disposable demo copy. Patch
              verification repeats the checks and preserves normal authorized
              access.
            </p>
            <p>
              <strong>
                “Passed; awaiting review” still requires your review.
              </strong>{' '}
              Open the local workspace to inspect the diff and regression
              evidence. A failed or incomplete check must not be treated as a
              verified fix. The REPL does not apply these demo patches to your
              project.
            </p>
            <p>
              <code>report</code> saves a sanitized Markdown report and prints
              its path. Demo files live under{' '}
              <code>~/.local/share/shadowlab</code> by default, or the XDG data
              directory when configured. Set <code>SHADOWLAB_HOME</code> before
              starting to choose another location.
            </p>
            <p>
              Enter <code>stop</code> to stop the current demo and keep its
              evidence, or <code>quit</code> to close the console and stop its
              local services. Saved evidence remains on disk. Keep the run
              directory private; it also contains local operational logs and an
              API token.
            </p>
          </section>

          <section id="browser">
            <h2>Optional browser validation</h2>
            <p>
              The default demo does not require Chromium. For real UI checks,
              install the Chromium version matching the shipped Playwright
              dependency:
            </p>
            <Command label="Install browser">
              {'uvx --from playwright==1.63.0 playwright install chromium'}
            </Command>
            <p>
              Linux also needs Chromium&apos;s system libraries; follow{' '}
              <a href="https://playwright.dev/python/docs/browsers#install-system-dependencies">
                Playwright&apos;s system dependency instructions
              </a>
              . If you already have a compatible Chromium, set{' '}
              <code>SHADOWLAB_CHROMIUM_PATH</code> to its executable before
              launching <code>shadow repl</code>.
            </p>
            <Command label="Browser REPL commands">
              {'demo browser\nfindings\nreport'}
            </Command>
            <p>
              The browser run uses separate anonymous, Alice, and Bob contexts
              with synthetic identities and disposable records. It exercises the
              real UI and owner/cross-user controls. Inspect the browser
              verdicts and coverage in the local workspace or exported report.
              Missing Chromium, failures, timeouts, and unsupported setup remain
              incomplete coverage, not successful validation.
            </p>
          </section>

          <section id="project">
            <span className="docs-step">04 / YOUR SOURCE</span>
            <h2>Use it in your project</h2>
            <p>
              V1&apos;s route discovery focuses on Next.js projects. From your
              project directory, use the standalone CLI in your normal shell.
              These commands are not REPL commands:
            </p>
            <Command label="Project analysis">
              {
                'cd /path/to/your-nextjs-project\nshadow init\nshadow analyze .\nshadow scan --repository .\nshadow findings\nshadow report --format markdown > shadow-report.md'
              }
            </Command>
            <p>
              <code>analyze .</code> prints discovered routes and source
              locations. <code>scan --repository .</code> runs source analysis
              and available scanners, with no dynamic target enabled. It does
              not build, install, or execute your project. Static hypotheses
              remain <code>INCONCLUSIVE</code> until runtime validation is
              performed.
            </p>
            <p>
              The CLI writes local state into <code>.shadowlab/</code> in the
              current directory. Add <code>.shadowlab/</code> to your
              project&apos;s <code>.gitignore</code>, run these commands from
              the same directory, and review exported reports before sharing.
              For machine-readable output, use{' '}
              <code>shadow report --format json &gt; shadow-report.json</code>.
            </p>
            <div className="docs-note">
              <strong>Current coverage</strong>
              <p>
                Automatic patches and browser identity workflows cover the
                shipped local demo. Arbitrary untrusted repository execution
                stays disabled until verified VM-grade isolation is available.
                Docker Compose alone is not that security boundary. Missing
                scanner tools or failed advisory checks are reported explicitly;
                a completed scan is not a complete security assessment.
              </p>
            </div>
          </section>

          <section id="commands">
            <h2>Command reference</h2>
            <div className="docs-table">
              <table>
                <caption>Inside shadow repl</caption>
                <thead>
                  <tr>
                    <th>Command</th>
                    <th>What it does</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['demo / 1', 'Run the bundled synthetic investigation.'],
                    [
                      'doctor / 2',
                      'Check Node, npm, and Git availability; Node must be 22+.',
                    ],
                    [
                      'demo browser',
                      'Run the trusted demo with isolated browser identities.',
                    ],
                    [
                      'findings',
                      'List the latest demo findings and their verdicts.',
                    ],
                    [
                      'fix NUMBER',
                      'Approve a disposable demo patch experiment; review its diff.',
                    ],
                    [
                      'report',
                      'Export the latest demo report and print its private file path.',
                    ],
                    ['stop', 'Stop the demo services; retain saved evidence.'],
                    [
                      'help',
                      'Show available commands and the authorization rules.',
                    ],
                    ['quit / exit / q', 'Exit and stop local demo services.'],
                  ].map(([command, meaning]) => (
                    <tr key={command}>
                      <td>
                        <code>{command}</code>
                      </td>
                      <td>{meaning}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              Outside the REPL, <code>shadow --help</code> lists standalone
              commands, and <code>shadow doctor</code> checks the database and
              available scanners. Pressing Ctrl+C during a demo cancels its work
              and stops its services. Type <code>demo</code> to start another
              disposable run.
            </p>
          </section>

          <section id="screenshots">
            <span className="docs-step">05 / SEE THE WORKFLOW</span>
            <h2>Terminal screenshots</h2>
            <p>
              These are actual terminal recordings from the installed CLI on
              Linux, captured on {captures.recordedAt}. They are rendered for
              readability with private paths and run identifiers normalized.
              Package installation and source-analysis output are marked as
              excerpts. No cookies, credentials, tokens, or sensitive response
              values are published.
            </p>
            <p>
              The demo and browser run completed, and the pictured
              authentication patch passed verification while awaiting review.
              Each screenshot has a downloadable text transcript. Select an
              image to view it at full size.
            </p>
            <div className="docs-gallery">
              {captures.recordings.map((record) => (
                <figure key={record.id}>
                  <figcaption>
                    <span>{record.number}</span>
                    <div>
                      <h3>{record.title}</h3>
                      <p>{record.description}</p>
                    </div>
                  </figcaption>
                  <a
                    href={`/docs/terminal/${record.id}.png`}
                    aria-label={`View full-size ${record.title} screenshot`}
                  >
                    <Image
                      src={`/docs/terminal/${record.id}.png`}
                      alt={record.alt}
                      width={record.width}
                      height={record.height}
                      unoptimized
                      sizes="(max-width: 700px) 100vw, 850px"
                    />
                  </a>
                  <a
                    className="docs-transcript"
                    href={`/docs/terminal/${record.id}.txt`}
                    download
                  >
                    Download {record.title.toLowerCase()} transcript{' '}
                    <ArrowRight size={13} />
                  </a>
                </figure>
              ))}
            </div>
            <p className="docs-meta">
              Recorded CLI source:{' '}
              <a
                href={`https://github.com/Devesh36/shadow-lab/tree/${captures.sourceCommit}`}
              >
                {captures.sourceCommit.slice(0, 7)}
              </a>
              . Outputs may differ as the project evolves.
            </p>
          </section>

          <section id="troubleshooting">
            <h2>Troubleshooting</h2>
            <dl className="docs-faq">
              <dt>The shell cannot find shadow.</dt>
              <dd>
                Run <code>uv tool update-shell</code> and open a new terminal.
                For Homebrew, ensure its bin directory is on your PATH.
              </dd>
              <dt>The first demo is slow or setup fails.</dt>
              <dd>
                Check Node.js 22+, npm, Git, and package registry access. Read
                the printed private <code>setup.log</code> path locally. Ctrl+C
                cancels setup; fix the prerequisite and start <code>demo</code>{' '}
                again.
              </dd>
              <dt>The browser did not open.</dt>
              <dd>
                Copy the printed loopback workspace URL into your browser. The
                local services must still be running.
              </dd>
              <dt>Browser coverage is incomplete.</dt>
              <dd>
                Install compatible Playwright Chromium and its system libraries,
                or configure <code>SHADOWLAB_CHROMIUM_PATH</code>. Inspect the
                recorded failure; do not interpret incomplete coverage as a
                passing check.
              </dd>
              <dt>My project results are INCONCLUSIVE.</dt>
              <dd>
                A source-only scan produces hypotheses. It does not demonstrate
                exploitation. The supported runtime reproduction workflow in V1
                uses the bundled demo.
              </dd>
              <dt>Do I need an LLM key or a cloud account?</dt>
              <dd>
                No. The default rule-based demo works without either. The public
                website hosts only the landing page and these docs;
                investigations run on your machine.
              </dd>
            </dl>
            <Link className="landing-secondary" href="/">
              <ArrowLeft size={15} /> Return to ShadowLab
            </Link>
          </section>
        </main>
      </div>
      <footer className="landing-footer">
        <Link href="/" className="landing-brand">
          <Shield size={20} /> ShadowLab
        </Link>
        <span>Application security, with evidence.</span>
        <a href="https://github.com/Devesh36/shadow-lab/blob/main/LICENSE">
          MIT licensed ↗
        </a>
      </footer>
    </div>
  );
}
