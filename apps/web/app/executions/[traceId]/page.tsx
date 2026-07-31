import {notFound} from "next/navigation";

import {api} from "@/lib/api";
import {label} from "@/lib/presentation";
import type {Execution} from "@/lib/types";

export const dynamic = "force-dynamic";

type Score = {root_cause: string; rationale: string[]; status: string; mahalanobis_distance?: number; ambiguity_score?: number; trajectory_volatility?: number; baseline_id?: string};

export default async function ExecutionDetail({params}: {params: Promise<{traceId: string}>}) {
  const {traceId} = await params;
  let execution: Execution;
  let scores: Score[];
  try {
    [execution, scores] = await Promise.all([
      api<Execution>(`/v1/executions/${traceId}`),
      api<Score[]>(`/v1/executions/${traceId}/scores`),
    ]);
  } catch {
    notFound();
  }
  const score = scores[0];
  return (
    <div className="page-shell">
      <section className="page-heading"><p className="eyebrow">Execution detail</p><h1>{execution.agent_name}</h1><code>{traceId}</code></section>
      <div className="detail-grid">
        <section className="panel"><h2>Trajectory</h2><dl><div><dt>Cluster</dt><dd>{execution.cluster_id}</dd></div><div><dt>Environment</dt><dd>{execution.environment}</dd></div><div><dt>Steps</dt><dd>{execution.step_count}</dd></div><div><dt>Tokens</dt><dd>{execution.total_tokens}</dd></div><div><dt>Data quality</dt><dd>{label(execution.data_quality)}</dd></div></dl></section>
        <section className="panel"><h2>Classification</h2>{score ? <><span className="badge">{label(score.status)}</span><h3>{label(score.root_cause)}</h3><ul>{score.rationale.map((reason) => <li key={reason}>{reason}</li>)}</ul></> : <p className="empty">Score unavailable.</p>}</section>
      </div>
      {score && <section className="metric-grid"><Metric label="Mahalanobis distance" value={score.mahalanobis_distance}/><Metric label="Input ambiguity" value={score.ambiguity_score}/><Metric label="Trajectory volatility" value={score.trajectory_volatility}/><article className="metric"><p className="eyebrow">Baseline</p><strong className="small-value">{score.baseline_id ?? "Structural only"}</strong><p>Versioned scoring evidence</p></article></section>}
      <div className="notice">Prompt and output text are not stored. Investigation uses hashes, structural features, embeddings, and score rationale.</div>
    </div>
  );
}

function Metric({label: metricLabel, value}: {label: string; value?: number}) {
  return <article className="metric"><p className="eyebrow">{metricLabel}</p><strong>{value?.toFixed(3) ?? "—"}</strong><p>Computed evidence</p></article>;
}

