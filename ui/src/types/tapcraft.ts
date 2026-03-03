/**
 * Tapcraft domain model types
 */

export interface Workspace {
  id: number;
  owner_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface ActivityOperation {
  id: number;
  activity_id: number;
  name: string;
  display_name: string;
  description: string | null;
  config_schema: string;
  code_symbol: string;
  created_at: string;
  updated_at: string;
}

export interface Activity {
  id: number;
  workspace_id: number;
  name: string;
  slug: string;
  description: string | null;
  category: string | null;
  code_module_path: string;
  graph_id: number | null;
  created_at: string;
  updated_at: string;
  operations: ActivityOperation[];
}

export interface Node {
  id: number;
  graph_id: number;
  kind: 'trigger' | 'activity_operation' | 'primitive' | 'logic';
  label: string;
  activity_operation_id: number | null;
  primitive_type: string | null;
  config: string;
  config_schema: string;
  ui_position: string;
  created_at: string;
  updated_at: string;
}

export interface Edge {
  id: number;
  graph_id: number;
  from_node_id: number;
  to_node_id: number;
  path: string | null;
  label: string | null;
  created_at: string;
  updated_at: string;
}

export interface Graph {
  id: number;
  workspace_id: number;
  owner_type: 'workflow' | 'activity';
  owner_id: number;
  entry_node_id: number | null;
  layout_metadata: string;
  version: number;
  nodes: Node[];
  edges: Edge[];
  created_at: string;
  updated_at: string;
}

export interface Workflow {
  id: number;
  workspace_id: number;
  name: string;
  slug: string;
  description: string | null;
  graph_id: number;
  code_module_path: string;
  entrypoint_symbol: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowWithGraph extends Workflow {
  graph: Graph;
}

export interface Schedule {
  id: number;
  workspace_id: number;
  workflow_id: number;
  name: string;
  cron: string;
  timezone: string;
  enabled: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Run {
  id: number;
  workspace_id: number;
  workflow_id: number;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  started_at: string | null;
  ended_at: string | null;
  summary: string | null;
  error_excerpt: string | null;
  input_config: string;
  temporal_workflow_id: string | null;
  temporal_run_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentMessage {
  id: number;
  session_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  action: string | null;
  created_at: string;
}

export interface AgentSession {
  id: number;
  workspace_id: number;
  target_type: 'activity' | 'workflow';
  target_id: number | null;
  mode: 'create' | 'modify' | 'debug';
  user_prompt: string;
  plan: string | null;
  graph_diff: string | null;
  code_diff_summary: string | null;
  status: 'draft' | 'applied' | 'rejected';
  created_at: string;
  updated_at: string;
  messages?: AgentMessage[];
}

// API Request/Response types
export interface CreateWorkflowRequest {
  user_prompt: string;
  available_activities?: number[] | null;
}

export interface CreateWorkflowResponse {
  workflow: Workflow;
  graph: Graph;
  code_preview: string;
  agent_session_id: number;
}

export interface ExecuteWorkflowRequest {
  workflow_id: number;
  input_config: Record<string, unknown>;
}

export interface ExecuteWorkflowResponse {
  run_id: number;
  workflow_id: number;
  temporal_workflow_id: string;
  status: string;
}

export interface ActivityHistoryEntry {
  activity_name: string;
  status: 'completed' | 'failed' | 'running' | 'timed_out';
  scheduled_at: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  error?: string | null;
}

export interface RunStatusResponse {
  run_id: number;
  status: string;
  started_at: string | null;
  ended_at?: string | null;
  summary?: string | null;
  error_excerpt?: string | null;
  temporal_status?: string;
  workflow_id?: number;
  workflow_name?: string;
  temporal_workflow_id?: string | null;
  input_config?: string;
  activity_history?: ActivityHistoryEntry[];
}

// Graph visualization types
export interface NodePosition {
  x: number;
  y: number;
}

export interface ParsedNode extends Node {
  position: NodePosition;
  configData: Record<string, unknown>;
}

export interface ParsedGraph extends Omit<Graph, 'nodes'> {
  nodes: ParsedNode[];
}
