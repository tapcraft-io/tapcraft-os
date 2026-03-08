import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '../components/Toast';
import { apiFetch } from '../hooks/useTapcraft';
import { formatDistanceToNow } from 'date-fns';
import type { Webhook, Workflow } from '../types/tapcraft';

const WORKSPACE_ID = 1;

const WebhooksPage = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [form, setForm] = useState({ workflow_id: '', path: '', secret: '' });
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const { data: webhooks = [], isLoading } = useQuery({
    queryKey: ['webhooks', WORKSPACE_ID],
    queryFn: () => apiFetch<Webhook[]>(`/webhooks?workspace_id=${WORKSPACE_ID}`),
  });

  const { data: workflows = [] } = useQuery({
    queryKey: ['workflows', WORKSPACE_ID],
    queryFn: () => apiFetch<Workflow[]>(`/workflows?workspace_id=${WORKSPACE_ID}`),
  });

  const createWebhook = useMutation({
    mutationFn: (data: { workflow_id: number; path: string; secret?: string; enabled?: boolean }) =>
      apiFetch<Webhook>('/webhooks', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
      setForm({ workflow_id: '', path: '', secret: '' });
      setShowCreateForm(false);
      addToast('success', 'Webhook created');
    },
    onError: (e: Error) => addToast('error', e.message),
  });

  const updateWebhook = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { enabled?: boolean; path?: string; secret?: string } }) =>
      apiFetch<Webhook>(`/webhooks/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
      addToast('success', 'Webhook updated');
    },
    onError: (e: Error) => addToast('error', e.message),
  });

  const deleteWebhook = useMutation({
    mutationFn: (id: number) =>
      apiFetch<{ deleted: boolean }>(`/webhooks/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
      addToast('success', 'Webhook deleted');
    },
    onError: (e: Error) => addToast('error', e.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.workflow_id || !form.path) return;
    createWebhook.mutate({
      workflow_id: Number(form.workflow_id),
      path: form.path,
      secret: form.secret || undefined,
      enabled: true,
    });
  };

  const getWorkflowName = (workflowId: number) => {
    const wf = workflows.find((w) => w.id === workflowId);
    return wf ? wf.name : `Workflow #${workflowId}`;
  };

  const getWebhookUrl = (path: string) => {
    return `POST /hooks/${path}`;
  };

  const copyToClipboard = (webhook: Webhook) => {
    const fullUrl = `${window.location.origin}/hooks/${webhook.path}`;
    navigator.clipboard.writeText(fullUrl).then(() => {
      setCopiedId(webhook.id);
      addToast('success', 'URL copied to clipboard');
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="w-full px-8 py-6 border-b border-border-dark bg-background-dark sticky top-0 z-10">
        <div className="max-w-[1200px] mx-auto flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-white text-3xl font-bold tracking-tight">Webhooks</h2>
            <p className="text-zinc-400 mt-1">Trigger workflows via HTTP endpoints</p>
          </div>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="flex items-center gap-2 h-10 px-6 bg-primary text-zinc-950 text-sm font-bold rounded-lg hover:bg-primary/90 transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Create Webhook
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 px-8 py-8 overflow-auto">
        <div className="max-w-[1200px] mx-auto space-y-8">
          {/* Create Webhook Form */}
          {showCreateForm && (
            <form onSubmit={handleSubmit} className="rounded-xl border border-border-dark bg-surface-light p-6">
              <div className="flex items-center gap-2 mb-4">
                <span className="material-symbols-outlined text-primary">webhook</span>
                <h3 className="text-white font-medium">New Webhook</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Workflow</label>
                  <select
                    value={form.workflow_id}
                    onChange={(e) => setForm((p) => ({ ...p, workflow_id: e.target.value }))}
                    className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                  >
                    <option value="">Select a workflow...</option>
                    {workflows.map((wf) => (
                      <option key={wf.id} value={wf.id}>
                        {wf.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Path</label>
                  <input
                    type="text"
                    value={form.path}
                    onChange={(e) => setForm((p) => ({ ...p, path: e.target.value }))}
                    placeholder="my-webhook"
                    className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">
                    Secret <span className="text-zinc-600 normal-case">(optional)</span>
                  </label>
                  <input
                    type="password"
                    value={form.secret}
                    onChange={(e) => setForm((p) => ({ ...p, secret: e.target.value }))}
                    placeholder="webhook_secret"
                    className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                  />
                </div>
              </div>
              <div className="mt-4 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateForm(false);
                    setForm({ workflow_id: '', path: '', secret: '' });
                  }}
                  className="flex items-center h-10 px-4 text-sm text-zinc-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createWebhook.isPending || !form.workflow_id || !form.path}
                  className="flex items-center gap-2 h-10 px-6 bg-primary text-zinc-950 text-sm font-bold rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[18px]">add</span>
                  {createWebhook.isPending ? 'Creating...' : 'Create Webhook'}
                </button>
              </div>
            </form>
          )}

          {/* Webhooks Table */}
          {isLoading ? (
            <div className="rounded-xl border border-border-dark bg-surface-light/50 overflow-hidden">
              <div className="p-8 space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse flex items-center gap-4">
                    <div className="w-20 h-6 bg-zinc-700 rounded" />
                    <div className="flex-1 h-4 bg-zinc-800 rounded" />
                    <div className="w-24 h-4 bg-zinc-800 rounded" />
                  </div>
                ))}
              </div>
            </div>
          ) : webhooks.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border-2 border-dashed border-border-dark rounded-xl">
              <div className="w-16 h-16 rounded-full bg-surface-light flex items-center justify-center mb-4">
                <span className="material-symbols-outlined text-3xl text-zinc-500">webhook</span>
              </div>
              <p className="text-white font-medium">No webhooks yet</p>
              <p className="text-zinc-500 text-sm mt-1">Create a webhook to trigger workflows via HTTP</p>
            </div>
          ) : (
            <div className="rounded-xl border border-border-dark bg-surface-light/50 overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-zinc-900/50 border-b border-border-dark">
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Path</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Workflow</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Triggers</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Last Triggered</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800">
                    {webhooks.map((webhook) => (
                      <tr key={webhook.id} className="hover:bg-zinc-700/20 transition-colors">
                        {/* Path */}
                        <td className="px-6 py-4">
                          <div className="flex flex-col gap-1">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-white font-mono">/hooks/{webhook.path}</span>
                              <button
                                onClick={() => copyToClipboard(webhook)}
                                className="text-zinc-500 hover:text-primary transition-colors p-0.5"
                                title="Copy webhook URL"
                              >
                                <span className="material-symbols-outlined text-[16px]">
                                  {copiedId === webhook.id ? 'check' : 'content_copy'}
                                </span>
                              </button>
                            </div>
                            <span className="text-xs text-zinc-500 font-mono">{getWebhookUrl(webhook.path)}</span>
                          </div>
                        </td>

                        {/* Workflow */}
                        <td className="px-6 py-4">
                          <span className="text-sm text-zinc-300">{getWorkflowName(webhook.workflow_id)}</span>
                        </td>

                        {/* Status Toggle */}
                        <td className="px-6 py-4">
                          <button
                            onClick={() =>
                              updateWebhook.mutate({
                                id: webhook.id,
                                data: { enabled: !webhook.enabled },
                              })
                            }
                            className="flex items-center gap-2"
                          >
                            {webhook.enabled ? (
                              <span className="inline-flex items-center gap-1.5 rounded bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/20">
                                <span className="material-symbols-outlined text-[12px] icon-filled">check_circle</span>
                                Enabled
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 rounded bg-zinc-500/10 px-2 py-1 text-xs font-medium text-zinc-400 ring-1 ring-inset ring-zinc-500/20">
                                <span className="material-symbols-outlined text-[12px]">pause_circle</span>
                                Disabled
                              </span>
                            )}
                          </button>
                        </td>

                        {/* Trigger Count */}
                        <td className="px-6 py-4">
                          <span className="text-sm text-zinc-300 font-mono">{webhook.trigger_count}</span>
                        </td>

                        {/* Last Triggered */}
                        <td className="px-6 py-4 text-sm text-zinc-400">
                          {webhook.last_triggered_at
                            ? formatDistanceToNow(new Date(webhook.last_triggered_at), { addSuffix: true })
                            : '--'}
                        </td>

                        {/* Actions */}
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() =>
                                updateWebhook.mutate({
                                  id: webhook.id,
                                  data: { enabled: !webhook.enabled },
                                })
                              }
                              className="text-zinc-500 hover:text-white transition-colors p-1"
                              title={webhook.enabled ? 'Disable webhook' : 'Enable webhook'}
                            >
                              <span className="material-symbols-outlined text-[18px]">
                                {webhook.enabled ? 'pause' : 'play_arrow'}
                              </span>
                            </button>
                            <button
                              onClick={() => {
                                if (confirm('Are you sure you want to delete this webhook?')) {
                                  deleteWebhook.mutate(webhook.id);
                                }
                              }}
                              className="text-zinc-500 hover:text-red-400 transition-colors p-1"
                              title="Delete webhook"
                            >
                              <span className="material-symbols-outlined text-[18px]">delete</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WebhooksPage;
