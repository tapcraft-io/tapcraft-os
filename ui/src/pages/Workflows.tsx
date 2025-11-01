import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import PatchBay from '../components/PatchBay';
import Inspector from '../components/Inspector';
import client from '../hooks/useApi';
import { RunRecord, WorkflowSpec } from '../types';

const WorkflowsPage = () => {
  const [selected, setSelected] = useState<WorkflowSpec | undefined>();
  const { data: workflows } = useQuery<WorkflowSpec[]>({
    queryKey: ['workflows'],
    queryFn: async () => {
      const { data } = await client.get('/workflows');
      return data.workflows ?? data;
    }
  });

  const { data: runs } = useQuery<RunRecord[]>({
    queryKey: ['runs', selected?.workflow_ref],
    queryFn: async () => {
      if (!selected) return [];
      const { data } = await client.get('/runs', { params: { workflow_ref: selected.workflow_ref, limit: 20 } });
      return data.runs ?? data;
    },
    enabled: Boolean(selected)
  });

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_360px] gap-8">
      <div>
        <PatchBay
          onSelect={(workflowRef) => {
            const match = workflows?.find((wf) => wf.workflow_ref === workflowRef);
            if (match) {
              setSelected(match);
            }
          }}
        />
      </div>
      <Inspector workflow={selected} runs={runs} />
    </div>
  );
};

export default WorkflowsPage;
