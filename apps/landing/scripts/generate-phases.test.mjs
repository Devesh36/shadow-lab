import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { generate, history, localDate, parseGit } from './generate-phases.mjs';

const sha = 'a'.repeat(40);
const next = 'b'.repeat(40);
const catalog = () => ({ timezone: 'Asia/Kolkata', phases: [{ id: 'ongoing', title: 'Continuous improvement' }],
  entries: [{ commit: sha, date: '2026-10-09', phase: 'ongoing', title: 'Baseline', impact: 'Preserved the application.' }] });

test('commit dates use IST across UTC midnight boundaries', () => {
  assert.equal(localDate('2026-10-09T20:00:00Z'), '2026-10-10');
  assert.equal(localDate('2026-10-09T18:29:59Z'), '2026-10-09');
  assert.throws(() => localDate('invalid'), /Invalid/);
});
test('Git records keep delimiter characters inside subjects and reject invalid links', () => {
  assert.equal(parseGit(`${sha}\x1f2026-10-09T12:00:00Z\x1fUpdate | navigation\n`)[0].subject, 'Update | navigation');
  assert.throws(() => parseGit('bad\x1f2026-10-09\x1fTitle'), /Invalid/);
});
test('every available new commit appears even without an annotation', () => {
  const result = history(catalog(), [{ commit: next, date: '2026-10-10', subject: 'Improve setup diagnostics' }]);
  assert.equal(result.entries.length, 2);
  assert.equal(result.entries[0].commit, next);
  assert.match(result.entries[0].impact, /Improve setup diagnostics/);
});
test('shallow histories retain older curated commits without duplication', () => {
  const result = history(catalog(), [{ commit: sha, date: '2026-10-09', subject: 'Original subject' }]);
  assert.equal(result.entries.length, 1);
  assert.equal(result.entries[0].title, 'Baseline');
});
test('the current work note resolves to its own commit without a self-referential hash', () => {
  const notes = catalog();
  notes.entries.push({ commit: null, matchSubject: 'Add timeline', date: '2026-10-10', phase: 'ongoing',
                       title: 'A public history', impact: 'Explains each change.' });
  const preview = history(notes);
  assert.equal(preview.entries[0].commit, null);
  const result = history(notes, [{ commit: next, date: '2026-10-10', subject: 'Add timeline' }]);
  assert.equal(result.entries.length, 2);
  assert.equal(result.entries[0].commit, next);
  assert.equal(result.entries[0].title, 'A public history');
});
test('same-day Git chronology is newest first, independent of snapshot order', () => {
  const result = history(catalog(), [
    { commit: next, date: '2026-10-09', subject: 'Newer' },
    { commit: sha, date: '2026-10-09', subject: 'Older' },
  ]);
  assert.deepEqual(result.entries.map(entry => entry.commit), [next, sha]);
});
test('bad dates, phases and duplicate commit annotations fail rather than silently publish', () => {
  for (const change of [entry => { entry.date = '2026-02-31'; }, entry => { entry.phase = 'unknown'; }]) {
    const notes = catalog(); change(notes.entries[0]);
    assert.throws(() => history(notes), /Invalid/);
  }
  const notes = catalog(); notes.entries.push(notes.entries[0]);
  assert.throws(() => history(notes), /duplicate/);
});
test('source archives build the reviewed snapshot without Git or network calls', () => {
  const directory = mkdtempSync(join(tmpdir(), 'shadow-phases-'));
  try {
    mkdirSync(join(directory, 'content'));
    writeFileSync(join(directory, 'content/phases.json'), JSON.stringify(catalog()));
    const result = generate(directory);
    assert.equal(result.source, 'recorded-snapshot');
    assert.equal(JSON.parse(readFileSync(join(directory, '.generated/phases.json'))).entries[0].commit, sha);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});

test('Git-free provider builds link the current work note using valid injected metadata', () => {
  const directory = mkdtempSync(join(tmpdir(), 'shadow-provider-phases-'));
  try {
    const notes = catalog();
    notes.entries.push({ commit: null, matchSubject: 'Add timeline', date: '2026-10-10', phase: 'ongoing',
                         title: 'Public history', impact: 'Explains changes.' });
    mkdirSync(join(directory, 'content'));
    writeFileSync(join(directory, 'content/phases.json'), JSON.stringify(notes));
    const result = generate(directory, { VERCEL_GIT_COMMIT_SHA: next, VERCEL_GIT_COMMIT_MESSAGE: 'Add timeline\nBody omitted' });
    assert.equal(result.source, 'provider-and-notes');
    assert.equal(result.entries[0].commit, next);
    assert.equal(result.entries[0].date, '2026-10-10');
    const fallback = generate(directory, { VERCEL_GIT_COMMIT_SHA: 'invalid', VERCEL_GIT_COMMIT_MESSAGE: 'Add timeline' });
    assert.equal(fallback.source, 'recorded-snapshot');
    assert.equal(fallback.entries[0].commit, null);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});
