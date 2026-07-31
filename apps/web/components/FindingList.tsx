import Link from "next/link";

import type {Finding} from "@/lib/types";
import {label} from "@/lib/presentation";

export function FindingList({findings}: {findings: Finding[]}) {
  if (!findings.length) return <p className="empty">No active findings in current tenant.</p>;
  return (
    <ul className="findings">
      {findings.map((finding) => (
        <li key={finding.finding_id}>
          <div>
            <span className={`badge severity-${finding.severity}`}>{finding.severity}</span>
            <strong>{finding.title}</strong>
            <p>{label(finding.root_cause)} · {finding.state}</p>
          </div>
          <Link href={`/executions/${finding.trace_id}`}>Inspect execution</Link>
        </li>
      ))}
    </ul>
  );
}

