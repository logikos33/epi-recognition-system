'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Settings,
  Brain,
  Camera,
  Package,
  Wrench,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Monitoramento', href: '/dashboard/monitoring', icon: Camera },
  { name: 'Gerenciar Câmeras', href: '/dashboard/cameras', icon: Settings },
  { name: 'Gerenciar Classes', href: '/dashboard/classes', icon: Package },
  { name: 'Treinamento', href: '/dashboard/training', icon: Brain },
  { name: 'Painel de Treinamento', href: '/dashboard/training-panel', icon: Wrench },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="flex h-full w-64 flex-col border-r bg-background">
      <div className="flex-1 overflow-y-auto py-4">
        <nav className="space-y-1 px-3">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.name}
              </Link>
            )
          })}
        </nav>
      </div>

      <div className="border-t p-4">
        <p className="text-xs text-muted-foreground">
          Versão 1.0.0 (Cloud)
        </p>
      </div>
    </div>
  )
}
