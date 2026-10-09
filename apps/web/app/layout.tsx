import type { ReactNode } from 'react';
import './globals.css';
export const metadata = { title: 'ShadowLab · Security workspace', description: 'Evidence-driven application security investigations' };
export default function Layout({ children }: { children: ReactNode }) { return <html lang="en"><body>{children}</body></html>; }
