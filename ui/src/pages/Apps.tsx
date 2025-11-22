import { useState } from 'react';
import { CubeIcon, PlusIcon } from '@heroicons/react/24/outline';
import { useApps } from '../hooks/useTapcraft';

const WORKSPACE_ID = 1; // TODO: Get from context/route

const Apps = () => {
  const { data: apps, isLoading, error } = useApps(WORKSPACE_ID);

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 w-32 bg-slate-700 rounded mb-4" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-slate-800 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-400">
          Error loading apps: {error.message}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-3">
            <CubeIcon className="h-7 w-7 text-orange-500" />
            Apps
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Reusable capabilities that can be used in workflows
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-md text-sm font-medium transition-colors">
          <PlusIcon className="h-4 w-4" />
          Create App
        </button>
      </div>

      {/* Apps List */}
      {apps && apps.length === 0 ? (
        <div className="text-center py-12 bg-slate-900/30 rounded-lg border border-slate-800">
          <CubeIcon className="h-12 w-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400 mb-4">No apps yet</p>
          <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-md text-sm">
            Create your first app
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {apps?.map((app) => (
            <div
              key={app.id}
              className="p-5 bg-slate-900/50 border border-slate-800 rounded-lg hover:border-slate-700 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-medium">{app.name}</h3>
                    {app.category && (
                      <span className="px-2 py-0.5 text-xs bg-slate-800 text-slate-400 rounded">
                        {app.category}
                      </span>
                    )}
                  </div>
                  {app.description && (
                    <p className="text-sm text-slate-400 mb-3">{app.description}</p>
                  )}
                  <div className="flex items-center gap-4 text-xs text-slate-500">
                    <span>{app.operations.length} operations</span>
                    <span>•</span>
                    <span className="font-mono">{app.code_module_path}</span>
                  </div>
                </div>
                <button className="px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors">
                  View →
                </button>
              </div>

              {/* Operations */}
              {app.operations.length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-800">
                  <div className="text-xs text-slate-500 mb-2">Operations:</div>
                  <div className="flex flex-wrap gap-2">
                    {app.operations.map((op) => (
                      <div
                        key={op.id}
                        className="px-2 py-1 bg-slate-800/50 rounded text-xs text-slate-300"
                        title={op.description || undefined}
                      >
                        {op.display_name}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Apps;
