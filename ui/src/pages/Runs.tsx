import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRuns, useWorkflows } from '../hooks/useTapcraft';
import { formatDistanceToNow } from 'date-fns';

const WORKSPACE_ID = 1;

const Runs = () => {
  const navigate = useNavigate();
  const { data: runs, isLoading, error } = useRuns(WORKSPACE_ID);
  const { data: workflows } = useWorkflows(WORKSPACE_ID);

  const [showFilters, setShowFilters] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [workflowFilter, setWorkflowFilter] = useState<number | null>(null);

  const filteredRuns = (runs ?? []).filter(run => {
    if (statusFilter !== 'all' && run.status !== statusFilter) return false;
    if (workflowFilter !== null && run.workflow_id !== workflowFilter) return false;
    return true;
  });

  const formatDuration = (startedAt: string | null, endedAt: string | null) => {
    if (!startedAt || !endedAt) return '--';
    const ms = new Date(endedAt).getTime() - new Date(startedAt).getTime();
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return (
          <span className="inline-flex items-center gap-1.5 rounded bg-sky-500/10 px-2 py-1 text-xs font-medium text-sky-400 ring-1 ring-inset ring-sky-500/20">
            <span className="animate-spin material-symbols-outlined text-[12px]">progress_activity</span>
            Running
          </span>
        );
      case 'succeeded':
        return (
          <span className="inline-flex items-center gap-1.5 rounded bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/20">
            <span className="material-symbols-outlined text-[12px] icon-filled">check_circle</span>
            Success
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1.5 rounded bg-red-500/10 px-2 py-1 text-xs font-medium text-red-400 ring-1 ring-inset ring-red-500/20">
            <span className="material-symbols-outlined text-[12px] icon-filled">error</span>
            Failed
          </span>
        );
      case 'queued':
        return (
          <span className="inline-flex items-center gap-1.5 rounded bg-amber-500/10 px-2 py-1 text-xs font-medium text-amber-400 ring-1 ring-inset ring-amber-500/20">
            <span className="material-symbols-outlined text-[12px]">schedule</span>
            Queued
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 rounded bg-zinc-500/10 px-2 py-1 text-xs font-medium text-zinc-400 ring-1 ring-inset ring-zinc-500/20">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="w-full px-8 py-6 border-b border-border-dark bg-background-dark sticky top-0 z-10">
        <div className="max-w-[1200px] mx-auto flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-2">
            <h2 className="text-white text-3xl font-bold tracking-tight">Execution History</h2>
            <p className="text-zinc-400 text-base">
              {filteredRuns.length} {filteredRuns.length !== (runs?.length ?? 0) ? `of ${runs?.length ?? 0} ` : 'total '}runs
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center justify-center h-9 px-4 rounded-lg border text-sm font-medium transition-colors ${
                showFilters || statusFilter !== 'all' || workflowFilter !== null
                  ? 'bg-primary/10 border-primary/30 text-primary hover:bg-primary/20'
                  : 'bg-surface-light border-border-dark text-zinc-300 hover:text-white hover:border-zinc-500'
              }`}
            >
              <span className="material-symbols-outlined text-[18px] mr-2">filter_list</span>
              Filter
              {(statusFilter !== 'all' || workflowFilter !== null) && (
                <span className="ml-1.5 bg-primary text-zinc-950 rounded-full w-5 h-5 text-xs font-bold flex items-center justify-center">
                  {(statusFilter !== 'all' ? 1 : 0) + (workflowFilter !== null ? 1 : 0)}
                </span>
              )}
            </button>
            {(statusFilter !== 'all' || workflowFilter !== null) && (
              <button
                onClick={() => { setStatusFilter('all'); setWorkflowFilter(null); }}
                className="flex items-center h-9 px-3 text-xs text-zinc-400 hover:text-white transition-colors"
              >
                Clear filters
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Filters */}
      {showFilters && (
        <div className="px-8 py-4 border-b border-border-dark bg-zinc-900/50">
          <div className="max-w-[1200px] mx-auto flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Status</label>
              <div className="flex items-center gap-1">
                {['all', 'running', 'succeeded', 'failed', 'queued'].map(s => (
                  <button
                    key={s}
                    onClick={() => setStatusFilter(s)}
                    className={`h-7 px-3 rounded-md text-xs font-medium transition-colors ${
                      statusFilter === s
                        ? 'bg-primary text-zinc-950'
                        : 'bg-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-700'
                    }`}
                  >
                    {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Workflow</label>
              <select
                value={workflowFilter ?? ''}
                onChange={(e) => setWorkflowFilter(e.target.value ? Number(e.target.value) : null)}
                className="h-7 px-2 rounded-md text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700 focus:border-primary focus:outline-none"
              >
                <option value="">All workflows</option>
                {workflows?.map(wf => (
                  <option key={wf.id} value={wf.id}>{wf.name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 px-8 py-8 overflow-auto">
        <div className="max-w-[1200px] mx-auto">
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
          ) : error ? (
            <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6">
              <div className="flex items-center gap-3 text-red-400">
                <span className="material-symbols-outlined">error</span>
                <span>Error loading runs: {error.message}</span>
              </div>
            </div>
          ) : filteredRuns.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border-2 border-dashed border-border-dark rounded-xl">
              <div className="w-16 h-16 rounded-full bg-surface-light flex items-center justify-center mb-4">
                <span className="material-symbols-outlined text-3xl text-zinc-500">history</span>
              </div>
              <p className="text-white font-medium">
                {(statusFilter !== 'all' || workflowFilter !== null) ? 'No matching runs' : 'No runs yet'}
              </p>
              <p className="text-zinc-500 text-sm mt-1">
                {(statusFilter !== 'all' || workflowFilter !== null) ? 'Try adjusting your filters' : 'Execute a workflow to see runs here'}
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-border-dark bg-surface-light/50 overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-zinc-900/50 border-b border-border-dark">
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Workflow</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Started</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Duration</th>
                      <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Summary</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800">
                    {filteredRuns.map((run) => (
                      <tr key={run.id} onClick={() => navigate(`/runs/${run.id}`)} className="hover:bg-zinc-700/20 transition-colors cursor-pointer">
                        <td className="px-6 py-4">{getStatusBadge(run.status)}</td>
                        <td className="px-6 py-4">
                          <div className="flex flex-col">
                            <span className="text-sm font-medium text-white">
                              Workflow {run.workflow_id}
                            </span>
                            <span className="text-xs text-zinc-500 font-mono">#{run.id}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-zinc-400">
                          {run.started_at
                            ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true })
                            : '--'}
                        </td>
                        <td className="px-6 py-4 text-sm text-zinc-300 font-mono">
                          {run.status === 'running' ? (
                            <span className="text-sky-400">...</span>
                          ) : (
                            formatDuration(run.started_at, run.ended_at)
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm text-zinc-400 max-w-xs truncate">
                          {run.error_excerpt ? (
                            <span className="text-red-400">{run.error_excerpt}</span>
                          ) : run.summary ? (
                            run.summary
                          ) : (
                            '--'
                          )}
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

export default Runs;
