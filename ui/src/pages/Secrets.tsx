import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '../components/Toast';
import { apiFetch } from '../hooks/useTapcraft';

interface SecretOut {
  id: number;
  name: string;
  category: string | null;
  created_at: string;
}

const SecretsPage = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [form, setForm] = useState({ name: '', value: '', category: '' });

  const { data: secrets = [], isLoading } = useQuery({
    queryKey: ['secrets'],
    queryFn: () => apiFetch<SecretOut[]>('/secrets'),
  });

  const createSecret = useMutation({
    mutationFn: (data: { name: string; value: string; category?: string }) =>
      apiFetch<SecretOut>('/secrets', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['secrets'] });
      setForm({ name: '', value: '', category: '' });
      addToast('success', 'Secret created');
    },
    onError: (e: Error) => addToast('error', e.message),
  });

  const deleteSecret = useMutation({
    mutationFn: (name: string) =>
      apiFetch<{ deleted: boolean }>(`/secrets/${name}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['secrets'] });
      addToast('success', 'Secret deleted');
    },
    onError: (e: Error) => addToast('error', e.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.value) return;
    createSecret.mutate({
      name: form.name,
      value: form.value,
      category: form.category || undefined,
    });
  };

  return (
    <div className="flex flex-col h-full">
      <header className="w-full px-8 py-6 border-b border-border-dark bg-background-dark sticky top-0 z-10">
        <div className="max-w-[1000px] mx-auto">
          <h2 className="text-white text-3xl font-bold tracking-tight">Secrets</h2>
          <p className="text-zinc-400 mt-1">Manage API keys and credentials used by activities</p>
        </div>
      </header>

      <div className="flex-1 px-8 py-8 overflow-auto">
        <div className="max-w-[1000px] mx-auto space-y-8">
          {/* Add Secret Form */}
          <form onSubmit={handleSubmit} className="rounded-xl border border-border-dark bg-surface-light p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="material-symbols-outlined text-primary">key</span>
              <h3 className="text-white font-medium">Add Secret</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                  placeholder="github_token"
                  className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Value</label>
                <input
                  type="password"
                  value={form.value}
                  onChange={(e) => setForm((p) => ({ ...p, value: e.target.value }))}
                  placeholder="ghp_..."
                  className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Category</label>
                <input
                  type="text"
                  value={form.category}
                  onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}
                  placeholder="api_keys"
                  className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                />
              </div>
            </div>
            <div className="mt-4 flex justify-end">
              <button
                type="submit"
                disabled={createSecret.isPending || !form.name || !form.value}
                className="flex items-center gap-2 h-10 px-6 bg-primary text-zinc-950 text-sm font-bold rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[18px]">add</span>
                {createSecret.isPending ? 'Saving...' : 'Add Secret'}
              </button>
            </div>
          </form>

          {/* Secrets List */}
          <div className="rounded-xl border border-border-dark bg-surface-light overflow-hidden">
            <div className="px-6 py-4 border-b border-border-dark">
              <h3 className="text-white font-medium">Stored Secrets</h3>
            </div>
            {isLoading ? (
              <div className="p-6 space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse h-12 bg-zinc-800 rounded-lg" />
                ))}
              </div>
            ) : secrets.length === 0 ? (
              <div className="p-12 text-center">
                <span className="material-symbols-outlined text-4xl text-zinc-600 mb-2 block">key_off</span>
                <p className="text-zinc-500 text-sm">No secrets configured yet</p>
              </div>
            ) : (
              <div className="divide-y divide-border-dark">
                {secrets.map((s) => (
                  <div key={s.id} className="flex items-center justify-between px-6 py-3 hover:bg-zinc-800/30 transition-colors">
                    <div className="flex items-center gap-4">
                      <span className="material-symbols-outlined text-zinc-500">lock</span>
                      <div>
                        <span className="text-white text-sm font-mono">{s.name}</span>
                        {s.category && (
                          <span className="ml-3 text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">
                            {s.category}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => deleteSecret.mutate(s.name)}
                      className="text-zinc-500 hover:text-red-400 transition-colors p-1"
                    >
                      <span className="material-symbols-outlined text-[18px]">delete</span>
                    </button>
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

export default SecretsPage;
