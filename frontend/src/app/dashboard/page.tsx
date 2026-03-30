'use client'

import { useEffect, useState } from 'react'
import { AuthProtected } from '@/components/auth-protected'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, Camera, Fuel, Truck, TrendingUp, Loader2 } from 'lucide-react'

export default function DashboardPage() {
  const [stats, setStats] = useState({
    totalCameras: 0,
    activeCameras: 0,
    activeSessions: 0,
    completedSessions: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        // Fetch cameras
        const camerasResult = await api.listCameras()
        const totalCameras = camerasResult.cameras?.length || 0
        const activeCameras = camerasResult.cameras?.filter((c: any) => c.is_active).length || 0

        // Fetch sessions
        const activeSessionsResult = await api.get('/api/sessions?status=active')
        const activeSessions = activeSessionsResult.sessions?.length || 0

        const completedSessionsResult = await api.get('/api/sessions?status=completed')
        const completedSessions = completedSessionsResult.sessions?.length || 0

        setStats({
          totalCameras,
          activeCameras,
          activeSessions,
          completedSessions
        })
      } catch (err) {
        console.error('Error fetching stats:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  if (loading) {
    return (
      <AuthProtected>
        <div className="h-full flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </AuthProtected>
    )
  }

  return (
    <AuthProtected>
      <div className="h-full flex flex-col">
        <div className="border-b px-6 py-4">
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Visão geral do sistema de monitoramento
          </p>
        </div>

        <div className="flex-1 overflow-auto p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {/* Total Cameras */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total de Câmeras
                </CardTitle>
                <Camera className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats.totalCameras}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Configuradas no sistema
                </p>
              </CardContent>
            </Card>

            {/* Active Cameras */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Câmeras Ativas
                </CardTitle>
                <Activity className="h-4 w-4 text-green-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats.activeCameras}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Em operação
                </p>
              </CardContent>
            </Card>

            {/* Active Sessions */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Sessões Ativas
                </CardTitle>
                <Fuel className="h-4 w-4 text-blue-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats.activeSessions}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Em andamento
                </p>
              </CardContent>
            </Card>

            {/* Completed Sessions */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Concluídas Hoje
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-green-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats.completedSessions}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Sessões finalizadas
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Acesso Rápido</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button
                onClick={() => (window.location.href = '/dashboard/monitoring')}
                className="p-4 border rounded-lg hover:bg-accent transition-colors text-left"
              >
                <Camera className="h-6 w-6 mb-2 text-primary" />
                <h3 className="font-semibold">Monitoramento</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Visualize câmeras em tempo real
                </p>
              </button>

              <button
                onClick={() => (window.location.href = '/dashboard/cameras')}
                className="p-4 border rounded-lg hover:bg-accent transition-colors text-left"
              >
                <Activity className="h-6 w-6 mb-2 text-primary" />
                <h3 className="font-semibold">Gerenciar Câmeras</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Configure suas câmeras IP
                </p>
              </button>

              <button
                onClick={() => (window.location.href = '/dashboard/training')}
                className="p-4 border rounded-lg hover:bg-accent transition-colors text-left"
              >
                <Truck className="h-6 w-6 mb-2 text-primary" />
                <h3 className="font-semibold">Treinamento</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Treine modelos de IA
                </p>
              </button>
            </CardContent>
          </Card>
        </div>
      </div>
    </AuthProtected>
  )
}
