/**
 * React Query hooks for Tapcraft API
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  Activity,
  Workflow,
  WorkflowWithGraph,
  Run,
  Schedule,
  Graph,
  Node,
  Edge,
  ExecuteWorkflowRequest,
  ExecuteWorkflowResponse,
  RunStatusResponse,
  Webhook,
  OAuthProvider,
  OAuthCredential,
} from '../types/tapcraft';
import { getStoredApiKey } from '../components/AuthGate';

const API_BASE = '/api';

// Helper for API calls — injects X-API-Key from localStorage
export async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const apiKey = getStoredApiKey();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      ...headers,
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
// Health & Config
// ============================================================================

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => apiFetch<{
      status: string;
      temporal?: { connected: boolean; namespace: string };
      worker?: { active: boolean; heartbeat_interval?: number };
    }>('/health'),
    refetchInterval: 10_000,
  });
}

export function useConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: () => apiFetch<Record<string, any>>('/config'),
  });
}

export function useSaveConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: Record<string, any>) =>
      apiFetch<Record<string, any>>('/config', {
        method: 'PUT',
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
  });
}

// ============================================================================
// Activities
// ============================================================================

export function useActivities(workspaceId: number) {
  return useQuery({
    queryKey: ['activities', workspaceId],
    queryFn: () => apiFetch<Activity[]>(`/activities?workspace_id=${workspaceId}`),
  });
}

export function useActivity(activityId: number) {
  return useQuery({
    queryKey: ['activities', activityId],
    queryFn: () => apiFetch<Activity>(`/activities/${activityId}`),
    enabled: !!activityId,
  });
}

export function useActivityCode(activityId: number) {
  return useQuery({
    queryKey: ['activities', activityId, 'code'],
    queryFn: () => apiFetch<{ code: string | null; module_path: string }>(`/activities/${activityId}/code`),
    enabled: !!activityId,
  });
}

export function useActivityUsage(activityId: number) {
  return useQuery({
    queryKey: ['activities', activityId, 'usage'],
    queryFn: () => apiFetch<{ workflows: { id: number; name: string; slug: string; description: string | null }[] }>(`/activities/${activityId}/usage`),
    enabled: !!activityId,
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
    queryFn: () => apiFetch<{ code: string; module_path: string }>(`/workflows/${workflowId}/code`),
    enabled: !!workflowId,
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
    refetchInterval: (query) => {
      // Stop polling if run is finished
      const d = query.state.data;
      if (d?.status === 'succeeded' || d?.status === 'failed') {
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

// ============================================================================
// Graph Mutations
// ============================================================================

export function useUpdateNode(graphId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ nodeId, data }: { nodeId: number; data: { label?: string; config?: string; ui_position?: string } }) =>
      apiFetch<Node>(`/graphs/nodes/${nodeId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['graphs', graphId] });
    },
  });
}

export function useCreateNode(graphId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      kind: string;
      label: string;
      config?: string;
      config_schema?: string;
      ui_position?: string;
      activity_operation_id?: number | null;
      primitive_type?: string | null;
    }) =>
      apiFetch<Node>(`/graphs/${graphId}/nodes`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['graphs', graphId] });
    },
  });
}

export function useDeleteNode(graphId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (nodeId: number) =>
      apiFetch<void>(`/graphs/nodes/${nodeId}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['graphs', graphId] });
    },
  });
}

export function useCreateEdge(graphId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { from_node_id: number; to_node_id: number; path?: string; label?: string }) =>
      apiFetch<Edge>(`/graphs/${graphId}/edges`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['graphs', graphId] });
    },
  });
}

export function useDeleteEdge(graphId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (edgeId: number) =>
      apiFetch<void>(`/graphs/edges/${edgeId}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['graphs', graphId] });
    },
  });
}

// ============================================================================
// Code Regeneration
// ============================================================================

export function useRegenerateCode() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (workflowId: number) =>
      apiFetch<{ code: string; module_path: string }>(`/workflows/${workflowId}/regenerate`, {
        method: 'POST',
      }),
    onSuccess: (_data, workflowId) => {
      queryClient.invalidateQueries({ queryKey: ['workflows', workflowId, 'code'] });
    },
  });
}

// ============================================================================
// Webhooks
// ============================================================================

export function useWebhooks(workspaceId: number, workflowId?: number) {
  const params = new URLSearchParams({ workspace_id: workspaceId.toString() });
  if (workflowId) params.append('workflow_id', workflowId.toString());

  return useQuery({
    queryKey: ['webhooks', workspaceId, workflowId],
    queryFn: () => apiFetch<Webhook[]>(`/webhooks?${params.toString()}`),
  });
}

export function useCreateWebhook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { workflow_id: number; path: string; secret?: string; enabled?: boolean }) =>
      apiFetch<Webhook>('/webhooks', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
    },
  });
}

export function useUpdateWebhook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ webhookId, data }: { webhookId: number; data: { path?: string; secret?: string; enabled?: boolean } }) =>
      apiFetch<Webhook>(`/webhooks/${webhookId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
    },
  });
}

export function useDeleteWebhook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (webhookId: number) =>
      apiFetch<void>(`/webhooks/${webhookId}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
    },
  });
}

// ============================================================================
// Run Actions
// ============================================================================

export function useRetryRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: number) =>
      apiFetch<Run>(`/runs/${runId}/retry`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });
}

export function useCancelRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: number) =>
      apiFetch<{ cancelled: boolean }>(`/runs/${runId}/cancel`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });
}

// ============================================================================
// OAuth
// ============================================================================

export function useOAuthProviders(workspaceId: number) {
  return useQuery({
    queryKey: ['oauth-providers', workspaceId],
    queryFn: () => apiFetch<OAuthProvider[]>(`/oauth/providers?workspace_id=${workspaceId}`),
  });
}

export function useCreateOAuthProvider() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      name: string;
      slug: string;
      client_id: string;
      client_secret: string;
      auth_url: string;
      token_url: string;
      scopes?: string;
      redirect_uri?: string;
    }) =>
      apiFetch<OAuthProvider>('/oauth/providers', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-providers'] });
    },
  });
}

export function useDeleteOAuthProvider() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (providerId: number) =>
      apiFetch<void>(`/oauth/providers/${providerId}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-providers'] });
      queryClient.invalidateQueries({ queryKey: ['oauth-credentials'] });
    },
  });
}

export function useOAuthCredentials(workspaceId: number, providerId?: number) {
  const params = new URLSearchParams({ workspace_id: workspaceId.toString() });
  if (providerId) params.append('provider_id', providerId.toString());

  return useQuery({
    queryKey: ['oauth-credentials', workspaceId, providerId],
    queryFn: () => apiFetch<OAuthCredential[]>(`/oauth/credentials?${params.toString()}`),
  });
}

export function useDeleteOAuthCredential() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentialId: number) =>
      apiFetch<void>(`/oauth/credentials/${credentialId}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-credentials'] });
      queryClient.invalidateQueries({ queryKey: ['oauth-providers'] });
    },
  });
}

export function useRefreshOAuthCredential() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentialId: number) =>
      apiFetch<OAuthCredential>(`/oauth/credentials/${credentialId}/refresh`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-credentials'] });
    },
  });
}

