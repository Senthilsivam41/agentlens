import Link from "next/link";

import {FindingList} from "@/components/FindingList";
import {MetricCard} from "@/components/MetricCard";
import {api} from "@/lib/api";
import {compact, percentage} from "@/lib/presentation";
import type {Finding, Summary} from "@/lib/types";

export const dynamic = "force-dynamic";

const emptySummary: Summary = {
  executions: 0,
  drifted: 0,
  semantic_scored: 0,
  semantic_coverage: 0,
  open_findings: 0,
};

export default async function OverviewPage() {
  let summary = emptySummary;
  let findings: Finding[] = [];
  let degraded = false;
  try {
    [summary, findings] = await Promise.all([
      api<Summary>("/v1/metrics/summary"),
      api<Finding[]>("/v1/findings?limit=8"),
    ]);
  } catch {
    degraded = true;
  }
  const driftRate = summary.executions ? summary.drifted / summary.executions : 0;
  return (
    <div className="page-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Production pilot</p>
          <h1>See why agents drift.</h1>
          <p className="lede">Trace behavior, resource waste, and mathematical drift without placing an LLM judge in the request path.</p>
        </div>
        <Link className="primary-action" href="/executions">Investigate executions</Link>
      </section>
      {degraded && <div className="notice" role="status">Live data unavailable. Check API and ClickHouse readiness.</div>}
      <section className="metric-grid" aria-label="Agent health summary">
        <MetricCard label="Executions" value={compact(summary.executions)} detail="Current tenant" />
        <MetricCard label="Drift rate" value={percentage(driftRate)} detail={`${summary.drifted} drifted`} tone={driftRate > 0.1 ? "warning" : "good"} />
        <MetricCard label="Semantic coverage" value={percentage(summary.semantic_coverage)} detail={`${summary.semantic_scored} selected traces`} />
        <MetricCard label="Open findings" value={compact(summary.open_findings)} detail="Awaiting review" tone={summary.open_findings ? "warning" : "good"} />
      </section>
      <section className="panel">
        <div className="section-heading"><div><p className="eyebrow">Priority queue</p><h2>Recent findings</h2></div><Link href="/executions">View all</Link></div>
        <FindingList findings={findings} />
      </section>
    </div>
  );
}

