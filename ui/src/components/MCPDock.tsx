import { useQuery } from '@tanstack/react-query';
import { Popover, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { RocketLaunchIcon } from '@heroicons/react/24/solid';
import client from '../hooks/useApi';
import { MCPServer } from '../types';

const MCPDock = () => {
  const { data } = useQuery<MCPServer[]>({
    queryKey: ['mcp', 'servers'],
    queryFn: async () => {
      const { data } = await client.get('/mcp/servers');
      return data.servers ?? data;
    },
    refetchInterval: 60_000
  });

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-6 flex justify-center">
      <div className="pointer-events-auto flex items-end gap-3 rounded-full border border-holo-blue/30 bg-black/60 px-6 py-3 shadow-2xl shadow-holo-blue/10">
        {data?.map((server) => (
          <Popover key={server.name} className="relative">
            {({ open }) => (
              <>
                <Popover.Button className="flex flex-col items-center gap-2 rounded-2xl border border-holo-blue/30 bg-deck-panel/80 px-4 py-3 text-xs uppercase tracking-[0.3em] text-slate-300 hover:text-holo-blue">
                  <RocketLaunchIcon className={`h-6 w-6 ${open ? 'text-holo-blue' : 'text-slate-400'}`} />
                  {server.name}
                </Popover.Button>
                <Transition
                  as={Fragment}
                  enter="transition ease-out duration-200"
                  enterFrom="opacity-0 translate-y-4"
                  enterTo="opacity-100 translate-y-0"
                  leave="transition ease-in duration-150"
                  leaveFrom="opacity-100 translate-y-0"
                  leaveTo="opacity-0 translate-y-2"
                >
                  <Popover.Panel className="absolute bottom-20 left-1/2 z-10 w-72 -translate-x-1/2 rounded-3xl border border-holo-blue/30 bg-deck-panel/90 p-4 text-xs text-slate-200 shadow-glow">
                    <h3 className="text-xs uppercase tracking-[0.3em] text-holo-blue">Tools</h3>
                    <ul className="mt-3 space-y-2">
                      {server.tools?.map((tool) => (
                        <li key={tool.id} className="rounded-2xl border border-slate-700/60 bg-black/50 p-3">
                          <p className="text-[11px] uppercase tracking-[0.3em] text-holo-amber">{tool.id}</p>
                          <p className="mt-1 text-slate-400">{tool.source}</p>
                        </li>
                      )) ?? <li className="text-slate-500">No tools cached.</li>}
                    </ul>
                  </Popover.Panel>
                </Transition>
              </>
            )}
          </Popover>
        ))}
        {(!data || data.length === 0) && <span className="text-xs text-slate-500">Dock empty — register an MCP server.</span>}
      </div>
    </div>
  );
};

export default MCPDock;
