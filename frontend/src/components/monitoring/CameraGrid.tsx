// frontend/src/components/monitoring/CameraGrid.tsx
'use client'

import { useState, useMemo } from 'react'
import { useCameraStreams } from '@/hooks/useCameraStreams'
import type { SessionInfo } from '@/types/monitoring'
import { CameraContainer } from './CameraContainer'
import { ThumbnailsList } from './ThumbnailsList'
import { CameraListSidebar } from './CameraListSidebar'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Video, Plus, RefreshCw, AlertCircle } from 'lucide-react'

const MAX_CAMERAS = 12
const PRIMARY_COUNT = 3

/**
 * Main camera grid component with 3 primary + 9 thumbnail cameras
 */
export function CameraGrid() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [expandedPrimaryId, setExpandedPrimaryId] = useState<number | null>(
    null
  )

  const {
    cameras,
    selectedCameraIds,
    primaryCameras,
    thumbnailCameras,
    loading,
    error,
    fetchCameras,
    addCamera,
    removeCamera,
    promoteToPrimary,
    demoteToThumbnail
  } = useCameraStreams({
    autoRefresh: true,
    refreshInterval: 30000 // 30 seconds
  })

  // Mock session data (will be replaced with real data in Task 2.5)
  const sessionsMap = useMemo<Map<number, SessionInfo | null>>(() => {
    const map = new Map<number, SessionInfo | null>()
    selectedCameraIds.forEach((id) => {
      // For now, all cameras have no active session
      map.set(id, null)
    })
    return map
  }, [selectedCameraIds])

  // Toggle camera selection
  const handleToggleCamera = (cameraId: number) => {
    if (selectedCameraIds.includes(cameraId)) {
      removeCamera(cameraId)
    } else {
      addCamera(cameraId)
    }
  }

  // Get primary camera objects
  const primaryCameraObjects = useMemo(() => {
    return primaryCameras
      .map((id) => cameras.find((c) => c.id === id))
      .filter((c): c is Exclude<typeof c, undefined> => c !== undefined)
  }, [primaryCameras, cameras])

  // Get thumbnail camera objects
  const thumbnailCameraObjects = useMemo(() => {
    return thumbnailCameras
      .map((id) => cameras.find((c) => c.id === id))
      .filter((c): c is Exclude<typeof c, undefined> => c !== undefined)
  }, [thumbnailCameras, cameras])

  // Loading state
  if (loading && cameras.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">Carregando câmeras...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error && cameras.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 mx-auto mb-4 text-destructive" />
          <h3 className="text-lg font-semibold mb-2">Erro ao carregar câmeras</h3>
          <p className="text-muted-foreground mb-4">{error}</p>
          <Button onClick={fetchCameras} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Tentar novamente
          </Button>
        </div>
      </div>
    )
  }

  // Empty state - no cameras configured
  if (cameras.length === 0) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center max-w-lg">
          <Video className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
          <h3 className="text-xl font-semibold mb-2">
            Nenhuma câmera configurada
          </h3>
          <p className="text-muted-foreground mb-6">
            Configure câmeras IP no sistema para começar a monitorar as baias
            de abastecimento.
          </p>
          <div className="bg-muted rounded-lg p-4 text-sm text-left">
            <p className="font-semibold mb-2">Para configurar câmeras:</p>
            <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
              <li>Acesse a página de Configurações</li>
              <li>Adicione as baias de abastecimento</li>
              <li>Configure as câmeras IP para cada baia</li>
              <li>Volte aqui para selecionar as câmeras</li>
            </ol>
          </div>
        </div>
      </div>
    )
  }

  // Empty state - no cameras selected
  if (selectedCameraIds.length === 0) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center max-w-lg">
          <Video className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
          <h3 className="text-xl font-semibold mb-2">
            Nenhuma câmera selecionada
          </h3>
          <p className="text-muted-foreground mb-6">
            Selecione até {MAX_CAMERAS} câmeras para monitoramento em tempo
            real.
          </p>
          <Button onClick={() => setIsSidebarOpen(true)} size="lg">
            <Plus className="w-4 h-4 mr-2" />
            Selecionar Câmeras
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-2xl font-bold">Grade de Câmeras</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {selectedCameraIds.length} câmera{selectedCameraIds.length !== 1 ? 's' : ''} selecionada
              {selectedCameraIds.length !== 1 ? 's' : ''}
            </p>
          </div>
          <Badge variant="secondary" className="text-sm">
            {primaryCameras.length} primária{primaryCameras.length !== 1 ? 's' : ''} /{' '}
            {thumbnailCameras.length} miniatura{thumbnailCameras.length !== 1 ? 's' : ''}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          {/* Refresh button */}
          <Button
            variant="outline"
            size="sm"
            onClick={fetchCameras}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </Button>

          {/* Add cameras button */}
          {selectedCameraIds.length < MAX_CAMERAS && (
            <Button
              onClick={() => setIsSidebarOpen(true)}
              size="sm"
              disabled={loading}
            >
              <Plus className="w-4 h-4 mr-2" />
              Adicionar Câmeras
            </Button>
          )}

          {/* Edit selection button */}
          {selectedCameraIds.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsSidebarOpen(true)}
            >
              Editar Seleção
            </Button>
          )}
        </div>
      </div>

      {/* Primary cameras grid */}
      {primaryCameraObjects.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3">Câmeras Primárias</h3>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {primaryCameraObjects.map((camera) => {
              const sessionInfo = sessionsMap.get(camera.id) || null
              const isExpanded = expandedPrimaryId === camera.id

              return (
                <div
                  key={camera.id}
                  className={`
                    transition-all duration-300
                    ${isExpanded ? 'lg:col-span-2' : ''}
                  `}
                >
                  <CameraContainer
                    camera={camera}
                    sessionInfo={sessionInfo}
                    isExpanded={isExpanded}
                    onToggleExpand={() =>
                      setExpandedPrimaryId(
                        isExpanded ? null : camera.id
                      )
                    }
                  />
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Thumbnails section */}
      {thumbnailCameraObjects.length > 0 && (
        <div className="flex-1">
          <h3 className="text-lg font-semibold mb-3">Miniaturas</h3>
          <ThumbnailsList
            cameras={thumbnailCameraObjects}
            sessionsMap={sessionsMap}
            onPromoteToPrimary={promoteToPrimary}
            onRemoveCamera={removeCamera}
          />
        </div>
      )}

      {/* Camera selection sidebar */}
      <CameraListSidebar
        allCameras={cameras}
        selectedCameraIds={selectedCameraIds}
        maxCameras={MAX_CAMERAS}
        onToggleCamera={handleToggleCamera}
        onClose={() => setIsSidebarOpen(false)}
        isOpen={isSidebarOpen}
      />
    </div>
  )
}
