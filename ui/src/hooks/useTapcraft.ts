/**
 * React Query hooks for Tapcraft API
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  App,
  Workflow,
  WorkflowWithGraph,
  Run,
  Schedule,
  Graph,
  CreateWorkflowRequest,
  CreateWorkflowResponse,
  ExecuteWorkflowRequest,
  ExecuteWorkflowResponse,
  RunStatusResponse,
} from '../types/tapcraft';

const API_BASE = 'http://localhost:8000';

// Helper for API calls
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API Error: ${response.status} - ${error}`);
  }

  return response.json();
}

// ============================================================================
// Apps
// ============================================================================

export function useApps(workspaceId: number) {
  return useQuery({
    queryKey: ['apps', workspaceId],
    queryFn: () => apiFetch<App[]>(`/apps?workspace_id=${workspaceId}`),
  });
}

export function useApp(appId: number) {
  return useQuery({
    queryKey: ['apps', appId],
    queryFn: () => apiFetch<App>(`/apps/${appId}`),
    enabled: !!appId,
  });
}

// ============================================================================
// Workflows
// ============================================================================

export function useWorkflows(workspaceId: number) {
  return useQuery({
    queryKey: ['workflows', workspaceId],
    queryFn: () => apiFetch<Workflow[]>(`/workflows?workspace_id=${workspaceId}`),
  });
}

export function useWorkflow(workflowId: number) {
  return useQuery({
    queryKey: ['workflows', workflowId],
    queryFn: () => apiFetch<Workflow>(`/workflows/${workflowId}`),
    enabled: !!workflowId,
  });
}

export function useWorkflowGraph(graphId: number) {
  return useQuery({
    queryKey: ['graphs', graphId],
    queryFn: () => apiFetch<Graph>(`/graphs/${graphId}`),
    enabled: !!graphId,
  });
}

export function useWorkflowCode(workflowId: number) {
  return useQuery({
    queryKey: ['workflows', workflowId, 'code'],
    queryFn: () => apiFetch<{ code: string; module_path: string }>(`/agent/workflows/${workflowId}/code`),
    enabled: !!workflowId,
  });
}

// ============================================================================
// Agent - Create Workflow
// ============================================================================

export function useCreateWorkflow(workspaceId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateWorkflowRequest) =>
      apiFetch<CreateWorkflowResponse>(`/agent/workflows?workspace_id=${workspaceId}`, {
        method: 'POST',
        body: JSON.stringify(request),
      }),
    onSuccess: () => {
      // Invalidate workflows list to refetch
      queryClient.invalidateQueries({ queryKey: ['workflows', workspaceId] });
    },
  });
}

// ============================================================================
// Workflow Execution
// ============================================================================

export function useExecuteWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ workflowId, request }: { workflowId: number; request: ExecuteWorkflowRequest }) =>
      apiFetch<ExecuteWorkflowResponse>(`/execution/workflows/${workflowId}/execute`, {
        method: 'POST',
        body: JSON.stringify(request),
      }),
    onSuccess: (data) => {
      // Invalidate runs list
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });
}

// ============================================================================
// Runs
// ============================================================================

export function useRuns(workspaceId: number, workflowId?: number) {
  const params = new URLSearchParams({ workspace_id: workspaceId.toString() });
  if (workflowId) params.append('workflow_id', workflowId.toString());

  return useQuery({
    queryKey: ['runs', workspaceId, workflowId],
    queryFn: () => apiFetch<Run[]>(`/runs?${params.toString()}`),
    refetchInterval: 3000, // Poll every 3 seconds for status updates
  });
}

export function useRun(runId: number) {
  return useQuery({
    queryKey: ['runs', runId],
    queryFn: () => apiFetch<Run>(`/runs/${runId}`),
    enabled: !!runId,
  });
}

export function useRunStatus(runId: number) {
  return useQuery({
    queryKey: ['runs', runId, 'status'],
    queryFn: () => apiFetch<RunStatusResponse>(`/execution/runs/${runId}/status`),
    enabled: !!runId,
    refetchInterval: (data) => {
      // Stop polling if run is finished
      if (data?.status === 'succeeded' || data?.status === 'failed') {
        return false;
      }
      return 2000; // Poll every 2 seconds while running
    },
  });
}

// ============================================================================
// Schedules
// ============================================================================

export function useSchedules(workspaceId: number, workflowId?: number) {
  const params = new URLSearchParams({ workspace_id: workspaceId.toString() });
  if (workflowId) params.append('workflow_id', workflowId.toString());

  return useQuery({
    queryKey: ['schedules', workspaceId, workflowId],
    queryFn: () => apiFetch<Schedule[]>(`/schedules?${params.toString()}`),
  });
}
