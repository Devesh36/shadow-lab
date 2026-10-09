import type { ReactNode } from 'react';
export const metadata = { title: 'ShadowLab disposable fixture' };
export default function Layout({ children }: { children: ReactNode }) {
  return <html lang="en"><body style={{ background: '#0a1018', color: '#dce8f5', fontFamily: 'monospace', padding: 40 }}>{children}</body></html>;
}
