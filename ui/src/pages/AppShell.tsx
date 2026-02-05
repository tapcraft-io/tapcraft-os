import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { RocketLaunchIcon, CubeIcon, BoltIcon, SparklesIcon, PlayIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';

const navItems = [
  { to: '/', label: 'Home', icon: RocketLaunchIcon },
  { to: '/apps', label: 'Apps', icon: CubeIcon },
  { to: '/workflows', label: 'Workflows', icon: BoltIcon },
  { to: '/agent', label: 'Agent', icon: SparklesIcon },
  { path: '/runs', label: 'Runs', icon: PlayIcon },
  { to: '/settings', label: 'Settings', icon: Cog6ToothIcon }
];

const AppShell = () => {
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-slate-900/50 px-4 py-6">
        <Link to="/" className="flex items-center gap-3 mb-8 px-2">
          <RocketLaunchIcon className="h-8 w-8 text-orange-500" />
          <div>
            <div className="text-lg font-semibold">Tapcraft</div>
            <div className="text-xs text-slate-500">Automation OS</div>
          </div>
        </Link>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to));

            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? 'bg-orange-500/10 text-orange-400 font-medium'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="mt-8 px-3 py-4 rounded-md bg-slate-800/30 border border-slate-700/50">
          <div className="text-xs text-slate-500 mb-2">Status</div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-sm text-slate-300">System Online</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};

export default AppShell;
