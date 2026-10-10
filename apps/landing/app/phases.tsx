import { ArrowUpRight, GitCommitHorizontal } from 'lucide-react';
import history from '../.generated/phases.json';

type Entry = (typeof history.entries)[number];
const date = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata',
});

function Update({ entry }: { entry: Entry }) {
  const phase = history.phases.find(phase => phase.id === entry.phase);
  return (
    <li className="m-phase-update" data-reveal data-commit={entry.commit || 'current-update'}>
      <div className="m-phase-date">
        <time dateTime={entry.date}>{date.format(new Date(entry.date))}</time>
        <span>{phase?.title}</span>
      </div>
      <div className="m-phase-change">
        <h3>{entry.title}</h3>
        <p>{entry.impact}</p>
        {entry.commit ? (
          <a href={`https://github.com/Devesh36/shadow-lab/commit/${entry.commit}`}>
            <GitCommitHorizontal size={14} aria-hidden="true" />
            <span>Commit {entry.commit.slice(0, 7)}</span>
            <ArrowUpRight size={13} aria-hidden="true" />
          </a>
        ) : <span className="m-phase-current">Work summary · commit link unavailable in this build</span>}
      </div>
    </li>
  );
}

export default function Phases() {
  const recent = history.entries.slice(0, 5);
  const earlier = history.entries.slice(5);
  return (
    <section id="phases" className="m-phases m-container" aria-labelledby="phases-title">
      <div className="m-section-heading" data-reveal>
        <div>
          <span className="m-eyebrow">BUILDING SHADOWLAB, ONE CHANGE AT A TIME</span>
          <h2 id="phases-title">Phases</h2>
        </div>
        <p>What changed, when, and what it made possible. A public record of the work behind ShadowLab.</p>
      </div>
      <div className="m-phase-overview">
        {history.phases.map((phase, index) => (
          <article key={phase.id} data-reveal>
            <span className="m-phase-index" aria-hidden="true">0{index + 1}</span>
            <h3>{phase.title}</h3>
            <p>{phase.description}</p>
          </article>
        ))}
      </div>
      <div className="m-phase-history-heading">
        <h3>Development history</h3>
        <span>{history.entries.length} recorded updates · Dates in IST</span>
      </div>
      <ol className="m-phase-timeline" aria-label="Latest development updates">
        {recent.map(entry => <Update key={entry.commit || entry.title} entry={entry} />)}
      </ol>
      {earlier.length > 0 && (
        <details className="m-phase-archive">
          <summary>View {earlier.length} earlier updates <span aria-hidden="true">+</span></summary>
          <ol className="m-phase-timeline" aria-label="Earlier development updates">
            {earlier.map(entry => <Update key={entry.commit || entry.title} entry={entry} />)}
          </ol>
        </details>
      )}
      <div className="m-phase-footnote">
        <p>Dates mark recorded changes, not an invented start date. Work is summarized here; private conversations and credentials stay private.</p>
        <a href="https://github.com/Devesh36/shadow-lab/commits/main/">Full commit archive <ArrowUpRight size={14} /></a>
      </div>
    </section>
  );
}
