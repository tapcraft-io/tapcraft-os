import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useActivity, useActivityCode, useActivityUsage } from '../hooks/useTapcraft';

type Tab = 'operations' | 'code' | 'usage';

export default function ActivityDetail() {
  const { id } = useParams<{ id: string }>();
  const activityId = Number(id);
  const [tab, setTab] = useState<Tab>('operations');

  const { data: activity, isLoading } = useActivity(activityId);
  const { data: codeData } = useActivityCode(activityId);
  const { data: usageData } = useActivityUsage(activityId);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex items-center gap-3 text-zinc-400">
          <span className="material-symbols-outlined animate-spin">progress_activity</span>
          Loading activity...
        </div>
      </div>
    );
  }

  if (!activity) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <span className="material-symbols-outlined text-4xl text-zinc-700">error</span>
          <p className="text-zinc-400 text-sm mt-2">Activity not found</p>
          <Link to="/activities" className="text-primary text-sm mt-2 inline-block hover:underline">
            Back to activities
          </Link>
        </div>
      </div>
    );
  }

  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: 'operations', label: 'Operations', icon: 'widgets' },
    { key: 'code', label: 'Code', icon: 'code' },
    { key: 'usage', label: 'Usage', icon: 'account_tree' },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="w-full px-8 py-6 border-b border-border-dark bg-background-dark">
        <div className="max-w-[1200px] mx-auto">
          <div className="flex items-center gap-2 text-sm text-zinc-500 mb-3">
            <Link to="/activities" className="hover:text-zinc-300 transition-colors">Activities</Link>
            <span className="material-symbols-outlined text-[14px]">chevron_right</span>
            <span className="text-zinc-300">{activity.name}</span>
          </div>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-white text-3xl font-bold tracking-tight">{activity.name}</h2>
              {activity.description && (
                <p className="text-zinc-400 mt-1">{activity.description}</p>
              )}
              <div className="flex items-center gap-3 mt-3">
                {activity.category && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary ring-1 ring-inset ring-primary/20">
                    {activity.category}
                  </span>
                )}
                <span className="text-xs text-zinc-500 font-mono">{activity.code_module_path}</span>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-6">
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  tab === t.key
                    ? 'bg-primary/10 text-primary'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">{t.icon}</span>
                {t.label}
                {t.key === 'operations' && (
                  <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px] bg-zinc-800 text-zinc-300">
                    {activity.operations.length}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 px-8 py-8 overflow-auto">
        <div className="max-w-[1200px] mx-auto">
          {tab === 'operations' && (
            <div className="rounded-xl border border-border-dark bg-surface-light/50 overflow-hidden">
              {activity.operations.length === 0 ? (
                <div className="p-8 text-center">
                  <span className="material-symbols-outlined text-4xl text-zinc-600">widgets</span>
                  <p className="text-zinc-400 mt-2">No operations defined</p>
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-zinc-900/50 border-b border-border-dark">
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Name</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Description</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Code Symbol</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Config</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800">
                    {activity.operations.map((op) => {
                      let schemaKeys: string[] = [];
                      try {
                        const schema = JSON.parse(op.config_schema);
                        schemaKeys = Object.keys(schema.properties ?? {});
                      } catch {}

                      return (
                        <tr key={op.id} className="hover:bg-zinc-700/20 transition-colors">
                          <td className="px-6 py-4">
                            <div className="text-sm font-medium text-white">{op.display_name}</div>
                            <div className="text-xs text-zinc-500 font-mono">{op.name}</div>
                          </td>
                          <td className="px-6 py-4 text-sm text-zinc-400 max-w-xs">
                            {op.description || '--'}
                          </td>
                          <td className="px-6 py-4 text-sm text-zinc-300 font-mono">
                            {op.code_symbol}
                          </td>
                          <td className="px-6 py-4 text-sm text-zinc-400">
                            {schemaKeys.length > 0 ? (
                              <div className="flex flex-wrap gap-1">
                                {schemaKeys.map((k) => (
                                  <span key={k} className="px-1.5 py-0.5 rounded bg-zinc-800 text-xs text-zinc-300 font-mono">
                                    {k}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              '--'
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {tab === 'code' && (
            <div className="rounded-xl border border-border-dark bg-surface-light/50 overflow-hidden">
              {codeData?.code ? (
                <pre className="p-6 text-sm text-zinc-300 font-mono overflow-x-auto leading-relaxed whitespace-pre">
                  {codeData.code}
                </pre>
              ) : (
                <div className="p-8 text-center">
                  <span className="material-symbols-outlined text-4xl text-zinc-600">code_off</span>
                  <p className="text-zinc-400 mt-2">Code not available</p>
                  <p className="text-zinc-500 text-sm mt-1">Module: {codeData?.module_path ?? activity.code_module_path}</p>
                </div>
              )}
            </div>
          )}

          {tab === 'usage' && (
            <div className="rounded-xl border border-border-dark bg-surface-light/50 overflow-hidden">
              {usageData?.workflows && usageData.workflows.length > 0 ? (
                <div className="divide-y divide-zinc-800">
                  {usageData.workflows.map((w) => (
                    <div key={w.id} className="px-6 py-4 flex items-center justify-between hover:bg-zinc-700/20 transition-colors">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="material-symbols-outlined text-[18px] text-zinc-500">account_tree</span>
                          <span className="text-sm font-medium text-white">{w.name}</span>
                        </div>
                        {w.description && (
                          <p className="text-xs text-zinc-500 mt-1 ml-7">{w.description}</p>
                        )}
                      </div>
                      <Link
                        to={`/workflows/${w.id}`}
                        className="text-primary text-sm hover:underline"
                      >
                        Open
                      </Link>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center">
                  <span className="material-symbols-outlined text-4xl text-zinc-600">link_off</span>
                  <p className="text-zinc-400 mt-2">Not used in any workflows</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
