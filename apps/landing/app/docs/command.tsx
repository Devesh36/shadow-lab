'use client';

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

export default function Command({
  label,
  children,
}: {
  label: string;
  children: string;
}) {
  const [status, setStatus] = useState('');
  async function copy() {
    try {
      await navigator.clipboard.writeText(children);
      setStatus('Copied.');
    } catch {
      setStatus('Select the commands to copy them manually.');
    }
  }
  return (
    <div className="docs-command">
      <div className="docs-command-bar">
        <span>{label}</span>
        <button aria-label={`Copy ${label}`} onClick={copy}>
          {status === 'Copied.' ? <Check size={14} /> : <Copy size={14} />} Copy
        </button>
      </div>
      <pre>
        <code>{children}</code>
      </pre>
      <span className="docs-copy-status" role="status">
        {status}
      </span>
    </div>
  );
}
