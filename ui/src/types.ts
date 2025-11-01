export interface Capability {
  id: string;
  source?: string;
  params_schema?: Record<string, unknown>;
  returns_schema?: Record<string, unknown>;
}

export interface PlanStep {
  id: string;
  goal: string;
  tool_candidates: string[];
  inputs_hint: Record<string, unknown>;
  outputs_hint: Record<string, unknown>;
}

export interface PlanDoc {
  steps: PlanStep[];
  risks: string[];
  artifacts: string[];
  schedule_hint?: {
    cron: string;
    timezone: string;
  } | null;
}

export interface WorkflowSpec {
  workflow_ref: string;
  config_schema?: Record<string, unknown>;
  loaded?: boolean;
}

export interface RunRecord {
  id: string;
  workflow_ref: string;
  status: string;
  started_at: string;
  ended_at?: string | null;
  duration_ms?: number;
  summary?: string | null;
}

export interface AgentGeneration {
  module_text: string;
  manifest: {
    workflow_ref: string;
    required_tools: string[];
    config_schema?: Record<string, unknown>;
    schedule?: {
      cron: string;
      timezone: string;
    } | null;
  };
}

export interface Issue {
  code: string;
  message: string;
  location?: {
    file: string;
    line?: number;
    symbol?: string;
  };
  fix_hint?: string;
}

export interface ValidationDiag {
  banned_imports: string[];
  unknown_tools: string[];
  schema_issues: string[];
  api_surface_used: string[];
}

export interface ValidationResult {
  ok: boolean;
  issues: Issue[];
  diagnostics?: ValidationDiag;
}

export interface TestsSpec {
  module_path: string;
  tests_text: string;
  commands: string[];
}

export interface MCPServer {
  name: string;
  endpoint: string;
  auth?: string | null;
  tools?: Capability[];
}

export interface DecisionRecord {
  workflow_ref: string;
  created_at: string;
  model: string;
  token_usage: {
    input: number;
    output: number;
  };
  tools: string[];
  prompts: {
    system: string;
    task: string;
    templates_used: string[];
  };
  config_keys: string[];
  notes?: string;
}
