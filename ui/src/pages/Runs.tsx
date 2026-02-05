import { PlayIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/outline';
import { useRuns } from '../hooks/useTapcraft';
import { formatDistanceToNow } from 'date-fns';

const WORKSPACE_ID = 1; // TODO: Get from context

const statusIcons = {
  queued: ClockIcon,
  running: ClockIcon,
  succeeded: CheckCircleIcon,
  failed: XCircleIcon,
};

const statusColors = {
  queued: 'text-slate-400',
  running: 'text-blue-400',
  succeeded: 'text-green-400',
  failed: 'text-red-400',
};

const Runs = () => {
  const { data: runs, isLoading, error } = useRuns(WORKSPACE_ID);

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-slate-800 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-400">
          Error loading runs: {error.message}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold flex items-center gap-3">
          <PlayIcon className="h-7 w-7 text-green-500" />
          Runs
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Workflow execution history and status
        </p>
      </div>

      {/* Runs List */}
      {runs && runs.length === 0 ? (
        <div className="text-center py-12 bg-slate-900/30 rounded-lg border border-slate-800">
          <PlayIcon className="h-12 w-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">No runs yet</p>
          <p className="text-sm text-slate-500 mt-1">
            Execute a workflow to see runs here
          </p>
        </div>
      ) : (
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-900/80 border-b border-slate-800">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Workflow
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Started
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Summary
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {runs?.map((run) => {
                const StatusIcon = statusIcons[run.status];
                const duration =
                  run.started_at && run.ended_at
                    ? Math.round(
                        (new Date(run.ended_at).getTime() - new Date(run.started_at).getTime()) /
                          1000
                      )
                    : null;

                return (
                  <tr key={run.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 text-sm">
                      <span className="font-mono text-slate-400">#{run.id}</span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className="text-slate-300">Workflow {run.workflow_id}</span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        <StatusIcon className={`h-4 w-4 ${statusColors[run.status]}`} />
                        <span className={statusColors[run.status]}>{run.status}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-400">
                      {run.started_at
                        ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true })
                        : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-400">
                      {duration ? `${duration}s` : run.status === 'running' ? '...' : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-400">
                      {run.error_excerpt ? (
                        <span className="text-red-400 text-xs">{run.error_excerpt.slice(0, 50)}...</span>
                      ) : run.summary ? (
                        run.summary.slice(0, 50)
                      ) : (
                        '-'
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default Runs;
