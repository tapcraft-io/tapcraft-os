import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '../components/Toast';
import { apiFetch } from '../hooks/useTapcraft';
import type { OAuthProvider, OAuthCredential } from '../types/tapcraft';

const EMPTY_PROVIDER_FORM = {
  name: '',
  slug: '',
  client_id: '',
  client_secret: '',
  auth_url: '',
  token_url: '',
  scopes: '',
  redirect_uri: '',
};

const OAuthProvidersPage = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [form, setForm] = useState({ ...EMPTY_PROVIDER_FORM });
  const [showForm, setShowForm] = useState(false);

  // ---- Providers ----
  const { data: providers = [], isLoading: providersLoading } = useQuery({
    queryKey: ['oauth-providers'],
    queryFn: () => apiFetch<OAuthProvider[]>('/oauth/providers?workspace_id=1'),
  });

  const createProvider = useMutation({
    mutationFn: (data: typeof form) =>
      apiFetch<OAuthProvider>('/oauth/providers', {
        method: 'POST',
        body: JSON.stringify({ ...data, workspace_id: 1 }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-providers'] });
      setForm({ ...EMPTY_PROVIDER_FORM });
      setShowForm(false);
      addToast('success', 'OAuth provider created');
    },
    onError: (e: Error) => addToast('error', e.message),
  });

  const deleteProvider = useMutation({
    mutationFn: (id: number) =>
      apiFetch<{ deleted: boolean }>(`/oauth/providers/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-providers'] });
      queryClient.invalidateQueries({ queryKey: ['oauth-credentials'] });
      addToast('success', 'Provider deleted');
    },
    onError: (e: Error) => addToast('error', e.message),
  });

  const connectProvider = useMutation({
    mutationFn: (id: number) =>
      apiFetch<{ authorize_url: string }>(`/oauth/providers/${id}/authorize`),
    onSuccess: (data) => {
      window.open(data.authorize_url, '_blank');
    },
    onError: (e: Error) => addToast('error', e.message),
  });

  // ---- Credentials ----
  const { data: credentials = [], isLoading: credentialsLoading } = useQuery({
    queryKey: ['oauth-credentials'],
    queryFn: () => apiFetch<OAuthCredential[]>('/oauth/credentials?workspace_id=1'),
  });

  const deleteCredential = useMutation({
    mutationFn: (id: number) =>
      apiFetch<{ deleted: boolean }>(`/oauth/credentials/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-credentials'] });
      queryClient.invalidateQueries({ queryKey: ['oauth-providers'] });
      addToast('success', 'Credential disconnected');
    },
    onError: (e: Error) => addToast('error', e.message),
  });

  const refreshCredential = useMutation({
    mutationFn: (id: number) =>
      apiFetch<OAuthCredential>(`/oauth/credentials/${id}/refresh`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oauth-credentials'] });
      addToast('success', 'Token refreshed');
    },
    onError: (e: Error) => addToast('error', e.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.slug || !form.client_id || !form.client_secret) return;
    createProvider.mutate(form);
  };

  const getProviderName = (providerId: number): string => {
    const p = providers.find((prov) => prov.id === providerId);
    return p?.name ?? 'Unknown';
  };

  return (
    <div className="flex flex-col h-full">
      <header className="w-full px-8 py-6 border-b border-border-dark bg-background-dark sticky top-0 z-10">
        <div className="max-w-[1000px] mx-auto">
          <h2 className="text-white text-3xl font-bold tracking-tight">OAuth Providers</h2>
          <p className="text-zinc-400 mt-1">Manage OAuth integrations and connected accounts</p>
        </div>
      </header>

      <div className="flex-1 px-8 py-8 overflow-auto">
        <div className="max-w-[1000px] mx-auto space-y-8">

          {/* ================================================================ */}
          {/* Section 1: OAuth Providers                                       */}
          {/* ================================================================ */}

          {/* Add Provider Toggle */}
          {!showForm && (
            <div className="flex justify-end">
              <button
                onClick={() => setShowForm(true)}
                className="flex items-center gap-2 h-10 px-6 bg-primary text-zinc-950 text-sm font-bold rounded-lg hover:bg-primary/90 transition-colors"
              >
                <span className="material-symbols-outlined text-[18px]">add</span>
                Add Provider
              </button>
            </div>
          )}

          {/* Add Provider Form */}
          {showForm && (
            <form onSubmit={handleSubmit} className="rounded-xl border border-border-dark bg-surface-light p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">add_link</span>
                  <h3 className="text-white font-medium">Add OAuth Provider</h3>
                </div>
                <button
                  type="button"
                  onClick={() => { setShowForm(false); setForm({ ...EMPTY_PROVIDER_FORM }); }}
                  className="text-zinc-500 hover:text-white transition-colors p-1"
                >
                  <span className="material-symbols-outlined text-[18px]">close</span>
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Name</label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                    placeholder="Google"
                    className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Slug</label>
                  <input
                    type="text"
                    value={form.slug}
                    onChange={(e) => setForm((p) => ({ ...p, slug: e.target.value }))}
                    placeholder="google"
                    className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Client ID</label>
                  <input
                    type="text"
                    value={form.client_id}
                    onChange={(e) => setForm((p) => ({ ...p, client_id: e.target.value }))}
                    placeholder="xxxxxxxxxxxx.apps.googleusercontent.com"
                    className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Client Secret</label>
                  <input
                    type="password"
                    value={form.client_secret}
                    onChange={(e) => setForm((p) => ({ ...p, client_secret: e.target.value }))}
                    placeholder="GOCSPX-..."
                    className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Auth URL</label>
                  <input
                    type="text"
                    value={form.auth_url}
                    onChange={(e) => setForm((p) => ({ ...p, auth_url: e.target.value }))}
                    placeholder="https://accounts.google.com/o/oauth2/auth"
                    className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Token URL</label>
                  <input
                    type="text"
                    value={form.token_url}
                    onChange={(e) => setForm((p) => ({ ...p, token_url: e.target.value }))}
                    placeholder="https://oauth2.googleapis.com/token"
                    className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Scopes</label>
                  <input
                    type="text"
                    value={form.scopes}
                    onChange={(e) => setForm((p) => ({ ...p, scopes: e.target.value }))}
                    placeholder="openid email profile"
                    className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Redirect URI</label>
                  <input
                    type="text"
                    value={form.redirect_uri}
                    onChange={(e) => setForm((p) => ({ ...p, redirect_uri: e.target.value }))}
                    placeholder="http://localhost:8001/api/oauth/callback"
                    className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                  />
                </div>
              </div>
              <div className="mt-4 flex justify-end">
                <button
                  type="submit"
                  disabled={createProvider.isPending || !form.name || !form.slug || !form.client_id || !form.client_secret}
                  className="flex items-center gap-2 h-10 px-6 bg-primary text-zinc-950 text-sm font-bold rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[18px]">add</span>
                  {createProvider.isPending ? 'Saving...' : 'Add Provider'}
                </button>
              </div>
            </form>
          )}

          {/* Providers List */}
          <div className="rounded-xl border border-border-dark bg-surface-light overflow-hidden">
            <div className="px-6 py-4 border-b border-border-dark">
              <h3 className="text-white font-medium">Configured Providers</h3>
            </div>
            {providersLoading ? (
              <div className="p-6 space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse h-12 bg-zinc-800 rounded-lg" />
                ))}
              </div>
            ) : providers.length === 0 ? (
              <div className="p-12 text-center">
                <span className="material-symbols-outlined text-4xl text-zinc-600 mb-2 block">link_off</span>
                <p className="text-zinc-500 text-sm">No OAuth providers configured yet</p>
              </div>
            ) : (
              <div className="divide-y divide-border-dark">
                {providers.map((p) => (
                  <div key={p.id} className="px-6 py-4 hover:bg-zinc-800/30 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4 min-w-0">
                        <span className="material-symbols-outlined text-zinc-500">cloud</span>
                        <div className="min-w-0">
                          <div className="flex items-center gap-3">
                            <span className="text-white text-sm font-medium">{p.name}</span>
                            <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded font-mono">
                              {p.slug}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 mt-1">
                            <span className="text-zinc-500 text-xs font-mono truncate">{p.client_id}</span>
                            {p.scopes && (
                              <span className="text-zinc-500 text-xs truncate">{p.scopes}</span>
                            )}
                            <span className="text-zinc-400 text-xs">
                              {p.credential_count} credential{p.credential_count !== 1 ? 's' : ''}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-4">
                        <button
                          onClick={() => connectProvider.mutate(p.id)}
                          disabled={connectProvider.isPending}
                          className="flex items-center gap-1.5 h-8 px-3 text-xs font-medium rounded-lg bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-colors disabled:opacity-50"
                        >
                          <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                          Connect
                        </button>
                        <button
                          onClick={() => deleteProvider.mutate(p.id)}
                          className="text-zinc-500 hover:text-red-400 transition-colors p-1"
                        >
                          <span className="material-symbols-outlined text-[18px]">delete</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ================================================================ */}
          {/* Section 2: Connected Accounts (Credentials)                      */}
          {/* ================================================================ */}

          <div className="rounded-xl border border-border-dark bg-surface-light overflow-hidden">
            <div className="px-6 py-4 border-b border-border-dark">
              <h3 className="text-white font-medium">Connected Accounts</h3>
            </div>
            {credentialsLoading ? (
              <div className="p-6 space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse h-12 bg-zinc-800 rounded-lg" />
                ))}
              </div>
            ) : credentials.length === 0 ? (
              <div className="p-12 text-center">
                <span className="material-symbols-outlined text-4xl text-zinc-600 mb-2 block">person_off</span>
                <p className="text-zinc-500 text-sm">No connected accounts yet</p>
                <p className="text-zinc-600 text-xs mt-1">Use the Connect button on a provider above to authorize</p>
              </div>
            ) : (
              <div className="divide-y divide-border-dark">
                {credentials.map((c) => (
                  <div key={c.id} className="px-6 py-4 hover:bg-zinc-800/30 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4 min-w-0">
                        <span className="material-symbols-outlined text-zinc-500">person</span>
                        <div className="min-w-0">
                          <div className="flex items-center gap-3">
                            <span className="text-white text-sm font-medium">{c.name}</span>
                            <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">
                              {getProviderName(c.provider_id)}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 mt-1">
                            <span className="text-zinc-500 text-xs">
                              Token: <span className="font-mono">{c.token_type}</span>
                            </span>
                            {c.expires_at && (
                              <span className="text-zinc-500 text-xs">
                                Expires: {new Date(c.expires_at).toLocaleString()}
                              </span>
                            )}
                            {c.scopes && (
                              <span className="text-zinc-500 text-xs truncate">{c.scopes}</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-4">
                        <button
                          onClick={() => refreshCredential.mutate(c.id)}
                          disabled={refreshCredential.isPending}
                          className="flex items-center gap-1.5 h-8 px-3 text-xs font-medium rounded-lg bg-zinc-800 text-zinc-300 border border-zinc-700 hover:bg-zinc-700 transition-colors disabled:opacity-50"
                        >
                          <span className="material-symbols-outlined text-[16px]">refresh</span>
                          Refresh
                        </button>
                        <button
                          onClick={() => deleteCredential.mutate(c.id)}
                          className="text-zinc-500 hover:text-red-400 transition-colors p-1"
                        >
                          <span className="material-symbols-outlined text-[18px]">delete</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
};

export default OAuthProvidersPage;
