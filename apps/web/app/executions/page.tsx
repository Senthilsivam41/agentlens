import Link from "next/link";

import {api} from "@/lib/api";
import {compact, label} from "@/lib/presentation";
import type {Execution, Page} from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function ExecutionsPage() {
  let executions: Execution[] = [];
  let degraded = false;
  try {
    executions = (await api<Page<Execution>>("/v1/executions?limit=100")).items;
  } catch {
    degraded = true;
  }
  return (
    <div className="page-shell">
      <section className="page-heading"><p className="eyebrow">Investigation</p><h1>Executions</h1><p>Tenant-scoped traces with structural and semantic evidence.</p></section>
      {degraded && <div className="notice" role="status">Execution data unavailable.</div>}
      <section className="panel table-wrap">
        <table>
          <thead><tr><th>Agent</th><th>Cluster</th><th>Quality</th><th>Steps</th><th>Tokens</th><th>Volatility</th><th><span className="sr-only">Action</span></th></tr></thead>
          <tbody>
            {executions.map((execution) => (
              <tr key={execution.trace_id}>
                <td><strong>{execution.agent_name}</strong><small>{execution.agent_version}</small></td>
                <td>{execution.cluster_id}<small>{execution.environment}</small></td>
                <td><span className="badge">{label(execution.data_quality)}</span></td>
                <td>{execution.step_count}</td><td>{compact(execution.total_tokens)}</td>
                <td>{execution.trajectory_volatility?.toFixed(2) ?? "Unavailable"}</td>
                <td><Link href={`/executions/${execution.trace_id}`}>Inspect</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!executions.length && <p className="empty">No executions received.</p>}
      </section>
    </div>
  );
}

