import {api} from "@/lib/api";
import {label} from "@/lib/presentation";

export const dynamic = "force-dynamic";

type Baseline = {baseline_id: string; agent_name: string; agent_version: string; environment: string; status: string; record_count: number; embedding_model: string};

export default async function BaselinesPage() {
  let baselines: Baseline[] = [];
  let degraded = false;
  try { baselines = await api<Baseline[]>("/v1/baselines"); } catch { degraded = true; }
  return <div className="page-shell"><section className="page-heading"><p className="eyebrow">Governance</p><h1>Imported baselines</h1><p>Immutable, externally curated reference populations.</p></section>{degraded && <div className="notice">Baseline data unavailable.</div>}<section className="panel table-wrap"><table><thead><tr><th>Agent</th><th>Environment</th><th>Status</th><th>Records</th><th>Embedding model</th></tr></thead><tbody>{baselines.map((baseline) => <tr key={baseline.baseline_id}><td><strong>{baseline.agent_name}</strong><small>{baseline.agent_version}</small></td><td>{baseline.environment}</td><td><span className="badge">{label(baseline.status)}</span></td><td>{baseline.record_count}</td><td>{baseline.embedding_model}</td></tr>)}</tbody></table>{!baselines.length && <p className="empty">No baseline imported.</p>}</section></div>;
}

