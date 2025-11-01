import CommandDeck from '../components/CommandDeck';

const Dashboard = () => {
  return (
    <div className="space-y-10">
      <CommandDeck />
      <p className="text-center text-xs uppercase tracking-[0.3em] text-slate-500">
        Maintain situational awareness across Temporal, MCP, and agent runs.
      </p>
    </div>
  );
};

export default Dashboard;
