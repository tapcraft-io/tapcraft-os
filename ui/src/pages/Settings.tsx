import ConfigPanel from '../components/ConfigPanel';

const SettingsPage = () => {
  return (
    <div className="space-y-10">
      <ConfigPanel />
      <p className="text-center text-xs uppercase tracking-[0.3em] text-slate-500">
        Secrets remain masked; adjustments sync with the API config service.
      </p>
    </div>
  );
};

export default SettingsPage;
