// frontend/src/components/monitoring/CameraGrid.tsx
'use client'

import { useState, useMemo, useEffect } from 'react'
import { useCameraStreams } from '@/hooks/useCameraStreams'
import { useFuelingSessions } from '@/hooks/useFuelingSessions'
import type { SessionInfo, FuelingSession, Camera } from '@/types/monitoring'
import { CameraContainer } from './CameraContainer'
import { ThumbnailsList } from './ThumbnailsList'
import { CameraListSidebar } from './CameraListSidebar'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Video, Plus, RefreshCw, AlertCircle, Loader2, CheckCircle2, Clock } from 'lucide-react'

const MAX_CAMERAS = 12
const PRIMARY_COUNT = 3
const MIN_SESSION_DURATION_MINUTES = 5 // Minimum duration before showing complete button

/**
 * Helper function to calculate elapsed time in HH:MM format
 */
function calculateElapsedTime(entryTime: Date): string {
  const now = new Date()
  const elapsedMs = now.getTime() - entryTime.getTime()
  const elapsedSeconds = Math.floor(elapsedMs / 1000)
  const hours = Math.floor(elapsedSeconds / 3600)
  const minutes = Math.floor((elapsedSeconds % 3600) / 60)
  const seconds = elapsedSeconds % 60

  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
}

/**
 * Helper function to convert FuelingSession to SessionInfo
 */
function sessionToSessionInfo(session: FuelingSession): SessionInfo {
  const entryTime = new Date(session.truck_entry_time)
  const totalProducts = Object.values(session.products_counted || {}).reduce((sum, count) => sum + count, 0)

  return {
    sessionId: session.id,
    licensePlate: session.license_plate,
    entryTime,
    elapsedTime: calculateElapsedTime(entryTime),
    productCount: totalProducts,
    currentWeight: session.final_weight || 0,
    status: session.status as 'active' | 'completed' | 'paused',
  }
}

/**
 * Main camera grid component with 3 primary + 9 thumbnail cameras
 */
export function CameraGrid() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [expandedPrimaryId, setExpandedPrimaryId] = useState<number | null>(null)
  const [isCreateSessionOpen, setIsCreateSessionOpen] = useState(false)
  const [isCompleteSessionOpen, setIsCompleteSessionOpen] = useState(false)
  const [selectedCameraForSession, setSelectedCameraForSession] = useState<Camera | null>(null)
  const [selectedSessionToComplete, setSelectedSessionToComplete] = useState<SessionInfo | null>(null)
  const [licensePlateInput, setLicensePlateInput] = useState('')
  const [elapsedTimeUpdater, setElapsedTimeUpdater] = useState(0)

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

  // Fetch active sessions with auto-refresh
  const {
    activeSessions,
    loading: sessionsLoading,
    error: sessionsError,
    createSession,
    completeSession,
    isCreating,
    isCompleting
  } = useFuelingSessions({
    autoRefresh: true,
    refreshInterval: 10000, // 10 seconds
    filters: { status: 'active' }
  })

  // Update elapsed time every second
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedTimeUpdater(prev => prev + 1)
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  // Map active sessions to cameras by bay_id
  const sessionsMap = useMemo<Map<number, SessionInfo | null>>(() => {
    const map = new Map<number, SessionInfo | null>()

    // Initialize all selected cameras with null (no session)
    selectedCameraIds.forEach((cameraId) => {
      map.set(cameraId, null)
    })

    // Map active sessions to cameras
    activeSessions.forEach((session) => {
      // Find camera that matches this session's bay_id and camera_id
      const camera = cameras.find(c => c.id === session.camera_id)
      if (camera && selectedCameraIds.includes(camera.id)) {
        const sessionInfo = sessionToSessionInfo(session)
        map.set(camera.id, sessionInfo)
      }
    })

    return map
  }, [activeSessions, cameras, selectedCameraIds, elapsedTimeUpdater])

  // Toggle camera selection
  const handleToggleCamera = (cameraId: number) => {
    if (selectedCameraIds.includes(cameraId)) {
      removeCamera(cameraId)
    } else {
      addCamera(cameraId)
    }
  }

  // Open create session dialog for a camera
  const handleOpenCreateSession = (camera: Camera) => {
    setSelectedCameraForSession(camera)
    setLicensePlateInput('')
    setIsCreateSessionOpen(true)
  }

  // Handle create session submission
  const handleCreateSession = async () => {
    if (!selectedCameraForSession || !licensePlateInput.trim()) {
      return
    }

    try {
      await createSession({
        bayId: selectedCameraForSession.bay_id,
        cameraId: selectedCameraForSession.id,
        licensePlate: licensePlateInput.trim().toUpperCase()
      })

      // Close dialog and reset state
      setIsCreateSessionOpen(false)
      setSelectedCameraForSession(null)
      setLicensePlateInput('')
    } catch (error) {
      console.error('Failed to create session:', error)
      // TODO: Show error toast to user
    }
  }

  // Handle cancel create session
  const handleCancelCreateSession = () => {
    setIsCreateSessionOpen(false)
    setSelectedCameraForSession(null)
    setLicensePlateInput('')
  }

  // Open complete session confirmation dialog
  const handleOpenCompleteSession = (sessionInfo: SessionInfo) => {
    setSelectedSessionToComplete(sessionInfo)
    setIsCompleteSessionOpen(true)
  }

  // Handle complete session submission
  const handleCompleteSession = async () => {
    if (!selectedSessionToComplete) {
      return
    }

    try {
      await completeSession(
        selectedSessionToComplete.sessionId,
        new Date().toISOString()
      )

      // Close dialog and reset state
      setIsCompleteSessionOpen(false)
      setSelectedSessionToComplete(null)
    } catch (error) {
      console.error('Failed to complete session:', error)
      // TODO: Show error toast to user
    }
  }

  // Handle cancel complete session
  const handleCancelCompleteSession = () => {
    setIsCompleteSessionOpen(false)
    setSelectedSessionToComplete(null)
  }

  // Check if session can be completed (minimum duration elapsed)
  const canCompleteSession = (sessionInfo: SessionInfo): boolean => {
    const now = new Date()
    const elapsedMs = now.getTime() - sessionInfo.entryTime.getTime()
    const elapsedMinutes = elapsedMs / (1000 * 60)
    return elapsedMinutes >= MIN_SESSION_DURATION_MINUTES
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
                    onCreateSession={() => handleOpenCreateSession(camera)}
                    onCompleteSession={
                      sessionInfo && sessionInfo.status === 'active'
                        ? () => handleOpenCompleteSession(sessionInfo)
                        : undefined
                    }
                    canCompleteSession={
                      sessionInfo ? canCompleteSession(sessionInfo) : false
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
            onCreateSession={handleOpenCreateSession}
            onCompleteSession={handleOpenCompleteSession}
            canCompleteSession={canCompleteSession}
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

      {/* Create session dialog */}
      <Dialog open={isCreateSessionOpen} onOpenChange={setIsCreateSessionOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Nova Sessão de Abastecimento</DialogTitle>
            <DialogDescription>
              Crie uma nova sessão para a câmera {selectedCameraForSession?.name} na Baía {selectedCameraForSession?.bay_id}.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="license-plate" className="text-right">
                Placa
              </Label>
              <Input
                id="license-plate"
                value={licensePlateInput}
                onChange={(e) => setLicensePlateInput(e.target.value.toUpperCase())}
                placeholder="ABC-1234"
                className="col-span-3"
                maxLength={8}
                autoFocus
              />
            </div>
            <div className="text-sm text-muted-foreground">
              <p>Informe a placa do caminhão para iniciar o monitoramento.</p>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleCancelCreateSession}
              disabled={isCreating}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              onClick={handleCreateSession}
              disabled={!licensePlateInput.trim() || isCreating}
            >
              {isCreating ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Criando...
                </>
              ) : (
                'Criar Sessão'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Complete session confirmation dialog */}
      <Dialog open={isCompleteSessionOpen} onOpenChange={setIsCompleteSessionOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Finalizar Sessão de Abastecimento</DialogTitle>
            <DialogDescription>
              Confirme a finalização da sessão para a placa {selectedSessionToComplete?.licensePlate}.
            </DialogDescription>
          </DialogHeader>
          {selectedSessionToComplete && (
            <div className="grid gap-4 py-4">
              {/* Session summary */}
              <div className="bg-muted rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Placa do Veículo:</span>
                  <span className="font-semibold">{selectedSessionToComplete.licensePlate}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Hora de Entrada:</span>
                  <span className="font-mono text-sm">
                    {selectedSessionToComplete.entryTime.toLocaleTimeString('pt-BR')}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Tempo Decorrido:</span>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-muted-foreground" />
                    <span className="font-mono font-semibold text-lg">
                      {selectedSessionToComplete.elapsedTime}
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Produtos Contados:</span>
                  <span className="font-semibold text-lg">
                    {selectedSessionToComplete.productCount}
                  </span>
                </div>
                {selectedSessionToComplete.currentWeight > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Peso Final:</span>
                    <span className="font-semibold">
                      {selectedSessionToComplete.currentWeight.toLocaleString('pt-BR')} kg
                    </span>
                  </div>
                )}
              </div>

              {/* Warning message */}
              <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-amber-800 dark:text-amber-200">
                    <p className="font-semibold mb-1">Confirmação necessária</p>
                    <p className="text-muted-foreground">
                      Certifique-se de que o caminhão tenha deixado a baia antes de finalizar a sessão.
                      Esta ação não pode ser desfeita.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleCancelCompleteSession}
              disabled={isCompleting}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              onClick={handleCompleteSession}
              disabled={isCompleting}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              {isCompleting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Finalizando...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  Finalizar Sessão
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
