/** Build-only Git history. No requests, credentials, chat transcripts or runtime functions. */
import { execFileSync } from 'node:child_process';
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const shaPattern = /^[0-9a-f]{40}$/;
const dayPattern = /^\d{4}-\d{2}-\d{2}$/;
export const timezone = 'Asia/Kolkata';

export function localDate(timestamp) {
  const value = new Date(timestamp);
  if (!Number.isFinite(value.getTime())) throw new Error('Invalid history date');
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(value);
  const get = type => parts.find(part => part.type === type).value;
  return `${get('year')}-${get('month')}-${get('day')}`;
}

export function parseGit(output) {
  return output.split('\n').filter(Boolean).map(row => {
    const [commit, timestamp, ...subject] = row.split('\x1f');
    if (!shaPattern.test(commit) || !subject.join('\x1f').trim()) throw new Error('Invalid Git history record');
    return { commit, date: localDate(timestamp), subject: subject.join('\x1f') };
  });
}

export function history(catalog, records = []) {
  if (catalog.timezone !== timezone) throw new Error('History dates must use India Standard Time');
  const phases = new Set(catalog.phases.map(phase => phase.id));
  const annotations = new Map();
  const pending = [];
  for (const entry of catalog.entries) {
    if (!dayPattern.test(entry.date) || localDate(entry.date) !== entry.date || !phases.has(entry.phase)
        || !entry.title?.trim() || !entry.impact?.trim()) throw new Error('Invalid public history annotation');
    if (entry.commit !== null) {
      if (!shaPattern.test(entry.commit) || annotations.has(entry.commit)) throw new Error('Invalid or duplicate annotated commit');
      annotations.set(entry.commit, entry);
    } else {
      if (!entry.matchSubject?.trim()) throw new Error('Current updates need an intended commit subject');
      pending.push(entry);
    }
  }
  const merged = new Map(annotations);
  const matched = new Set();
  for (const record of records) {
    const pendingEntry = pending.find(entry => !matched.has(entry) && entry.matchSubject === record.subject && entry.date === record.date);
    const annotation = annotations.get(record.commit) || pendingEntry;
    if (pendingEntry) matched.add(pendingEntry);
    merged.set(record.commit, {
      commit: record.commit, date: record.date, phase: annotation?.phase || 'ongoing',
      title: annotation?.title || record.subject,
      impact: annotation?.impact || 'Recorded repository change: ' + record.subject,
    });
  }
  const entries = [...merged.values(), ...pending.filter(entry => !matched.has(entry))];
  // Git supplies newest-first order; reverse map insertion order breaks same-day ties correctly.
  const ordered = entries.map((entry, index) => ({ ...entry, order: index }));
  const gitOrder = new Map(records.map((entry, index) => [entry.commit, index]));
  ordered.sort((left, right) => right.date.localeCompare(left.date) ||
    (left.commit === null && right.commit === null ? right.order - left.order : left.commit === null ? -1 : right.commit === null ? 1 :
      gitOrder.has(left.commit) && gitOrder.has(right.commit) ? gitOrder.get(left.commit) - gitOrder.get(right.commit) : right.order - left.order));
  return { timezone, phases: catalog.phases, source: records.length ? 'git-and-notes' : 'recorded-snapshot',
           entries: ordered.map(({ order, matchSubject, ...entry }) => entry) };
}

export function generate(directory, environment = process.env) {
  const catalog = JSON.parse(readFileSync(resolve(directory, 'content/phases.json'), 'utf8'));
  let records = [];
  try {
    const options = { encoding: 'utf8', timeout: 5000, maxBuffer: 2 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'] };
    const repository = execFileSync('git', ['-C', directory, 'rev-parse', '--show-toplevel'], options).trim();
    if (resolve(repository, 'apps/landing') === resolve(directory)) {
      records = parseGit(execFileSync('git', ['-C', directory, 'log', '--max-count=1000', '--format=%H%x1f%cI%x1f%s'], options));
    }
  } catch (error) {
    // Source archives and provider copies may not contain Git. Preserve the reviewed snapshot.
    if (error.code !== 'ENOENT' && error.status !== 128) throw error;
  }
  let providerMetadata = false;
  if (!records.length) {
    const commit = environment.VERCEL_GIT_COMMIT_SHA || '';
    const subject = (environment.VERCEL_GIT_COMMIT_MESSAGE || '').split('\n')[0].trim();
    const note = catalog.entries.find(entry => entry.commit === null && entry.matchSubject === subject);
    if (shaPattern.test(commit) && note) {
      // The provider supplies the hash/subject; keep the reviewed work date, not an invented timestamp.
      records.push({ commit, subject, date: note.date });
      providerMetadata = true;
    }
  }
  const result = history(catalog, records);
  if (providerMetadata) result.source = 'provider-and-notes';
  const output = resolve(directory, '.generated');
  mkdirSync(output, { recursive: true });
  writeFileSync(resolve(output, 'phases.json'), JSON.stringify(result, null, 2) + '\n');
  console.log(`Phase history: ${result.entries.length} recorded updates (${result.source})`);
  return result;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  generate(resolve(dirname(fileURLToPath(import.meta.url)), '..'));
}
