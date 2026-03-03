import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../components/AuthGate';

const navItems = [
  { to: '/', label: 'Dashboard', icon: 'dashboard' },
  { to: '/activities', label: 'Activities', icon: 'apps' },
  { to: '/workflows', label: 'Workflows', icon: 'account_tree' },
  { to: '/runs', label: 'Runs', icon: 'history' },
  { to: '/secrets', label: 'Secrets', icon: 'key' },
];

const AppShell = () => {
  const location = useLocation();
  const { logout } = useAuth();

  return (
    <div className="flex h-screen w-full overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 h-full bg-surface-dark border-r border-border-dark flex flex-col shrink-0">
        {/* Logo */}
        <div className="p-6 pb-2">
          <Link to="/" className="flex flex-col gap-1">
            <h1 className="text-white text-xl font-bold tracking-tight flex items-center gap-2">
              <span className="material-symbols-outlined text-primary icon-filled">terminal</span>
              Tapcraft
            </h1>
            <p className="text-zinc-500 text-xs font-medium tracking-wider uppercase ml-8">Automation OS</p>
          </Link>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto py-4 px-3 flex flex-col gap-6">
          <nav className="flex flex-col gap-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.to ||
                (item.to !== '/' && location.pathname.startsWith(item.to));

              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary/10 text-primary border border-primary/20'
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
                  }`}
                >
                  <span className={`material-symbols-outlined ${isActive ? 'icon-filled' : ''}`}>
                    {item.icon}
                  </span>
                  <span className="text-sm font-medium">{item.label}</span>
                </NavLink>
              );
            })}
          </nav>

          {/* Bottom section */}
          <div className="mt-auto flex flex-col gap-4">
            {/* New Workflow CTA */}
            <Link
              to="/workflows"
              className="flex w-full items-center justify-center rounded-lg h-10 px-4 bg-primary text-zinc-950 hover:bg-primary/90 transition-colors text-sm font-bold shadow-lg shadow-primary/20"
            >
              <span className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px]">add</span>
                New Workflow
              </span>
            </Link>

            {/* Settings */}
            <div className="flex flex-col gap-1 border-t border-zinc-800 pt-4">
              <NavLink
                to="/settings"
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                  location.pathname === '/settings'
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
                }`}
              >
                <span className="material-symbols-outlined">settings</span>
                <span className="text-sm font-medium">Settings</span>
              </NavLink>
              <button
                onClick={logout}
                className="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors text-zinc-400 hover:text-white hover:bg-zinc-800 w-full"
              >
                <span className="material-symbols-outlined">logout</span>
                <span className="text-sm font-medium">Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 h-full overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
};

export default AppShell;
