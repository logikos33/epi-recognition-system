import { useState } from 'react';
import { mockCameras } from '../lib/mock-data';
import { Video, Maximize2, TriangleAlert, CheckCircle, AlertTriangle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card } from '../components/ui/card';

type GridLayout = 1 | 4 | 9 | 16;

export function MonitoringPage() {
  const [gridLayout, setGridLayout] = useState<GridLayout>(4);
  const [selectedCameras] = useState(mockCameras.filter((c) => c.isActive));

  const gridSizeClass = {
    1: 'grid-cols-1',
    4: 'grid-cols-2',
    9: 'grid-cols-3',
    16: 'grid-cols-4',
  }[gridLayout];

  // Mock detections for each camera
  const mockDetections = {
    '1': [
      { id: 1, class: 'capacete', confidence: 0.95, status: 'safe' },
      { id: 2, class: 'luva_seguranca', confidence: 0.87, status: 'safe' },
    ],
    '2': [
      { id: 1, class: 'oculos_protecao', confidence: 0.65, status: 'warning' },
    ],
    '3': [],
    '4': [
      { id: 1, class: 'capacete', confidence: 0.92, status: 'safe' },
      { id: 2, class: 'luva_seguranca', confidence: 0.88, status: 'safe' },
      { id: 3, class: 'bota_seguranca', confidence: 0.91, status: 'safe' },
    ],
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Monitoramento ao Vivo</h1>
          <p className="text-text-secondary mt-1">
            Visualização em tempo real das câmeras de monitoramento
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Grid Layout Selector */}
          <div className="flex items-center bg-bg-tertiary border border-border rounded-lg p-1">
            {[1, 4, 9, 16].map((size) => (
              <button
                key={size}
                onClick={() => setGridLayout(size as GridLayout)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  gridLayout === size
                    ? 'bg-accent-blue text-white'
                    : 'text-text-secondary hover:bg-bg-secondary'
                }`}
              >
                {size === 1 ? '1x1' : size === 4 ? '2x2' : size === 9 ? '3x3' : '4x4'}
              </button>
            ))}
          </div>

          <Button variant="primary">Configurar Alertas</Button>
        </div>
      </div>

      {/* Alert Summary */}
      <Card className="border-l-4 border-l-accent-amber">
        <div className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-amber/10 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-accent-amber" />
            </div>
            <div>
              <p className="font-medium text-text-primary">Alertas Ativos</p>
              <p className="text-sm text-text-secondary">
                {selectedCameras.reduce((acc, cam) => acc + (mockDetections[cam.id as keyof typeof mockDetections]?.filter(d => d.status === 'warning').length || 0), 0)} detecções com baixa confiança
              </p>
            </div>
          </div>
          <Badge variant="warning">Requer Atenção</Badge>
        </div>
      </Card>

      {/* Video Grid */}
      <div className={`grid ${gridSizeClass} gap-4`}>
        {selectedCameras.slice(0, gridLayout).map((camera) => {
          const detections = mockDetections[camera.id as keyof typeof mockDetections] || [];
          const warningCount = detections.filter((d) => d.status === 'warning').length;

          return (
            <Card key={camera.id} className="overflow-hidden border border-border">
              {/* Video Header */}
              <div className="bg-bg-tertiary px-4 py-2 flex items-center justify-between border-b border-border">
                <div className="flex items-center gap-2">
                  <Video className="w-4 h-4 text-accent-blue" />
                  <span className="text-sm font-medium text-text-primary">{camera.name}</span>
                  <Badge
                    variant={camera.status === 'online' ? 'success' : 'error'}
                    className="ml-2"
                  >
                    {camera.status}
                  </Badge>
                </div>
                <Button variant="ghost" size="sm" className="p-1">
                  <Maximize2 className="w-4 h-4" />
                </Button>
              </div>

              {/* Video Feed (placeholder) */}
              <div className="relative aspect-video bg-black flex items-center justify-center">
                {/* Simulated video feed */}
                <div className="absolute inset-0 bg-gradient-to-br from-bg-tertiary to-bg-primary opacity-50"></div>

                {/* Camera icon placeholder */}
                <Video className="w-16 h-16 text-text-muted relative z-10" />

                {/* Detection boxes overlay (simulated) */}
                {detections.length > 0 && camera.status === 'online' && (
                  <div className="absolute top-4 left-4 right-4 space-y-2">
                    {detections.map((detection) => (
                      <div
                        key={detection.id}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-mono ${
                          detection.status === 'safe'
                            ? 'bg-accent-green/20 text-accent-green border border-accent-green/30'
                            : 'bg-accent-amber/20 text-accent-amber border border-accent-amber/30'
                        }`}
                      >
                        {detection.status === 'safe' ? (
                          <CheckCircle className="w-3 h-3" />
                        ) : (
                          <TriangleAlert className="w-3 h-3" />
                        )}
                        <span>{detection.class}</span>
                        <span className="opacity-75">
                          {(detection.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Timestamp */}
                <div className="absolute bottom-4 left-4 px-2 py-1 bg-black/50 rounded text-xs font-mono text-text-primary">
                  {new Date().toLocaleString('pt-BR')}
                </div>

                {/* Warning indicator */}
                {warningCount > 0 && (
                  <div className="absolute top-4 right-4 w-3 h-3 bg-accent-amber rounded-full animate-pulse"></div>
                )}
              </div>

              {/* Camera Footer */}
              <div className="bg-bg-tertiary px-4 py-2 flex items-center justify-between border-t border-border">
                <div className="flex items-center gap-4 text-xs text-text-secondary">
                  <span>{camera.ipAddress}</span>
                  <span>•</span>
                  <span>{camera.model}</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  {detections.length > 0 ? (
                    <span className="text-accent-green">{detections.length} detecções</span>
                  ) : (
                    <span className="text-text-muted">Sem detecções</span>
                  )}
                </div>
              </div>
            </Card>
          );
        })}

        {/* Empty slots */}
        {Array.from({ length: Math.max(0, gridLayout - selectedCameras.length) }).map((_, i) => (
          <Card key={`empty-${i}`} className="border border-border border-dashed">
            <div className="aspect-video flex flex-col items-center justify-center text-text-muted">
              <Video className="w-12 h-12 mb-2 opacity-50" />
              <p className="text-sm font-medium">Slot Vazio</p>
              <p className="text-xs mt-1">Configure mais câmeras</p>
            </div>
          </Card>
        ))}
      </div>

      {/* Legend */}
      <Card className="bg-bg-tertiary border border-border">
        <div className="p-4">
          <h3 className="text-sm font-medium text-text-primary mb-3">Legenda de Detecção</h3>
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-accent-green"></div>
              <span className="text-xs text-text-secondary">
                Confiança alta ({'>'}80%)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-accent-amber"></div>
              <span className="text-xs text-text-secondary">
                Confiança média (50-80%)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-accent-red"></div>
              <span className="text-xs text-text-secondary">
                Confiança baixa ({'<'}50%)
              </span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
