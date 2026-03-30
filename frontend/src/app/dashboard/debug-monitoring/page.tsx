'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { AuthProtected } from '@/components/auth-protected'

export default function DebugMonitoringPage() {
  const [token, setToken] = useState<string | null>(null)
  const [cameras, setCameras] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const check = async () => {
      // Check token
      const storedToken = localStorage.getItem('auth_token')
      setToken(storedToken ? `${storedToken.substring(0, 20)}...` : 'NONE')

      if (!storedToken) {
        setError('No token found in localStorage')
        setLoading(false)
        return
      }

      // Set token on API client
      api.setToken(storedToken)

      // Fetch cameras
      try {
        console.log('[Debug] Fetching cameras...')
        const result = await api.listCameras()
        console.log('[Debug] Result:', result)

        if (result.success) {
          setCameras(result.cameras)
        } else {
          setError(`API returned success=false: ${JSON.stringify(result)}`)
        }
      } catch (err: any) {
        console.error('[Debug] Error:', err)
        setError(err?.message || 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    check()
  }, [])

  return (
    <AuthProtected>
      <div className="p-6 space-y-6">
        <h1 className="text-3xl font-bold">Debug - Monitoramento</h1>

        {/* Token Info */}
        <div className="bg-muted rounded-lg p-4">
          <h2 className="font-semibold mb-2">Auth Token</h2>
          <p className="text-sm font-mono">{token || 'Loading...'}</p>
        </div>

        {/* API Info */}
        <div className="bg-muted rounded-lg p-4">
          <h2 className="font-semibold mb-2">API Base URL</h2>
          <p className="text-sm font-mono">{process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'}</p>
        </div>

        {/* Cameras */}
        <div className="bg-muted rounded-lg p-4">
          <h2 className="font-semibold mb-2">Câmeras ({cameras.length})</h2>
          {loading ? (
            <p className="text-sm text-muted-foreground">Carregando...</p>
          ) : error ? (
            <div className="bg-destructive/10 text-destructive p-3 rounded">
              <p className="font-semibold">Erro:</p>
              <p className="text-sm">{error}</p>
            </div>
          ) : cameras.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhuma câmera encontrada</p>
          ) : (
            <div className="space-y-2">
              {cameras.slice(0, 5).map((cam) => (
                <div key={cam.id} className="bg-background p-3 rounded text-sm">
                  <p className="font-semibold">{cam.name}</p>
                  <p className="text-muted-foreground">ID: {cam.id} | Bay: {cam.bay_id} | Active: {cam.is_active ? 'Yes' : 'No'}</p>
                </div>
              ))}
              {cameras.length > 5 && (
                <p className="text-muted-foreground text-sm">... e mais {cameras.length - 5} câmeras</p>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={() => window.location.href = '/dashboard/monitoring'}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
          >
            Ir para Monitoramento
          </button>
          <button
            onClick={() => {
              console.log('Token:', api.getToken())
              console.log('Cameras:', cameras)
            }}
            className="px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/90"
          >
            Log no Console
          </button>
        </div>
      </div>
    </AuthProtected>
  )
}
