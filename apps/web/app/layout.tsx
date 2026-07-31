import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import "./styles.css";

export const metadata: Metadata = {
  title: "Agent Lens",
  description: "Explainable observability for agentic AI executions",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="topbar">
          <Link className="brand" href="/">
            <span className="mark" aria-hidden="true">AL</span>
            <span>Agent Lens</span>
          </Link>
          <nav aria-label="Primary navigation">
            <Link href="/">Overview</Link>
            <Link href="/executions">Executions</Link>
            <Link href="/baselines">Baselines</Link>
          </nav>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}

