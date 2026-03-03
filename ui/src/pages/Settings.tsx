import { useState, useEffect } from 'react';
import { useConfig, useSaveConfig } from '../hooks/useTapcraft';
import { useToast } from '../components/Toast';

const SettingsPage = () => {
  const { data, isLoading } = useConfig();
  const saveConfig = useSaveConfig();
  const { addToast } = useToast();

  const [form, setForm] = useState({
    git_remote: '',
    git_branch: 'main',
    task_queue: 'default',
  });

  useEffect(() => {
    if (data) {
      setForm({
        git_remote: data.git_remote ?? '',
        git_branch: data.git_branch ?? 'main',
        task_queue: data.task_queue ?? 'default',
      });
    }
  }, [data]);

  const handleSave = () => {
    saveConfig.mutate(
      {
        git_remote: form.git_remote,
        git_branch: form.git_branch,
        timezone: data?.timezone ?? 'UTC',
        task_queue: form.task_queue,
      },
      {
        onSuccess: () => addToast('success', 'Settings saved successfully'),
        onError: () => addToast('error', 'Failed to save settings'),
      }
    );
  };

  const updateField = (field: string, value: string | number) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="w-full px-8 py-6 border-b border-border-dark bg-background-dark sticky top-0 z-10">
        <div className="max-w-[1000px] mx-auto">
          <h2 className="text-white text-3xl font-bold tracking-tight">Settings</h2>
          <p className="text-zinc-400 mt-1">Configure your Tapcraft environment</p>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 px-8 py-8 overflow-auto">
        <div className="max-w-[1000px] mx-auto">
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="animate-pulse rounded-xl border border-border-dark bg-surface-light p-6">
                  <div className="h-4 w-1/3 bg-zinc-700 rounded mb-4" />
                  <div className="space-y-3">
                    <div className="h-10 bg-zinc-800 rounded-lg" />
                    <div className="h-10 bg-zinc-800 rounded-lg" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Git Configuration */}
              <div className="rounded-xl border border-border-dark bg-surface-light p-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="material-symbols-outlined text-primary">code</span>
                  <h3 className="text-white font-medium">Git Configuration</h3>
                </div>
                <p className="text-zinc-500 text-sm mb-4">Configure git remotes and commit behavior.</p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Remote URL</label>
                    <input
                      type="text"
                      value={form.git_remote}
                      onChange={(e) => updateField('git_remote', e.target.value)}
                      placeholder="https://github.com/..."
                      className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Branch</label>
                    <input
                      type="text"
                      value={form.git_branch}
                      onChange={(e) => updateField('git_branch', e.target.value)}
                      className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                    />
                  </div>
                </div>
              </div>

              {/* Temporal Configuration */}
              <div className="rounded-xl border border-border-dark bg-surface-light p-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="material-symbols-outlined text-primary">cloud_queue</span>
                  <h3 className="text-white font-medium">Temporal</h3>
                </div>
                <p className="text-zinc-500 text-sm mb-4">Temporal connection and queue settings.</p>
                <div className="space-y-3">
                  <div className="flex justify-between items-center py-2">
                    <span className="text-zinc-400 text-sm">Address</span>
                    <span className="text-zinc-300 text-sm font-mono">{data?.temporal?.address ?? 'localhost:7233'}</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-t border-zinc-800">
                    <span className="text-zinc-400 text-sm">Namespace</span>
                    <span className="text-zinc-300 text-sm font-mono">{data?.temporal?.namespace ?? 'default'}</span>
                  </div>
                  <div className="pt-3 border-t border-zinc-800">
                    <label className="block text-xs text-zinc-400 uppercase tracking-wider mb-2">Task Queue</label>
                    <input
                      type="text"
                      value={form.task_queue}
                      onChange={(e) => updateField('task_queue', e.target.value)}
                      className="w-full h-10 px-3 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
                    />
                  </div>
                </div>
              </div>

              {/* About */}
              <div className="rounded-xl border border-border-dark bg-surface-light p-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="material-symbols-outlined text-primary">info</span>
                  <h3 className="text-white font-medium">About</h3>
                </div>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Version</span>
                    <span className="text-zinc-300 font-mono">0.1.0</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Environment</span>
                    <span className="text-zinc-300">Development</span>
                  </div>
                  <div className="pt-3 border-t border-zinc-800">
                    <p className="text-zinc-500 text-xs">
                      Tapcraft OS - Single-tenant automation platform powered by Temporal.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Save Button */}
          <div className="mt-8 flex items-center justify-end gap-3">
            <button
              onClick={handleSave}
              disabled={saveConfig.isPending}
              className="flex items-center gap-2 h-10 px-6 bg-primary text-zinc-950 text-sm font-bold rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {saveConfig.isPending ? (
                <>
                  <span className="animate-spin material-symbols-outlined text-[18px]">progress_activity</span>
                  Saving...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[18px]">save</span>
                  Save Changes
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
