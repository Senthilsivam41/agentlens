type Props = {
  label: string;
  value: string;
  detail: string;
  tone?: "neutral" | "warning" | "good";
};

export function MetricCard({label, value, detail, tone = "neutral"}: Props) {
  return (
    <article className={`metric metric-${tone}`}>
      <p className="eyebrow">{label}</p>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

