import { Link, useParams } from 'react-router-dom';
import { useRunStatus } from '../hooks/useTapcraft';
import { formatDistanceToNow } from 'date-fns';
import type { ActivityHistoryEntry } from '../types/tapcraft';

const formatDuration = (startedAt: string | null | undefined, endedAt: string | null | undefined) => {
  if (!startedAt || !endedAt) return '--';
  const ms = new Date(endedAt).getTime() - new Date(startedAt).getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <span className="material-symbols-outlined text-[20px] icon-filled text-emerald-400">check_circle</span>;
    case 'failed':
      return <span className="material-symbols-outlined text-[20px] icon-filled text-red-400">error</span>;
    case 'running':
      return <span className="material-symbols-outlined text-[20px] animate-spin text-sky-400">progress_activity</span>;
    case 'timed_out':
      return <span className="material-symbols-outlined text-[20px] icon-filled text-amber-400">timer_off</span>;
    default:
      return <span className="material-symbols-outlined text-[20px] text-zinc-500">circle</span>;
  }
};

const getRunStatusBadge = (status: string) => {
  switch (status) {
    case 'running':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-500/10 px-3 py-1 text-sm font-medium text-sky-400 ring-1 ring-inset ring-sky-500/20">
          <span className="animate-spin material-symbols-outlined text-[14px]">progress_activity</span>
          Running
        </span>
      );
    case 'succeeded':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-sm font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/20">
          <span className="material-symbols-outlined text-[14px] icon-filled">check_circle</span>
          Succeeded
        </span>
      );
    case 'failed':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-red-500/10 px-3 py-1 text-sm font-medium text-red-400 ring-1 ring-inset ring-red-500/20">
          <span className="material-symbols-outlined text-[14px] icon-filled">error</span>
          Failed
        </span>
      );
    case 'queued':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-3 py-1 text-sm font-medium text-amber-400 ring-1 ring-inset ring-amber-500/20">
          <span className="material-symbols-outlined text-[14px]">schedule</span>
          Queued
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-zinc-500/10 px-3 py-1 text-sm font-medium text-zinc-400 ring-1 ring-inset ring-zinc-500/20">
          {status}
        </span>
      );
  }
};

function ActivityTimeline({ activities }: { activities: ActivityHistoryEntry[] }) {
  if (activities.length === 0) {
    return (
      <div className="p-8 text-center">
        <span className="material-symbols-outlined text-4xl text-zinc-600">timeline</span>
        <p className="text-zinc-400 mt-2">No activity history available</p>
        <p className="text-zinc-500 text-sm mt-1">Activity steps will appear here during execution</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-zinc-800">
      {activities.map((activity, index) => (
        <div key={index} className="px-6 py-4 hover:bg-zinc-700/20 transition-colors">
          <div className="flex items-start gap-4">
            {/* Status icon + connector line */}
            <div className="flex flex-col items-center pt-0.5">
              {getStatusIcon(activity.status)}
              {index < activities.length - 1 && (
                <div className="w-px h-full min-h-[16px] bg-zinc-700 mt-1" />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-white">{activity.activity_name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    activity.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                    activity.status === 'failed' ? 'bg-red-500/10 text-red-400' :
                    activity.status === 'running' ? 'bg-sky-500/10 text-sky-400' :
                    'bg-amber-500/10 text-amber-400'
                  }`}>
                    {activity.status}
                  </span>
                </div>
                <span className="text-xs text-zinc-500 font-mono">
                  {formatDuration(activity.started_at, activity.ended_at)}
                </span>
              </div>

              {activity.error && (
                <div className="mt-2 p-3 rounded-lg bg-red-500/5 border border-red-500/20">
                  <p className="text-sm text-red-400 font-mono break-all">{activity.error}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const runId = Number(id);
  const { data: runStatus, isLoading } = useRunStatus(runId);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex items-center gap-3 text-zinc-400">
          <span className="material-symbols-outlined animate-spin">progress_activity</span>
          Loading run details...
        </div>
      </div>
    );
  }

  if (!runStatus) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <span className="material-symbols-outlined text-4xl text-zinc-700">error</span>
          <p className="text-zinc-400 text-sm mt-2">Run not found</p>
          <Link to="/runs" className="text-primary text-sm mt-2 inline-block hover:underline">
            Back to runs
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="w-full px-8 py-6 border-b border-border-dark bg-background-dark">
        <div className="max-w-[1200px] mx-auto">
          <div className="flex items-center gap-2 text-sm text-zinc-500 mb-3">
            <Link to="/runs" className="hover:text-zinc-300 transition-colors">Runs</Link>
            <span className="material-symbols-outlined text-[14px]">chevron_right</span>
            <span className="text-zinc-300">Run #{runStatus.run_id}</span>
          </div>

          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-4">
                <h2 className="text-white text-3xl font-bold tracking-tight">
                  Run #{runStatus.run_id}
                </h2>
                {getRunStatusBadge(runStatus.status)}
              </div>
              <div className="flex items-center gap-4 mt-2 text-sm text-zinc-400">
                {runStatus.workflow_name && (
                  <Link
                    to={`/workflows/${runStatus.workflow_id}`}
                    className="flex items-center gap-1.5 hover:text-primary transition-colors"
                  >
                    <span className="material-symbols-outlined text-[16px]">account_tree</span>
                    {runStatus.workflow_name}
                  </Link>
                )}
                {runStatus.started_at && (
                  <span className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[16px]">schedule</span>
                    {formatDistanceToNow(new Date(runStatus.started_at), { addSuffix: true })}
                  </span>
                )}
                <span className="flex items-center gap-1.5 font-mono">
                  <span className="material-symbols-outlined text-[16px]">timer</span>
                  {formatDuration(runStatus.started_at, runStatus.ended_at)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 px-8 py-8 overflow-auto">
        <div className="max-w-[1200px] mx-auto flex flex-col gap-6">
          {/* Metadata Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="rounded-xl border border-border-dark bg-surface-light/50 p-4">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Status</div>
              <div className="text-sm font-medium text-white capitalize">{runStatus.status}</div>
            </div>
            <div className="rounded-xl border border-border-dark bg-surface-light/50 p-4">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Duration</div>
              <div className="text-sm font-medium text-white font-mono">
                {formatDuration(runStatus.started_at, runStatus.ended_at)}
              </div>
            </div>
            <div className="rounded-xl border border-border-dark bg-surface-light/50 p-4">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Steps</div>
              <div className="text-sm font-medium text-white">
                {runStatus.activity_history?.length ?? 0}
              </div>
            </div>
            <div className="rounded-xl border border-border-dark bg-surface-light/50 p-4">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Temporal ID</div>
              <div className="text-sm font-medium text-zinc-300 font-mono truncate" title={runStatus.temporal_workflow_id ?? ''}>
                {runStatus.temporal_workflow_id ?? '--'}
              </div>
            </div>
          </div>

          {/* Activity Timeline */}
          <div>
            <h3 className="text-white text-lg font-semibold mb-3 flex items-center gap-2">
              <span className="material-symbols-outlined text-[20px]">timeline</span>
              Activity Timeline
            </h3>
            <div className="rounded-xl border border-border-dark bg-surface-light/50 overflow-hidden">
              <ActivityTimeline activities={runStatus.activity_history ?? []} />
            </div>
          </div>

          {/* Error Section */}
          {runStatus.error_excerpt && (
            <div>
              <h3 className="text-red-400 text-lg font-semibold mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px]">bug_report</span>
                Error Details
              </h3>
              <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-6">
                <pre className="text-sm text-red-400 font-mono whitespace-pre-wrap break-all">
                  {runStatus.error_excerpt}
                </pre>
              </div>
            </div>
          )}

          {/* Summary Section */}
          {runStatus.summary && (
            <div>
              <h3 className="text-white text-lg font-semibold mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px]">summarize</span>
                Summary
              </h3>
              <div className="rounded-xl border border-border-dark bg-surface-light/50 p-6">
                <p className="text-sm text-zinc-300">{runStatus.summary}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
