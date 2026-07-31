import Link from "next/link";

export default function NotFound() {
  return <div className="page-shell"><section className="page-heading"><p className="eyebrow">Not found</p><h1>Execution unavailable.</h1><p>It may not exist, may have expired, or may belong to another tenant.</p><Link className="primary-action" href="/executions">Return to executions</Link></section></div>;
}

