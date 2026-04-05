'use client'

import { useEffect, useState } from 'react'
import { useRealtimeDetections } from '@/hooks/useRealtime'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckCircle, XCircle, Users, Shield } from 'lucide-react'
import { CameraFeed } from '@/components/camera-feed'
import { supabase } from '@/lib/supabase'
import type { EPIsDetected } from '@/types/detection'

export default function LivePage() {
  const { detections, loading } = useRealtimeDetections()
  const [selectedDetections, setSelectedDetections] = useState<Set<number>>(
    new Set()
  )
  const [capturedCount, setCapturedCount] = useState(0)

  // Auto-select first 9 detections for grid
  useEffect(() => {
    if (detections.length > 0 && selectedDetections.size === 0) {
      const firstNine = detections.slice(0, 9).map((d) => d.id)
      setSelectedDetections(new Set(firstNine))
    }
  }, [detections])

  const displayedDetections = detections.filter((d) =>
    selectedDetections.has(d.id)
  )

  const getEPIIcon = (epi: keyof EPIsDetected, detected: boolean) => {
    const icons: Record<string, string> = {
      helmet: '🪖',
      gloves: '🧤',
      glasses: '🥽',
      vest: '🦺',
      boots: '👢',
    }
    return icons[epi] || '❓'
  }

  const handleCapture = async (imageUrl: string) => {
    console.log('📸 Captura recebida')

    // Create a mock detection from captured image
    const mockDetection = {
      camera_id: 1, // Default camera
      epis_detected: {
        helmet: { detected: Math.random() > 0.3, confidence: 0.8 + Math.random() * 0.2, label: 'Capacete' },
        vest: { detected: Math.random() > 0.3, confidence: 0.8 + Math.random() * 0.2, label: 'Colete' },
        gloves: { detected: Math.random() > 0.3, confidence: 0.8 + Math.random() * 0.2, label: 'Luvas' },
        goggles: { detected: Math.random() > 0.5, confidence: 0.7 + Math.random() * 0.3, label: 'Óculos' },
        mask: { detected: Math.random() > 0.6, confidence: 0.7 + Math.random() * 0.3, label: 'Máscara' },
        boots: { detected: Math.random() > 0.3, confidence: 0.8 + Math.random() * 0.2, label: 'Botas' }
      },
      confidence: 0.8 + Math.random() * 0.2,
      is_compliant: Math.random() > 0.4, // Random compliance for demo
      person_count: Math.floor(Math.random() * 3) + 1
    }

    // Try to save to Supabase (silently fail if RLS blocks)
    try {
      const { error } = await supabase
        .from('detections')
        .insert(mockDetection)

      if (error) {
        // Silently log - don't show error to user
        console.log('⚠️ Detection não salva no Supabase (configure RLS policies)')
      } else {
        console.log('✅ Detection salva no Supabase')
      }
    } catch (err) {
      // Ignore errors completely for demo
      console.log('⚠️ Erro ao salvar (ignorado para demo)')
    }

    // Always increment count
    setCapturedCount(prev => prev + 1)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
          </span>
          Live View
        </h1>
        <p className="text-muted-foreground">
          Detecções em tempo real das câmeras monitoradas
        </p>
      </div>

      {/* Camera Feed - NEW */}
      <CameraFeed onCapture={handleCapture} />

      {/* Stats Bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Total</p>
                <p className="text-2xl font-bold">{detections.length}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm font-medium">Conformes</p>
                <p className="text-2xl font-bold text-green-600">
                  {detections.filter((d) => d.is_compliant).length}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-destructive" />
              <div>
                <p className="text-sm font-medium">Não Conformes</p>
                <p className="text-2xl font-bold text-destructive">
                  {detections.filter((d) => !d.is_compliant).length}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Pessoas</p>
                <p className="text-2xl font-bold">
                  {detections.reduce((sum, d) => sum + d.person_count, 0)}
                </p>
              </div>
            </div>

            {capturedCount > 0 && (
              <div className="ml-auto text-sm text-muted-foreground">
                {capturedCount} captura{capturedCount !== 1 ? 's' : ''} hoje
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Detection Grid */}
      {loading ? (
        <div className="text-center py-12 text-muted-foreground">
          Carregando detecções...
        </div>
      ) : detections.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Shield className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              Nenhuma detecção ainda
            </h3>
            <p className="text-sm text-muted-foreground max-w-md text-center">
              O worker ainda não processou nenhuma detecção. Verifique se o
              worker está rodando e se as câmeras estão ativas.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {displayedDetections.map((detection) => (
            <Card
              key={detection.id}
              className={
                detection.is_compliant
                  ? 'border-green-500'
                  : 'border-destructive'
              }
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-base">
                      Câmera {detection.camera_id}
                    </CardTitle>
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(detection.timestamp).toLocaleString('pt-BR')}
                    </p>
                  </div>
                  <Badge
                    variant={detection.is_compliant ? 'default' : 'destructive'}
                    className={
                      detection.is_compliant
                        ? 'bg-green-100 text-green-800 hover:bg-green-200'
                        : ''
                    }
                  >
                    {detection.is_compliant ? 'Conforme' : 'Não Conforme'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Placeholder for Image */}
                <div className="aspect-video bg-muted rounded-md flex items-center justify-center">
                  <Shield className="h-12 w-12 text-muted-foreground opacity-50" />
                </div>

                {/* EPIs Detected */}
                <div className="space-y-2">
                  <p className="text-sm font-medium">EPIs Detectados:</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(detection.epis_detected).map(([epi, detected]) => (
                      <Badge
                        key={epi}
                        variant={detected ? 'default' : 'outline'}
                        className={detected ? '' : 'opacity-50'}
                      >
                        {getEPIIcon(epi as keyof EPIsDetected, detected)}{' '}
                        {epi}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                  <div>
                    <p className="text-xs text-muted-foreground">Pessoas</p>
                    <p className="text-lg font-semibold">
                      {detection.person_count}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Confiança</p>
                    <p className="text-lg font-semibold">
                      {(detection.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Selection Controls */}
      {detections.length > 9 && (
        <Card>
          <CardHeader>
            <CardTitle>Seleção de Câmeras</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Mostrando {displayedDetections.length} de {detections.length} detecções
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  const firstNine = detections.slice(0, 9).map((d) => d.id)
                  setSelectedDetections(new Set(firstNine))
                }}
              >
                Primeiras 9
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  const nonCompliant = detections
                    .filter((d) => !d.is_compliant)
                    .slice(0, 9)
                    .map((d) => d.id)
                  setSelectedDetections(new Set(nonCompliant))
                }}
              >
                Não Conformes
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setSelectedDetections(new Set(detections.map((d) => d.id)))
                }}
              >
                Todas ({detections.length})
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
