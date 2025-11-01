import { Tab } from '@headlessui/react';
import clsx from 'clsx';
import { useMemo } from 'react';
import { RunRecord, WorkflowSpec } from '../types';

interface InspectorProps {
  workflow?: WorkflowSpec;
  runs?: RunRecord[];
}

const Inspector = ({ workflow, runs = [] }: InspectorProps) => {
  const tabs = useMemo(
    () => [
      { name: 'Overview' },
      { name: 'Activities' },
      { name: 'Code' },
      { name: 'Runs' }
    ],
    []
  );

  if (!workflow) {
    return (
      <aside className="glass-panel w-96 p-6 text-sm text-slate-400">
        Select a workflow from the Patch Bay to inspect its instrumentation.
      </aside>
    );
  }

  return (
    <aside className="glass-panel w-96 p-6">
      <header className="mb-4">
        <h3 className="text-sm uppercase tracking-[0.3em] text-holo-blue">{workflow.workflow_ref}</h3>
        <p className="mt-2 text-xs text-slate-400">
          {workflow.loaded ? 'Loaded into worker and ready.' : 'Not yet loaded. Deploy from Agent Console.'}
        </p>
      </header>
      <Tab.Group>
        <Tab.List className="grid grid-cols-4 gap-2 text-[11px] uppercase tracking-[0.3em]">
          {tabs.map((tab) => (
            <Tab
              key={tab.name}
              className={({ selected }) =>
                clsx(
                  'rounded-full border px-2 py-1 transition-colors',
                  selected ? 'border-holo-blue/40 text-holo-blue shadow-glow' : 'border-transparent text-slate-400'
                )
              }
            >
              {tab.name}
            </Tab>
          ))}
        </Tab.List>
        <Tab.Panels className="mt-4 text-xs text-slate-300">
          <Tab.Panel>
            <ul className="space-y-2">
              {workflow.config_schema ? (
                Object.entries(workflow.config_schema).map(([key, value]) => (
                  <li key={key}>
                    <span className="text-slate-400">{key}</span>
                    <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-black/40 p-3 text-[11px] text-holo-amber/80">
                      {JSON.stringify(value, null, 2)}
                    </pre>
                  </li>
                ))
              ) : (
                <li>No config schema provided.</li>
              )}
            </ul>
          </Tab.Panel>
          <Tab.Panel>
            <p className="text-slate-400">Activities populated after validation.</p>
          </Tab.Panel>
          <Tab.Panel>
            <p className="text-slate-400">Load module to view generated code.</p>
          </Tab.Panel>
          <Tab.Panel>
            <ul className="space-y-2">
              {runs.map((run) => (
                <li key={run.id} className="flex items-center justify-between text-[11px]">
                  <span>{run.status}</span>
                  <span className="text-slate-500">{new Date(run.started_at).toLocaleString()}</span>
                </li>
              ))}
              {runs.length === 0 && <li>No recent runs.</li>}
            </ul>
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
    </aside>
  );
};

export default Inspector;
