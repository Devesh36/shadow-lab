/** Validate Vercel packaging offline using its installed Next.js builder.
 * Usage: node scripts/check-landing-vercel.cjs /path/to/node_modules/@vercel/next
 * Requires npm ci in apps/landing. Builds only a disposable copy of that trusted app.
 * No Vercel login, cloud project, deployment or application secrets are needed.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

async function main() {
  const builderPath = process.argv[2];
  assert.ok(builderPath, 'Pass the path to @vercel/next from an installed Vercel CLI');
  const { build } = require(path.resolve(builderPath));
  const root = path.resolve(__dirname, '..');
  const source = path.join(root, 'apps/landing');
  const evidence = path.join(root, '.shadowlab/vercel-manifest-fix');
  await fs.mkdir(evidence, { recursive: true });
  const workPath = await fs.mkdtemp(path.join(evidence, 'packaging-'));
  try {
    for (const name of ['app', 'package.json', 'package-lock.json', 'next.config.ts', 'tsconfig.json', 'vercel.json']) {
      await fs.cp(path.join(source, name), path.join(workPath, name), { recursive: true });
    }
    await fs.symlink(path.join(source, 'node_modules'), path.join(workPath, 'node_modules'), 'dir');
    const config = JSON.parse(await fs.readFile(path.join(workPath, 'vercel.json'), 'utf8'));
    const settings = { workPath, files: {}, entrypoint: 'package.json', meta: { isDev: true } };
    // Match the adapter enabled in the reported Vercel logs; all work remains local.
    process.env.NEXT_ENABLE_ADAPTER = '1';
    process.env.NEXT_TELEMETRY_DISABLED = '1';
    process.env.VERCEL = '1';
    process.env.CI = '1';
    const result = await build({ ...settings, config: { ...config, installCommand: '' } });
    assert.equal(result.buildOutputVersion, 3);
    const output = path.resolve(result.buildOutputPath);
    assert.equal(output, path.join(workPath, '.next/output'));
    const manifest = JSON.parse(await fs.readFile(path.join(output, 'config.json'), 'utf8'));
    assert.equal(manifest.version, 3);
    assert.ok((await fs.stat(path.join(output, 'static/index.html'))).isFile());
    const functions = await fs.readdir(path.join(output, 'functions')).catch(error => {
      if (error.code === 'ENOENT') return [];
      throw error;
    });
    assert.deepEqual(functions, [], 'The landing deployment must have no runtime functions');
    for (const route of ['api', 'app', 'demo']) {
      assert.equal(await fs.access(path.join(output, 'static', route)).then(() => true, () => false), false);
    }
    // The same real builder must reject the former override after compiling succeeded.
    await assert.rejects(
      build({ ...settings, config: { ...config, installCommand: '', buildCommand: 'true', outputDirectory: 'out' } }),
      error => error.code === 'NEXT_NO_ROUTES_MANIFEST' && error.message.includes('/out/routes-manifest.json')
    );
    await fs.writeFile(path.join(evidence, 'packaging-check.json'), JSON.stringify({
      builder: '@vercel/next', buildOutputVersion: 3, output: '.next/output', runtimeFunctions: 0,
      landingHTML: true, knownBadOverride: 'NEXT_NO_ROUTES_MANIFEST',
      limitations: ['Local provider builder, not a cloud deployment or project-settings inspection'],
    }, null, 2) + '\n');
    console.log('Passed Vercel packaging: static landing, zero functions; former out override reproduces manifest failure');
  } finally {
    await fs.rm(workPath, { recursive: true, force: true });
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
