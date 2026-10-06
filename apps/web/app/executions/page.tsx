import Link from "next/link";

import {ActionBadge} from "@/components/ActionBadge";
import {api} from "@/lib/api";
import {compact, isDemoIdentity, label, volatilityTone} from "@/lib/presentation";
import type {Execution, Page} from "@/lib/types";

export const dynamic = "force-dynamic";

type ExecutionsSearch = {
  agent_name?: string | string[];
  environment?: string | string[];
};

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function ExecutionsPage({
  searchParams,
}: {
  searchParams: Promise<ExecutionsSearch>;
}) {
  const params = await searchParams;
  const agentName = first(params.agent_name);
  const environment = first(params.environment);
  const query = new URLSearchParams({limit: "100"});
  if (agentName) query.set("agent_name", agentName);
  if (environment) query.set("environment", environment);
  const demoFilter = isDemoIdentity(agentName ?? "", environment ?? "");
  let executions: Execution[] = [];
  let degraded = false;
  try {
    executions = (await api<Page<Execution>>(`/v1/executions?${query}`)).items;
  } catch {
    degraded = true;
  }
  return (
    <div className="page-shell">
      <section className="page-heading"><p className="eyebrow">Investigation</p><h1>Executions</h1><p>Red means act on the agent or a tool. Orange means review the prompt or the path. Green means no action.</p></section>
      {demoFilter && <div className="notice" role="status">Demo traffic for customer walkthroughs. These executions are the simulated support agent <strong>demo-support-agent</strong> in the <strong>demo</strong> environment, kept separate from production agents.</div>}
      {degraded && <div className="notice" role="status">Execution data unavailable.</div>}
      <section className="panel table-wrap">
        <table>
          <thead><tr><th>Agent</th><th>Cluster</th><th>Action</th><th>Quality</th><th>Steps</th><th>Tokens</th><th>Volatility</th><th><span className="sr-only">Inspect</span></th></tr></thead>
          <tbody>
            {executions.map((execution) => (
              <tr key={execution.trace_id}>
                <td><strong>{execution.agent_name}</strong>{isDemoIdentity(execution.agent_name, execution.environment) && <> <span className="badge">Demo</span></>}<small>{execution.agent_version}</small></td>
                <td>{execution.cluster_id}<small>{execution.environment}</small></td>
                <td><ActionBadge rootCause={execution.root_cause} /></td>
                <td><span className="badge">{label(execution.data_quality)}</span></td>
                <td>{execution.step_count}</td><td>{compact(execution.total_tokens)}</td>
                <td className={`metric-value tone-text-${volatilityTone(execution.trajectory_volatility)}`}>{execution.trajectory_volatility?.toFixed(2) ?? "Unavailable"}</td>
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

