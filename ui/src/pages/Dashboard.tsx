import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { useRuns, useHealth, useWorkflowHealth, useTerminateStuck, useWorkflows, useActivities, useSchedules } from '../hooks/useTapcraft';
import type { Run } from '../types/tapcraft';

const WORKSPACE_ID = 1;

const Dashboard = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { data: health } = useHealth();
  const { data: wfHealth } = useWorkflowHealth();
  const terminateStuck = useTerminateStuck();
  const { data: runs } = useRuns(WORKSPACE_ID);
  const { data: workflows } = useWorkflows(WORKSPACE_ID);
  const { data: activities } = useActivities(WORKSPACE_ID);
  const { data: schedules } = useSchedules(WORKSPACE_ID);

  const recentRuns = (runs ?? []).slice(0, 5);
  const activeSchedules = (schedules ?? []).filter(s => s.enabled);
  const upcomingSchedules = activeSchedules
    .filter(s => s.next_run_at)
    .sort((a, b) => new Date(a.next_run_at!).getTime() - new Date(b.next_run_at!).getTime())
    .slice(0, 5);

  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const formatDuration = (run: Run) => {
    if (!run.started_at || !run.ended_at) return '--';
    const ms = new Date(run.ended_at).getTime() - new Date(run.started_at).getTime();
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  const formatTime = (run: Run) => {
    if (!run.started_at) return '--';
    const diff = Date.now() - new Date(run.started_at).getTime();
    if (diff < 60000) return 'Now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return `${Math.floor(diff / 86400000)}d ago`;
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
      default:
        return (
          <span className="inline-flex items-center gap-1.5 rounded bg-zinc-500/10 px-2 py-1 text-xs font-medium text-zinc-400 ring-1 ring-inset ring-zinc-500/20">
            <span className="material-symbols-outlined text-[12px]">schedule</span>
            {status}
          </span>
        );
    }
  };

  return (
    <div className="max-w-[1400px] w-full mx-auto p-6 md:p-8 flex flex-col gap-8">
      {/* Page Header */}
      <header className="flex flex-wrap justify-between items-end gap-4">
        <div className="flex flex-col gap-1">
          <p className="text-zinc-400 text-sm font-medium">{format(new Date(), 'MMMM d, yyyy')}</p>
          <h2 className="text-white text-3xl font-bold tracking-tight">{greeting()}</h2>
          <div className="flex items-center gap-2 mt-1">
            {health?.status === 'ok' && wfHealth?.status === 'healthy' ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <p className="text-emerald-500 text-sm font-medium">All systems nominal</p>
              </>
            ) : wfHealth?.status === 'unhealthy' ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                </span>
                <p className="text-red-400 text-sm font-medium">
                  {wfHealth.unhealthy_workflows.length} unhealthy workflow{wfHealth.unhealthy_workflows.length !== 1 ? 's' : ''}
                </p>
              </>
            ) : wfHealth?.status === 'degraded' ? (
              <>
                <span className="flex h-2 w-2 rounded-full bg-amber-500"></span>
                <p className="text-amber-500 text-sm font-medium">Workflows degraded</p>
              </>
            ) : (
              <>
                <span className="flex h-2 w-2 rounded-full bg-amber-500"></span>
                <p className="text-amber-500 text-sm font-medium">Connecting...</p>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => queryClient.invalidateQueries()}
            className="flex items-center justify-center h-9 px-4 rounded-lg bg-surface-light border border-border-dark text-zinc-300 hover:text-white hover:border-zinc-500 text-sm font-medium transition-colors"
          >
            <span className="material-symbols-outlined text-[18px] mr-2">refresh</span>
            Refresh
          </button>
        </div>
      </header>

      {/* Counts Row */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div
          onClick={() => navigate('/workflows')}
          className="bg-surface-light border border-border-dark rounded-xl p-5 flex items-center gap-4 hover:border-zinc-500 transition-colors cursor-pointer"
        >
          <div className="p-2 bg-violet-500/10 rounded-lg text-violet-400 border border-violet-500/20">
            <span className="material-symbols-outlined">account_tree</span>
          </div>
          <div>
            <p className="text-white text-2xl font-bold tracking-tight">{workflows?.length ?? 0}</p>
            <p className="text-zinc-400 text-sm font-medium">Workflows</p>
          </div>
        </div>
        <div
          onClick={() => navigate('/activities')}
          className="bg-surface-light border border-border-dark rounded-xl p-5 flex items-center gap-4 hover:border-zinc-500 transition-colors cursor-pointer"
        >
          <div className="p-2 bg-sky-500/10 rounded-lg text-sky-400 border border-sky-500/20">
            <span className="material-symbols-outlined">extension</span>
          </div>
          <div>
            <p className="text-white text-2xl font-bold tracking-tight">{activities?.length ?? 0}</p>
            <p className="text-zinc-400 text-sm font-medium">Activities</p>
          </div>
        </div>
        <div
          onClick={() => navigate('/runs')}
          className="bg-surface-light border border-border-dark rounded-xl p-5 flex items-center gap-4 hover:border-zinc-500 transition-colors cursor-pointer"
        >
          <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400 border border-emerald-500/20">
            <span className="material-symbols-outlined">play_circle</span>
          </div>
          <div>
            <p className="text-white text-2xl font-bold tracking-tight">{runs?.length ?? 0}</p>
            <p className="text-zinc-400 text-sm font-medium">Total Runs</p>
          </div>
        </div>
        <div className="bg-surface-light border border-border-dark rounded-xl p-5 flex items-center gap-4 hover:border-zinc-500 transition-colors">
          <div className="p-2 bg-amber-500/10 rounded-lg text-amber-400 border border-amber-500/20">
            <span className="material-symbols-outlined">schedule</span>
          </div>
          <div>
            <p className="text-white text-2xl font-bold tracking-tight">{activeSchedules.length}</p>
            <p className="text-zinc-400 text-sm font-medium">Active Schedules</p>
          </div>
        </div>
      </section>

      {/* System Status */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Temporal Server */}
        <div className="bg-surface-light border border-border-dark rounded-xl p-5 flex flex-col gap-3 hover:border-zinc-500 transition-colors">
          <div className="flex justify-between items-start">
            <div className="p-2 bg-zinc-900 rounded-lg text-white border border-zinc-700">
              <span className="material-symbols-outlined">dns</span>
            </div>
            <span className={`flex h-2 w-2 rounded-full ${health?.temporal?.connected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-amber-500'}`}></span>
          </div>
          <div>
            <p className="text-zinc-400 text-sm font-medium mb-1">Temporal Server</p>
            <p className="text-white text-2xl font-bold tracking-tight">
              {health?.temporal?.connected ? 'Connected' : 'Connecting...'}
            </p>
          </div>
          <div className="pt-2 border-t border-zinc-700/50 mt-1">
            <p className="text-zinc-400 text-xs font-medium flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px]">dns</span>
              Namespace: {health?.temporal?.namespace ?? 'default'}
            </p>
          </div>
        </div>

        {/* Background Worker */}
        <div className="bg-surface-light border border-border-dark rounded-xl p-5 flex flex-col gap-3 hover:border-zinc-500 transition-colors">
          <div className="flex justify-between items-start">
            <div className="p-2 bg-zinc-900 rounded-lg text-white border border-zinc-700">
              <span className="material-symbols-outlined">precision_manufacturing</span>
            </div>
            <span className={`flex h-2 w-2 rounded-full ${health?.worker?.active !== false ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-amber-500'}`}></span>
          </div>
          <div>
            <p className="text-zinc-400 text-sm font-medium mb-1">Background Worker</p>
            <p className="text-white text-2xl font-bold tracking-tight">
              {health?.worker?.active !== false ? 'Active' : 'Inactive'}
            </p>
          </div>
          <div className="pt-2 border-t border-zinc-700/50 mt-1">
            <p className="text-zinc-400 text-xs font-medium flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px]">ecg_heart</span>
              Heartbeat: {health?.worker?.heartbeat_interval ?? 10}s
            </p>
          </div>
        </div>

        {/* Git Sync */}
        <div className="bg-surface-light border border-border-dark rounded-xl p-5 flex flex-col gap-3 hover:border-zinc-500 transition-colors">
          <div className="flex justify-between items-start">
            <div className="p-2 bg-zinc-900 rounded-lg text-white border border-zinc-700">
              <span className="material-symbols-outlined">sync_alt</span>
            </div>
            <span className="flex h-2 w-2 rounded-full bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.5)]"></span>
          </div>
          <div>
            <p className="text-zinc-400 text-sm font-medium mb-1">Git Sync</p>
            <p className="text-white text-2xl font-bold tracking-tight">Synced</p>
          </div>
          <div className="pt-2 border-t border-zinc-700/50 mt-1">
            <p className="text-zinc-400 text-xs font-medium flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px]">call_split</span>
              Branch: main
            </p>
          </div>
        </div>
      </section>

      {/* Unhealthy Workflows Alert */}
      {wfHealth && wfHealth.unhealthy_workflows.length > 0 && (
        <section className="bg-red-500/5 border border-red-500/20 rounded-xl p-5 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-500/10 rounded-lg text-red-400 border border-red-500/20">
                <span className="material-symbols-outlined">warning</span>
              </div>
              <div>
                <h3 className="text-red-400 font-bold">
                  {wfHealth.unhealthy_workflows.length} Stuck Workflow{wfHealth.unhealthy_workflows.length !== 1 ? 's' : ''} Detected
                </h3>
                <p className="text-red-400/70 text-sm">
                  These workflows have activities retrying beyond the safety threshold
                </p>
              </div>
            </div>
            <button
              onClick={() => terminateStuck.mutate(undefined)}
              disabled={terminateStuck.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 hover:text-red-300 text-sm font-medium transition-colors disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-[16px]">
                {terminateStuck.isPending ? 'progress_activity' : 'stop_circle'}
              </span>
              {terminateStuck.isPending ? 'Terminating...' : 'Terminate All Stuck'}
            </button>
          </div>
          {terminateStuck.isSuccess && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-4 py-2 text-emerald-400 text-sm">
              Terminated {terminateStuck.data.terminated_count} workflow{terminateStuck.data.terminated_count !== 1 ? 's' : ''}
            </div>
          )}
          <div className="space-y-2">
            {wfHealth.unhealthy_workflows.map((wf) => (
              <div key={wf.workflow_id} className="bg-zinc-900/50 rounded-lg px-4 py-3 flex items-center justify-between">
                <div className="flex flex-col gap-0.5">
                  <span className="text-white text-sm font-medium font-mono">{wf.workflow_id}</span>
                  <span className="text-zinc-500 text-xs">{wf.workflow_type}</span>
                </div>
                <div className="flex flex-col items-end gap-0.5">
                  {wf.issues.map((issue, i) => (
                    <span key={i} className="text-red-400/80 text-xs">{issue}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Recent Activity */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h3 className="text-white text-lg font-bold tracking-tight">Recent Activity</h3>
          <span className="inline-flex items-center rounded-full bg-zinc-800 px-2 py-1 text-xs font-medium text-zinc-400 ring-1 ring-inset ring-zinc-700/50">
            Last 24 hours
          </span>
        </div>
        <div className="bg-surface-light border border-border-dark rounded-xl overflow-hidden">
          {recentRuns.length === 0 ? (
            <div className="p-8 text-center">
              <span className="material-symbols-outlined text-4xl text-zinc-600 mb-2">history</span>
              <p className="text-zinc-400">No recent activity</p>
              <p className="text-zinc-500 text-sm mt-1">Execute a workflow to see runs here</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-zinc-900/50 border-b border-border-dark">
                  <tr>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Workflow</th>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Duration</th>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider text-right">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {recentRuns.map((run) => (
                    <tr key={run.id} className="hover:bg-zinc-700/20 transition-colors">
                      <td className="px-6 py-4">{getStatusBadge(run.status)}</td>
                      <td className="px-6 py-4 font-medium text-white">{workflows?.find(w => w.id === run.workflow_id)?.name ?? `Workflow ${run.workflow_id}`}</td>
                      <td className="px-6 py-4 text-zinc-300 font-mono">{formatDuration(run)}</td>
                      <td className="px-6 py-4 text-right text-zinc-400 font-mono">{formatTime(run)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
      {/* Upcoming Schedules */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h3 className="text-white text-lg font-bold tracking-tight">Upcoming Schedules</h3>
          <span className="inline-flex items-center rounded-full bg-zinc-800 px-2 py-1 text-xs font-medium text-zinc-400 ring-1 ring-inset ring-zinc-700/50">
            {activeSchedules.length} active
          </span>
        </div>
        <div className="bg-surface-light border border-border-dark rounded-xl overflow-hidden">
          {upcomingSchedules.length === 0 ? (
            <div className="p-8 text-center">
              <span className="material-symbols-outlined text-4xl text-zinc-600 mb-2">schedule</span>
              <p className="text-zinc-400">No upcoming schedules</p>
              <p className="text-zinc-500 text-sm mt-1">Schedules will appear here when configured</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-zinc-900/50 border-b border-border-dark">
                  <tr>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Workflow</th>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider">Schedule</th>
                    <th className="px-6 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wider text-right">Next Run</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {upcomingSchedules.map((schedule) => {
                    const wf = workflows?.find(w => w.id === schedule.workflow_id);
                    return (
                      <tr key={schedule.id} className="hover:bg-zinc-700/20 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex flex-col">
                            <span className="text-sm font-medium text-white">{wf?.name ?? `Workflow ${schedule.workflow_id}`}</span>
                            <span className="text-xs text-zinc-500">{schedule.name}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-zinc-300 font-mono text-xs">{schedule.cron}</td>
                        <td className="px-6 py-4 text-right text-zinc-400 text-sm">
                          {schedule.next_run_at ? format(new Date(schedule.next_run_at), 'MMM d, h:mm a') : '--'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
