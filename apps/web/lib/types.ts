export type Summary = {
  executions: number;
  drifted: number;
  semantic_scored: number;
  semantic_coverage: number;
  open_findings: number;
};

export type Execution = {
  trace_id: string;
  cluster_id: string;
  environment: string;
  agent_name: string;
  agent_version: string;
  started_at: string;
  data_quality: string;
  trajectory_volatility: number | null;
  step_count: number;
  total_tokens: number;
};

export type Finding = {
  finding_id: string;
  trace_id: string;
  severity: string;
  root_cause: string;
  title: string;
  state: string;
  created_at: string;
};

export type Page<T> = {items: T[]; next_cursor: string | null};

