# Deploy only the ShadowLab landing page

The public website lives in `apps/landing`, a standalone Next.js app with `output: 'export'`. It preserves the existing landing design and exports HTML, CSS and JavaScript. Demo/workspace calls to action point to installation instructions so visitors can run `shadow repl` locally. It has no API routes, database dependencies, service bindings or runtime functions. The original application in `apps/web`, FastAPI backend, REPL and synthetic demo remain intact.

## Vercel settings

1. In Vercel, choose **Add New → Project**, import `Devesh36/shadow-lab`, and select the branch containing this change (`feature/browser-identity-validation`). For an existing project, change its Root Directory and clear previous build/output overrides.
2. Set **Root Directory: `apps/landing`**.
3. Set **Framework Preset: Next.js** and **Build Command: `npm run build`**. **Disable the Output Directory override**, including any previously saved `out` value, so Vercel auto-detects the framework output. Use Node.js 22+ and the default npm installation, which uses the committed lockfile. This app is self-contained; source files outside its Root Directory are unnecessary.
4. No application environment variables or credentials are needed. Do not add API tokens, LLM keys, database URLs or bindings for this website.
5. Select **Deploy** and open the resulting `*.vercel.app` URL. Check the install tabs, clipboard button and mobile layout. `/api/v1/health`, `/app` and `/demo` should return 404 because only the landing website is published. Install ShadowLab locally for the interactive investigation demo.

There is no repository-root `vercel.json` and no multi-service deployment. The configuration in `apps/landing/vercel.json` retains the existing production CSP, nosniff, no-referrer and frame-denial headers for the exported site. No global network/security permissions are changed.

If deployment reports missing `out/routes-manifest.json`, the Output Directory was overridden incorrectly. Next.js stores its build manifests under `.next`; `out` contains the standalone static export for local/manual hosting. Vercel's Next.js builder handles those automatically. Remove the override in **Project Settings → Build and Deployment**, then redeploy the latest commit. Keep `output: 'export'` in `next.config.ts`; this correction does not add server-side application routes.

## Preview locally

Prerequisites: Node.js 22+, npm. From the repository root:

```bash
npm --prefix apps/landing ci
npm --prefix apps/landing run build
npm --prefix apps/landing run typecheck
python3 -m http.server 3100 --bind 127.0.0.1 --directory apps/landing/out
```

Open `http://127.0.0.1:3100`. The static preview needs no Python application dependencies, running API, database or token. Python's basic preview server does not apply Vercel's configured security headers; verify their delivery after actual deployment. Stop it with Ctrl+C. For source development, run `npm --prefix apps/landing run dev`; production validation uses the exported assets.

With the repository's Python dependencies and Playwright Chromium installed, run `uv run python scripts/validate-landing.py` while the static preview is running. `SHADOWLAB_CHROMIUM_PATH` can select an existing compatible browser. This helper checks only the fixed loopback website, applies the configured production headers to browser responses for local validation, and saves sanitized screenshots and results under `.shadowlab/vercel-validation/`.

To test provider packaging without login or deployment, install the pinned Vercel CLI into a temporary directory and pass its builder path to `node scripts/check-landing-vercel.cjs /path/to/node_modules/@vercel/next`. The helper compiles a disposable copy with Vercel's Next.js adapter, checks the static Build Output v3 and absence of runtime functions, and confirms the former `out` override fails with the reported missing-manifest error. The `landing-packaging` CI job runs this check with Vercel CLI 63.1.0.

See [validation](validation.md) for observed build/browser/regression results and limitations. Cloud deployment and provider-side configuration need an authenticated Vercel account; no site has been deployed from this workspace.
