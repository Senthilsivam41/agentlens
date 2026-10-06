import {actionSignal} from "@/lib/presentation";

export function ActionBadge({rootCause}: {rootCause?: string | null}) {
  const signal = actionSignal(rootCause);
  if (!signal) return <span className="badge">Pending</span>;
  return <span className={`badge tone-${signal.tone}`}>{signal.name} · {signal.action}</span>;
}
