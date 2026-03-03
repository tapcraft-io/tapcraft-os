import { useState } from 'react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { useWorkflows, useRuns } from '../hooks/useTapcraft';
import type { Workflow, Run } from '../types/tapcraft';

const WORKSPACE_ID = 1;

const WorkflowsPage = () => {
  const [selected, setSelected] = useState<Workflow | undefined>();

  const { data: workflows, isLoading, error } = useWorkflows(WORKSPACE_ID);

  const { data: runs } = useRuns(WORKSPACE_ID, selected?.id);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return (
          <span className="inline-flex items-center gap-1 rounded bg-sky-500/10 px-1.5 py-0.5 text-xs font-medium text-sky-400 ring-1 ring-inset ring-sky-500/20">
            <span className="animate-spin material-symbols-outlined text-[10px]">progress_activity</span>
            Running
          </span>
        );
      case 'succeeded':
        return (
          <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 px-1.5 py-0.5 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/20">
            <span className="material-symbols-outlined text-[10px] icon-filled">check_circle</span>
            Success
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 rounded bg-red-500/10 px-1.5 py-0.5 text-xs font-medium text-red-400 ring-1 ring-inset ring-red-500/20">
            <span className="material-symbols-outlined text-[10px] icon-filled">error</span>
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded bg-zinc-500/10 px-1.5 py-0.5 text-xs font-medium text-zinc-400 ring-1 ring-inset ring-zinc-500/20">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="flex h-full">
      {/* Workflow List */}
      <div className="flex-1 flex flex-col border-r border-border-dark">
        {/* Header */}
        <header className="px-6 py-4 border-b border-border-dark bg-background-dark">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-white text-xl font-bold tracking-tight">Workflows</h2>
              <p className="text-zinc-500 text-sm">{workflows?.length ?? 0} workflows</p>
            </div>
            <Link
              to="/workflows"
              className="flex items-center gap-2 h-9 px-4 bg-primary text-zinc-950 text-sm font-bold rounded-lg hover:bg-primary/90 transition-colors"
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
              New
            </Link>
          </div>
        </header>

        {/* List */}
        <div className="flex-1 overflow-auto p-4">
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse p-4 rounded-xl bg-surface-light border border-border-dark">
                  <div className="h-4 w-1/3 bg-zinc-700 rounded mb-2" />
                  <div className="h-3 w-2/3 bg-zinc-800 rounded" />
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4">
              <div className="flex items-center gap-2 text-red-400 text-sm">
                <span className="material-symbols-outlined text-[18px]">error</span>
                Error loading workflows
              </div>
            </div>
          ) : workflows && workflows.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 border-2 border-dashed border-border-dark rounded-xl">
              <span className="material-symbols-outlined text-3xl text-zinc-600 mb-2">account_tree</span>
              <p className="text-zinc-400 text-sm">No workflows yet</p>
              <Link to="/workflows" className="mt-3 text-primary text-sm font-medium hover:underline">
                Create your first workflow
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {workflows?.map((workflow) => (
                <div
                  key={workflow.id}
                  onClick={() => setSelected(workflow)}
                  className={`w-full text-left p-4 rounded-xl border transition-colors cursor-pointer ${
                    selected?.id === workflow.id
                      ? 'bg-primary/10 border-primary/30 text-white'
                      : 'bg-surface-light border-border-dark hover:border-zinc-600 text-zinc-300'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`material-symbols-outlined text-[18px] ${selected?.id === workflow.id ? 'text-primary' : 'text-zinc-500'}`}>
                          account_tree
                        </span>
                        <span className="font-medium truncate">{workflow.name}</span>
                      </div>
                      {workflow.description && (
                        <p className="text-sm text-zinc-500 mt-1 line-clamp-1">{workflow.description}</p>
                      )}
                      <div className="flex items-center gap-3 mt-2 text-xs text-zinc-500">
                        <span className="font-mono">{workflow.slug}</span>
                        <Link
                          to={`/workflows/${workflow.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 text-primary hover:underline"
                        >
                          <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                          Open Editor
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Inspector Panel */}
      <div className="w-96 flex flex-col bg-surface-dark">
        <header className="px-6 py-4 border-b border-border-dark">
          <h3 className="text-white font-medium">
            {selected ? selected.name : 'Select a workflow'}
          </h3>
        </header>

        {selected ? (
          <div className="flex-1 overflow-auto">
            {/* Workflow Details */}
            <div className="p-6 border-b border-border-dark">
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wider">Slug</label>
                  <p className="text-sm text-zinc-300 font-mono mt-1">{selected.slug}</p>
                </div>
                {selected.description && (
                  <div>
                    <label className="text-xs text-zinc-500 uppercase tracking-wider">Description</label>
                    <p className="text-sm text-zinc-300 mt-1">{selected.description}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Recent Runs */}
            <div className="p-6">
              <h4 className="text-xs text-zinc-500 uppercase tracking-wider mb-3">Recent Runs</h4>
              {runs && runs.length > 0 ? (
                <div className="space-y-2">
                  {runs.slice(0, 5).map((run) => (
                    <div key={run.id} className="flex items-center justify-between p-3 rounded-lg bg-zinc-900/50 border border-zinc-800">
                      <div className="flex items-center gap-3">
                        {getStatusBadge(run.status)}
                        <span className="text-xs text-zinc-500 font-mono">#{run.id}</span>
                      </div>
                      <span className="text-xs text-zinc-500">
                        {run.started_at
                          ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true })
                          : '--'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-zinc-500">No runs yet</p>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <span className="material-symbols-outlined text-4xl text-zinc-700">touch_app</span>
              <p className="text-zinc-500 text-sm mt-2">Select a workflow to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkflowsPage;
