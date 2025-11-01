import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { RocketLaunchIcon, SparklesIcon, WrenchIcon } from '@heroicons/react/24/outline';
import MCPDock from '../components/MCPDock';
import ChronoScope from '../components/ChronoScope';

const navItems = [
  { to: '/', label: 'Command Deck' },
  { to: '/agent', label: 'Agent Console' },
  { to: '/workflows', label: 'Patch Bay' },
  { to: '/settings', label: 'Config & Secrets' }
];

const AppShell = () => {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gradient-to-br from-deck-base via-deck-panel to-black text-slate-100">
      <header className="flex items-center justify-between px-10 py-6">
        <Link to="/" className="flex items-center gap-3 text-xl font-semibold tracking-wide">
          <RocketLaunchIcon className="h-8 w-8 text-holo-amber animate-pulseSlow" />
          Tapcraft Control Center
        </Link>
        <nav className="flex gap-4 text-sm">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `px-4 py-2 rounded-full border border-transparent transition-colors ${
                  isActive || location.pathname === item.to
                    ? 'border-holo-blue/40 text-holo-blue shadow-glow'
                    : 'text-slate-400 hover:text-slate-200'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex gap-3 text-xs">
          <span className="flex items-center gap-1 text-holo-blue">
            <SparklesIcon className="h-4 w-4" />
            Holo Mode
          </span>
          <span className="flex items-center gap-1 text-holo-amber/80">
            <WrenchIcon className="h-4 w-4" />
            Build 0.1
          </span>
        </div>
      </header>
      <main className="px-10 pb-24">
        <Outlet />
      </main>
      <footer className="px-10 pb-10">
        <ChronoScope />
      </footer>
      <MCPDock />
    </div>
  );
};

export default AppShell;
