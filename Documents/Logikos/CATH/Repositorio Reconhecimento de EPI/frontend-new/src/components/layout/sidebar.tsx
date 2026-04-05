import { NavLink } from 'react-router-dom';
import {
  Video,
  LayoutDashboard,
  Tag,
  Brain,
  BarChart3,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface NavItem {
  path: string;
  label: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { path: '/cameras', label: 'Câmeras', icon: Video },
  { path: '/monitoring', label: 'Monitoramento', icon: LayoutDashboard },
  { path: '/classes', label: 'Classes', icon: Tag },
  { path: '/training', label: 'Treinamento', icon: Brain },
  { path: '/dashboard', label: 'Dashboard', icon: BarChart3 },
];

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-bg-secondary border-r border-border flex flex-col z-50">
      {/* Logo */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent-blue flex items-center justify-center">
            <Video className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-text-primary">EPI Monitor</h1>
            <p className="text-xs text-text-secondary">Sistema de Reconhecimento</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto scrollbar-thin">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/cameras'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 group',
                isActive
                  ? 'bg-accent-blue/10 text-accent-blue'
                  : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon className={cn('w-5 h-5', isActive ? 'text-accent-blue' : 'text-text-secondary group-hover:text-text-primary')} />
                <span>{item.label}</span>
                {isActive && <ChevronRight className="ml-auto w-4 h-4 text-accent-blue" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <div className="px-4 py-3 rounded-lg bg-bg-tertiary border border-border">
          <p className="text-xs text-text-secondary">Status do Sistema</p>
          <div className="flex items-center gap-2 mt-2">
            <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse"></div>
            <span className="text-sm font-medium text-accent-green">Operacional</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
