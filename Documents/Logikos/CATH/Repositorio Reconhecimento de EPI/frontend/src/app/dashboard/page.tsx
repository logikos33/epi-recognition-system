'use client'

import { signOut, getCurrentUser, type User } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LogOut, Package, Wrench, Camera, LayoutDashboard, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { useEffect, useState } from 'react'

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    setUser(getCurrentUser())
  }, [])

  const handleLogout = () => {
    signOut()
    router.push('/login')
  }

  // Avoid hydration mismatch by not rendering until mounted
  if (!mounted) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-gray-900" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">EPI Recognition System</h1>
              <p className="text-sm text-gray-600">Bem-vindo, {user?.full_name || user?.email}</p>
            </div>
            <Button onClick={handleLogout} variant="outline">
              <LogOut className="w-4 h-4 mr-2" />
              Sair
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Link href="/dashboard/classes">
            <Card className="cursor-pointer hover:shadow-lg transition-shadow">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Package className="w-6 h-6 text-blue-600" />
                  Gerenciar Classes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">Configure classes YOLO para detecção</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/dashboard/training-panel">
            <Card className="cursor-pointer hover:shadow-lg transition-shadow">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Wrench className="w-6 h-6 text-green-600" />
                  Painel de Treinamento
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">Acompanhe o treinamento do modelo</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/dashboard/cameras">
            <Card className="cursor-pointer hover:shadow-lg transition-shadow">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Camera className="w-6 h-6 text-purple-600" />
                  Câmeras
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">Gerencie câmeras IP</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/dashboard/monitoring">
            <Card className="cursor-pointer hover:shadow-lg transition-shadow">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <LayoutDashboard className="w-6 h-6 text-orange-600" />
                  Monitoramento
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">Visualize monitoramento em tempo real</p>
              </CardContent>
            </Card>
          </Link>
        </div>
      </main>
    </div>
  )
}
