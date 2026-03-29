// frontend/src/app/dashboard/monitoring/page.tsx
'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Camera, LayoutDashboard, Settings } from 'lucide-react'
import { AuthProtected } from '@/components/auth-protected'
import { CameraGrid } from '@/components/monitoring/CameraGrid'

// Placeholder components (will implement in next tasks)
function DashboardTab() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Dashboard</h2>
      <div className="bg-muted rounded-lg h-96 flex items-center justify-center">
        <p className="text-muted-foreground">Dashboard coming soon...</p>
      </div>
    </div>
  )
}

function ConfigTab() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Configuration</h2>
      <div className="bg-muted rounded-lg h-96 flex items-center justify-center">
        <p className="text-muted-foreground">Configuration coming soon...</p>
      </div>
    </div>
  )
}

export default function MonitoringPage() {
  const [activeTab, setActiveTab] = useState('cameras')

  return (
    <AuthProtected>
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="border-b px-6 py-4">
          <h1 className="text-3xl font-bold">Monitoramento de Abastecimento</h1>
          <p className="text-muted-foreground mt-1">
            Monitoramento em tempo real de baias de carregamento
          </p>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1">
          <div className="border-b px-6">
            <TabsList>
              <TabsTrigger value="cameras" className="flex items-center gap-2">
                <Camera className="w-4 h-4" />
                Câmeras
              </TabsTrigger>
              <TabsTrigger value="dashboard" className="flex items-center gap-2">
                <LayoutDashboard className="w-4 h-4" />
                Dashboard
              </TabsTrigger>
              <TabsTrigger value="config" className="flex items-center gap-2">
                <Settings className="w-4 h-4" />
                Configurações
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="cameras" className="flex-1 m-0">
            <CameraGrid />
          </TabsContent>

          <TabsContent value="dashboard" className="flex-1 m-0">
            <DashboardTab />
          </TabsContent>

          <TabsContent value="config" className="flex-1 m-0">
            <ConfigTab />
          </TabsContent>
        </Tabs>
      </div>
    </AuthProtected>
  )
}
