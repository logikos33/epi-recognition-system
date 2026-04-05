import { Bell, Settings, User } from 'lucide-react';
import { Button } from '../ui/button';

export function Header() {
  return (
    <header className="h-16 bg-bg-secondary border-b border-border flex items-center justify-between px-6 sticky top-0 z-40">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold text-text-primary">Sistema de Monitoramento de EPI</h2>
      </div>

      <div className="flex items-center gap-3">
        {/* Notifications */}
        <Button variant="ghost" size="sm" className="relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-accent-red rounded-full"></span>
        </Button>

        {/* Settings */}
        <Button variant="ghost" size="sm">
          <Settings className="w-5 h-5" />
        </Button>

        {/* User */}
        <div className="flex items-center gap-3 pl-3 border-l border-border">
          <div className="text-right">
            <p className="text-sm font-medium text-text-primary">Admin</p>
            <p className="text-xs text-text-secondary">admin@empresa.com</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center">
            <User className="w-5 h-5 text-accent-blue" />
          </div>
        </div>
      </div>
    </header>
  );
}
