import Link from "next/link";

import {ActionBadge} from "@/components/ActionBadge";
import {label} from "@/lib/presentation";
import type {Finding} from "@/lib/types";

export function FindingList({findings}: {findings: Finding[]}) {
  if (!findings.length) return <p className="empty">No active findings in current tenant.</p>;
  return (
    <ul className="findings">
      {findings.map((finding) => (
        <li key={finding.finding_id}>
          <div>
            <ActionBadge rootCause={finding.root_cause} />
            <strong>{finding.title}</strong>
            <p>{label(finding.root_cause)} · {finding.state}</p>
          </div>
          <Link href={`/executions/${finding.trace_id}`}>Inspect execution</Link>
        </li>
      ))}
    </ul>
  );
}

