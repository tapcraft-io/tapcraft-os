import { Link, useNavigate } from 'react-router-dom';
import { useActivities } from '../hooks/useTapcraft';

const WORKSPACE_ID = 1;

const activityIcons: Record<string, { icon: string; bg: string; text: string; border: string }> = {
  default: { icon: 'apps', bg: 'bg-blue-900/30', text: 'text-blue-400', border: 'border-blue-900/50' },
  email: { icon: 'mail', bg: 'bg-purple-900/30', text: 'text-purple-400', border: 'border-purple-900/50' },
  slack: { icon: 'chat', bg: 'bg-orange-900/30', text: 'text-orange-400', border: 'border-orange-900/50' },
  notion: { icon: 'note', bg: 'bg-zinc-900/30', text: 'text-zinc-400', border: 'border-zinc-900/50' },
  http: { icon: 'http', bg: 'bg-teal-900/30', text: 'text-teal-400', border: 'border-teal-900/50' },
  database: { icon: 'database', bg: 'bg-pink-900/30', text: 'text-pink-400', border: 'border-pink-900/50' },
};

const getActivityIcon = (name: string) => {
  const lowerName = name.toLowerCase();
  for (const key of Object.keys(activityIcons)) {
    if (lowerName.includes(key)) return activityIcons[key];
  }
  return activityIcons.default;
};

const Activities = () => {
  const navigate = useNavigate();
  const { data: activities, isLoading, error } = useActivities(WORKSPACE_ID);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="w-full px-8 py-6 border-b border-border-dark bg-background-dark sticky top-0 z-10">
        <div className="max-w-[1200px] mx-auto flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-2">
            <h2 className="text-white text-3xl font-bold tracking-tight">Your Activities</h2>
            <p className="text-zinc-400 text-base">Manage and develop your activity inventory.</p>
          </div>
          <div className="flex items-center gap-3">
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 px-8 py-8 overflow-auto">
        <div className="max-w-[1200px] mx-auto flex flex-col gap-6">
          {isLoading ? (
            <div className="rounded-xl border border-border-dark bg-surface-light/50 overflow-hidden">
              <div className="p-8 space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse flex items-center gap-4">
                    <div className="w-8 h-8 rounded bg-zinc-700" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 w-1/4 bg-zinc-700 rounded" />
                      <div className="h-3 w-1/2 bg-zinc-800 rounded" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6">
              <div className="flex items-center gap-3 text-red-400">
                <span className="material-symbols-outlined">error</span>
                <span>Error loading activities: {error.message}</span>
              </div>
            </div>
          ) : activities && activities.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border-2 border-dashed border-border-dark rounded-xl">
              <div className="w-16 h-16 rounded-full bg-surface-light flex items-center justify-center mb-4">
                <span className="material-symbols-outlined text-3xl text-zinc-500">add_circle</span>
              </div>
              <p className="text-white font-medium">No activities yet</p>
              <p className="text-zinc-500 text-sm mt-1">Create your first activity to get started</p>
              <Link
                to="/workflows"
                className="mt-6 flex items-center gap-2 h-10 px-5 bg-primary text-zinc-950 text-sm font-bold rounded-lg"
              >
                <span className="material-symbols-outlined text-[18px]">add</span>
                Create Workflow
              </Link>
            </div>
          ) : (
            <div className="rounded-xl border border-border-dark bg-surface-light/50 overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-zinc-900/50 border-b border-border-dark">
                      <th className="p-4 text-xs font-semibold uppercase tracking-wider text-zinc-500 w-1/4">Name</th>
                      <th className="p-4 text-xs font-semibold uppercase tracking-wider text-zinc-500 w-1/3">Description</th>
                      <th className="p-4 text-xs font-semibold uppercase tracking-wider text-zinc-500 w-1/6">Category</th>
                      <th className="p-4 text-xs font-semibold uppercase tracking-wider text-zinc-500 text-center w-1/12">Ops</th>
                      <th className="p-4 text-xs font-semibold uppercase tracking-wider text-zinc-500 text-right w-1/6">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800">
                    {activities?.map((activity) => {
                      const iconStyle = getActivityIcon(activity.name);
                      return (
                        <tr key={activity.id} className="group hover:bg-zinc-700/20 transition-colors">
                          <td className="p-4">
                            <div className="flex items-center gap-3">
                              <div className={`w-8 h-8 rounded ${iconStyle.bg} ${iconStyle.text} flex items-center justify-center border ${iconStyle.border}`}>
                                <span className="material-symbols-outlined text-[18px]">{iconStyle.icon}</span>
                              </div>
                              <div>
                                <div className="text-sm font-medium text-white group-hover:text-primary transition-colors">
                                  {activity.name}
                                </div>
                                <div className="text-xs text-zinc-500 mt-0.5 font-mono">
                                  {activity.code_module_path}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="p-4">
                            <p className="text-sm text-zinc-400 line-clamp-1">
                              {activity.description || 'No description'}
                            </p>
                          </td>
                          <td className="p-4">
                            {activity.category ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary ring-1 ring-inset ring-primary/20">
                                {activity.category}
                              </span>
                            ) : (
                              <span className="text-zinc-500 text-sm">—</span>
                            )}
                          </td>
                          <td className="p-4 text-center">
                            <span className="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-800 text-white">
                              {activity.operations.length}
                            </span>
                          </td>
                          <td className="p-4 text-right">
                            <button
                              onClick={() => navigate(`/activities/${activity.id}`)}
                              className="inline-flex items-center justify-center h-8 px-4 rounded-lg border border-border-dark bg-transparent text-xs font-medium text-white hover:bg-primary hover:text-zinc-950 hover:border-primary transition-colors"
                            >
                              Open
                            </button>
                          </td>
                        </tr>
                      );
                    })}
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

export default Activities;
