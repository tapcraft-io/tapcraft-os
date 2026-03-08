import { useState, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useRunStatus, apiFetch } from '../hooks/useTapcraft';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow, format } from 'date-fns';
import type { ActivityHistoryEntry } from '../types/tapcraft';

// ============================================================================
// Helpers
// ============================================================================

const formatDuration = (startedAt: string | null | undefined, endedAt: string | null | undefined) => {
  if (!startedAt || !endedAt) return '--';
  const ms = new Date(endedAt).getTime() - new Date(startedAt).getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
};

const formatTimestamp = (ts: string | null | undefined) => {
  if (!ts) return '--';
  return format(new Date(ts), 'MMM d, yyyy HH:mm:ss.SSS');
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
    case 'cancelled':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-zinc-500/10 px-3 py-1 text-sm font-medium text-zinc-400 ring-1 ring-inset ring-zinc-500/20">
          <span className="material-symbols-outlined text-[14px] icon-filled">cancel</span>
          Cancelled
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

const getActivityStatusBadge = (status: string) => {
  const base = 'text-xs px-2 py-0.5 rounded-full font-medium';
  switch (status) {
    case 'completed':
      return <span className={`${base} bg-emerald-500/10 text-emerald-400`}>{status}</span>;
    case 'failed':
      return <span className={`${base} bg-red-500/10 text-red-400`}>{status}</span>;
    case 'running':
      return <span className={`${base} bg-sky-500/10 text-sky-400`}>{status}</span>;
    case 'timed_out':
      return <span className={`${base} bg-amber-500/10 text-amber-400`}>{status}</span>;
    default:
      return <span className={`${base} bg-zinc-500/10 text-zinc-400`}>{status}</span>;
  }
};

// ============================================================================
// JSON Viewer Component
// ============================================================================

function JsonViewer({ data, label }: { data: unknown; label: string }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const jsonString = JSON.stringify(data, null, 2);
  const lines = jsonString.split('\n');
  const isLong = lines.length > 3;
  const displayLines = expanded || !isLong ? lines : lines.slice(0, 3);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(jsonString).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [jsonString]);

  // Syntax highlighting for JSON
  const highlightJson = (line: string) => {
    return line.replace(
      /("(?:\\.|[^"\\])*")\s*:/g,
      '<span class="text-sky-400">$1</span>:'
    ).replace(
      /:\s*("(?:\\.|[^"\\])*")/g,
      ': <span class="text-emerald-400">$1</span>'
    ).replace(
      /:\s*(\d+\.?\d*)/g,
      ': <span class="text-amber-400">$1</span>'
    ).replace(
      /:\s*(true|false)/g,
      ': <span class="text-purple-400">$1</span>'
    ).replace(
      /:\s*(null)/g,
      ': <span class="text-zinc-500">$1</span>'
    );
  };

  return (
    <div className="mt-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">{label}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <span className="material-symbols-outlined text-[14px]">
            {copied ? 'check' : 'content_copy'}
          </span>
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <div className="rounded-lg bg-zinc-900 border border-zinc-800 p-3 font-mono text-xs leading-relaxed overflow-x-auto">
        {displayLines.map((line, i) => (
          <div
            key={i}
            className="text-zinc-300"
            dangerouslySetInnerHTML={{ __html: highlightJson(line) }}
          />
        ))}
        {isLong && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-1 text-xs text-sky-400 hover:text-sky-300 transition-colors flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[14px]">
              {expanded ? 'expand_less' : 'expand_more'}
            </span>
            {expanded ? 'Show less' : `Show more (${lines.length - 3} more lines)`}
          </button>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Activity Card Component
// ============================================================================

function ActivityCard({ activity, index, totalCount }: {
  activity: ActivityHistoryEntry;
  index: number;
  totalCount: number;
}) {
  const [isOpen, setIsOpen] = useState(false);

  const queueWait = activity.scheduled_at && activity.started_at
    ? formatDuration(activity.scheduled_at, activity.started_at)
    : null;

  const executionTime = activity.started_at && activity.ended_at
    ? formatDuration(activity.started_at, activity.ended_at)
    : null;

  const hasInput = activity.input !== undefined && activity.input !== null;
  const hasOutput = activity.output !== undefined && activity.output !== null;
  const hasError = activity.status === 'failed' && (activity.error || activity.error_type || activity.stack_trace);

  return (
    <div className="group">
      {/* Header row — always visible, clickable */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 hover:bg-zinc-700/20 transition-colors text-left"
      >
        <div className="flex items-start gap-4">
          {/* Status icon + connector line */}
          <div className="flex flex-col items-center pt-0.5">
            {getStatusIcon(activity.status)}
            {index < totalCount - 1 && (
              <div className="w-px h-full min-h-[16px] bg-zinc-700 mt-1" />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-sm font-medium text-white">{activity.activity_name}</span>
                {getActivityStatusBadge(activity.status)}
                {activity.attempt !== undefined && activity.attempt > 1 && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-700/50 text-zinc-400 font-medium">
                    Attempt {activity.attempt}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-xs text-zinc-500 font-mono">
                  {formatDuration(activity.started_at, activity.ended_at)}
                </span>
                <span className="material-symbols-outlined text-[16px] text-zinc-500 transition-transform duration-200"
                  style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}
                >
                  expand_more
                </span>
              </div>
            </div>
          </div>
        </div>
      </button>

      {/* Expanded section */}
      {isOpen && (
        <div className="px-6 pb-5 pl-[3.75rem]">
          <div className="flex flex-col gap-4">
            {/* Timing breakdown */}
            <div className="rounded-lg border border-border-dark bg-zinc-800/30 p-4">
              <h4 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px]">schedule</span>
                Timing
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-zinc-500 text-xs mb-0.5">Scheduled at</div>
                  <div className="text-zinc-300 font-mono text-xs">{formatTimestamp(activity.scheduled_at)}</div>
                </div>
                <div>
                  <div className="text-zinc-500 text-xs mb-0.5">Started at</div>
                  <div className="text-zinc-300 font-mono text-xs">{formatTimestamp(activity.started_at)}</div>
                </div>
                <div>
                  <div className="text-zinc-500 text-xs mb-0.5">Ended at</div>
                  <div className="text-zinc-300 font-mono text-xs">{formatTimestamp(activity.ended_at)}</div>
                </div>
                {queueWait && (
                  <div>
                    <div className="text-zinc-500 text-xs mb-0.5">Queue wait</div>
                    <div className="text-amber-400 font-mono text-xs">{queueWait}</div>
                  </div>
                )}
                {executionTime && (
                  <div>
                    <div className="text-zinc-500 text-xs mb-0.5">Execution time</div>
                    <div className="text-emerald-400 font-mono text-xs">{executionTime}</div>
                  </div>
                )}
              </div>
            </div>

            {/* Retry info */}
            {(activity.retry_state || (activity.attempt !== undefined && activity.attempt > 1)) && (
              <div className="rounded-lg border border-border-dark bg-zinc-800/30 p-4">
                <h4 className="text-xs font-medium text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[14px]">replay</span>
                  Retry Info
                </h4>
                <div className="flex gap-6 text-sm">
                  {activity.attempt !== undefined && (
                    <div>
                      <div className="text-zinc-500 text-xs mb-0.5">Attempt</div>
                      <div className="text-zinc-300 font-mono text-xs">{activity.attempt}</div>
                    </div>
                  )}
                  {activity.retry_state && (
                    <div>
                      <div className="text-zinc-500 text-xs mb-0.5">Retry State</div>
                      <div className="text-zinc-300 font-mono text-xs">{activity.retry_state}</div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Input */}
            {hasInput && (
              <JsonViewer data={activity.input} label="Input" />
            )}

            {/* Output */}
            {hasOutput && (
              <JsonViewer data={activity.output} label="Output" />
            )}

            {/* Error details */}
            {hasError && (
              <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
                <h4 className="text-xs font-medium text-red-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[14px]">bug_report</span>
                  Error Details
                </h4>
                {activity.error_type && (
                  <div className="mb-2">
                    <span className="text-xs text-zinc-500">Type: </span>
                    <span className="text-xs text-red-400 font-mono">{activity.error_type}</span>
                  </div>
                )}
                {activity.error && (
                  <pre className="text-sm text-red-400 font-mono whitespace-pre-wrap break-all mb-2">
                    {activity.error}
                  </pre>
                )}
                {activity.stack_trace && (
                  <details className="mt-2">
                    <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-400 transition-colors">
                      Stack Trace
                    </summary>
                    <pre className="mt-2 text-xs text-red-400/80 font-mono whitespace-pre-wrap break-all max-h-[300px] overflow-auto">
                      {activity.stack_trace}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Activity Timeline
// ============================================================================

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
        <ActivityCard
          key={index}
          activity={activity}
          index={index}
          totalCount={activities.length}
        />
      ))}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const runId = Number(id);
  const queryClient = useQueryClient();
  const { data: runStatus, isLoading } = useRunStatus(runId);

  const retryMutation = useMutation({
    mutationFn: () => apiFetch<unknown>(`/runs/${runId}/retry`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: ['runs', runId, 'status'] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => apiFetch<unknown>(`/runs/${runId}/cancel`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: ['runs', runId, 'status'] });
    },
  });

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

  const isTerminal = runStatus.status === 'failed' || runStatus.status === 'cancelled';
  const isActive = runStatus.status === 'running' || runStatus.status === 'queued';

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

            {/* Action buttons */}
            <div className="flex items-center gap-2 shrink-0">
              {isTerminal && (
                <button
                  onClick={() => retryMutation.mutate()}
                  disabled={retryMutation.isPending}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-sky-500/10 px-4 py-2 text-sm font-medium text-sky-400 ring-1 ring-inset ring-sky-500/20 hover:bg-sky-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span className="material-symbols-outlined text-[16px]">
                    {retryMutation.isPending ? 'progress_activity' : 'replay'}
                  </span>
                  {retryMutation.isPending ? 'Retrying...' : 'Retry'}
                </button>
              )}
              {isActive && (
                <button
                  onClick={() => cancelMutation.mutate()}
                  disabled={cancelMutation.isPending}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-red-500/10 px-4 py-2 text-sm font-medium text-red-400 ring-1 ring-inset ring-red-500/20 hover:bg-red-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span className="material-symbols-outlined text-[16px]">
                    {cancelMutation.isPending ? 'progress_activity' : 'cancel'}
                  </span>
                  {cancelMutation.isPending ? 'Cancelling...' : 'Cancel'}
                </button>
              )}
            </div>
          </div>

          {/* Mutation error feedback */}
          {retryMutation.isError && (
            <div className="mt-3 text-sm text-red-400 flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[14px]">error</span>
              Retry failed: {retryMutation.error?.message}
            </div>
          )}
          {cancelMutation.isError && (
            <div className="mt-3 text-sm text-red-400 flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[14px]">error</span>
              Cancel failed: {cancelMutation.error?.message}
            </div>
          )}
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
