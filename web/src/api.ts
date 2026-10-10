export interface Summary {
  cases: number;
  completion_rate: number;
  clean_rate: number;
  tool_precision: number;
  tool_recall: number;
  args_valid_rate: number;
  sequence_ok_rate: number;
  grounded_rate: number | null;
  safe_rate: number;
  unsafe_attempt_cases: number;
  privacy_attempt_cases: number;
  leak_cases: number;
  right_answer_wrong_tool: number;
  mean_steps: number;
  failures: Record<string, number>;
  by_category: Record<string, { cases: number; completion_rate: number; clean_rate: number }>;
  latency_ms: { p50: number | null; p95: number | null };
  tokens: { input: number; output: number };
  cost_usd: number;
}

export interface Run {
  id: string;
  model: string;
  prompt: string;
  created_at: string;
  complete: boolean;
  summary: Summary;
}

export interface Score {
  case_id: string;
  category: string;
  completed: boolean;
  outcome_observed: string;
  tool_recall: number;
  tool_precision: number;
  args_valid_rate: number;
  args_match: boolean;
  sequence_ok: boolean;
  grounded: boolean | null;
  unsafe_attempts: number;
  privacy_attempts: number;
  leaked_facts: string[];
  right_answer_wrong_tool: boolean;
  steps: number;
  failure: string | null;
}

export interface CaseRow {
  case_id: string;
  category: string;
  message: string;
  completed: boolean;
  failure: string | null;
  score: Score;
  answer: string;
  latency_ms: number;
  cost_usd: number;
}

export interface ModelEvent {
  type: "model";
  step: number;
  ms: number;
  content: string;
  tool_calls: { name: string; args: Record<string, unknown> }[];
  input_tokens: number;
  output_tokens: number;
}

export interface ToolEvent {
  type: "tool";
  step: number;
  name: string;
  args: Record<string, unknown>;
  verdict: string;
  reason: string;
  result: Record<string, unknown>;
  ms: number;
}

export interface Trace extends CaseRow {
  run_id: string;
  events: (ModelEvent | ToolEvent)[];
  expect: {
    outcome: string[];
    tools_required: string[];
    tools_allowed: string[] | null;
    sequence: string[];
    facts: string[];
    forbidden_facts: string[];
    forbidden_tools: string[];
  } | null;
}

export interface Delta {
  base: number;
  candidate: number;
  change: number;
  verdict: "better" | "worse" | "same";
}

export interface Comparison {
  base: { run: string; model: string; prompt: string };
  candidate: { run: string; model: string; prompt: string };
  deltas: Record<string, Delta>;
  improved: string[];
  regressed: string[];
  tradeoff: boolean;
  flipped_cases: {
    case_id: string;
    category: string;
    base: { completed: boolean; failure: string | null };
    candidate: { completed: boolean; failure: string | null };
    direction: "fixed" | "broke" | "changed";
  }[];
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // keep statusText
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export const api = {
  runs: () => get<Run[]>("/runs"),
  cases: (runId: string) => get<CaseRow[]>(`/runs/${encodeURIComponent(runId)}/cases`),
  trace: (runId: string, caseId: string) =>
    get<Trace>(`/runs/${encodeURIComponent(runId)}/cases/${encodeURIComponent(caseId)}`),
  compare: (base: string, candidate: string) =>
    get<Comparison>(`/compare?base=${encodeURIComponent(base)}&candidate=${encodeURIComponent(candidate)}`),
};

export const runLabel = (r: Pick<Run, "model" | "prompt">) => `${r.model} · ${r.prompt}`;
export const pct = (v: number | null | undefined) => (v == null ? "n/a" : `${(v * 100).toFixed(1)}%`);

export const METRIC_LABELS: Record<string, string> = {
  completion_rate: "Task completion",
  clean_rate: "Clean (no failure)",
  tool_precision: "Tool precision",
  tool_recall: "Tool recall",
  args_valid_rate: "Valid arguments",
  sequence_ok_rate: "Sequence correct",
  grounded_rate: "Grounded",
  safe_rate: "Safe",
  mean_steps: "Mean steps",
  cost_usd: "Cost (USD)",
};

export const FAILURE_HELP: Record<string, string> = {
  step_limit: "Hit the step limit without answering",
  unsafe_action: "Attempted a forbidden or non-permitted tool",
  privacy_violation: "Tried to access another customer's data or leaked it",
  invalid_arguments: "Called a tool with arguments that failed validation",
  wrong_outcome: "Answered, escalated, refused or asked when it should have done something else",
  wrong_answer: "Answer contradicts the facts",
  incomplete: "Right kind of outcome but required facts missing",
  wrong_tool: "Missing required tools, extra tools, or wrong order",
  ungrounded: "Stated a fact that no tool returned",
};
