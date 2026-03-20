'use client'

import { Suspense } from 'react'
import { useDetections } from '@/hooks/useDetections'
import { useCameras } from '@/hooks/useCameras'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Shield, CheckCircle, XCircle, Users } from 'lucide-react'

function DashboardContent() {
  const { detections } = useDetections()
  const { cameras } = useCameras()

  // Calculate metrics
  const totalDetections = detections.length
  const compliantDetections = detections.filter((d) => d.is_compliant).length
  const nonCompliantDetections = totalDetections - compliantDetections
  const complianceRate =
    totalDetections > 0 ? (compliantDetections / totalDetections) * 100 : 0

  const activeCameras = cameras.filter((c) => c.is_active).length
  const totalPersons = detections.reduce((sum, d) => sum + d.person_count, 0)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Visão geral do sistema de monitoramento de EPI
        </p>
      </div>

      {/* Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Taxa de Conformidade
            </CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {complianceRate.toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">
              Últimas 24 horas
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Câmeras Ativas
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeCameras}</div>
            <p className="text-xs text-muted-foreground">
              de {cameras.length} totais
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Detect. Conformes
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{compliantDetections}</div>
            <p className="text-xs text-muted-foreground">
              {totalDetections > 0
                ? `${((compliantDetections / totalDetections) * 100).toFixed(1)}%`
                : '0%'}
              {' do total'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Não Conformes
            </CardTitle>
            <XCircle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{nonCompliantDetections}</div>
            <p className="text-xs text-muted-foreground">
              {nonCompliantDetections > 0 ? 'Requer atenção' : 'Sem violações'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Detections */}
      <Card>
        <CardHeader>
          <CardTitle>Detecções Recentes</CardTitle>
        </CardHeader>
        <CardContent>
          {detections.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Shield className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">
                Nenhuma detecção ainda
              </h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Adicione câmeras e inicie o monitoramento para começar a ver
                detecções aqui.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {detections.slice(0, 10).map((detection) => (
                <div
                  key={detection.id}
                  className="flex items-center justify-between border-b pb-4 last:border-0 last:pb-0"
                >
                  <div className="flex items-center gap-4">
                    {detection.is_compliant ? (
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    ) : (
                      <XCircle className="h-5 w-5 text-destructive" />
                    )}
                    <div>
                      <p className="text-sm font-medium">
                        Câmera: {detection.camera?.name || 'Unknown'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(detection.timestamp).toLocaleString('pt-BR')}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">
                      {detection.person_count} pessoa(s)
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Confiança: {(detection.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <Card>
        <CardHeader>
          <CardTitle>Estatísticas Gerais</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Total de Pessoas Detectadas</span>
            <span className="text-sm font-medium">{totalPersons}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Confiança Média</span>
            <span className="text-sm font-medium">
              {totalDetections > 0
                ? `${(
                    detections.reduce((sum, d) => sum + d.confidence, 0) /
                    totalDetections *
                    100
                  ).toFixed(1)}%`
                : 'N/A'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Última Detecção</span>
            <span className="text-sm font-medium">
              {detections.length > 0
                ? new Date(
                    detections[0]?.timestamp || ''
                  ).toLocaleString('pt-BR')
                : 'N/A'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Total de Câmeras</span>
            <span className="text-sm font-medium">{cameras.length}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div>Carregando...</div>}>
      <DashboardContent />
    </Suspense>
  )
}
