'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '@/lib/api'
import { AuthProtected } from '@/components/auth-protected'
import { Camera, Settings, Monitor, Maximize2, Grid3x3, Grid2x2, Layout, Clock, Package, Car, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Switch } from '@/components/ui/switch'
import { useYOLOWorker } from '@/hooks/useYOLOWorker'
import { useVirtualizedStreams } from '@/hooks/useVirtualizedStreams'
import { useStreamReconnection } from '@/hooks/useStreamReconnection'

// Types
interface CameraData {
  id: number
  bay_id: number
  name: string
  rtsp_url: string | null
  is_active: boolean
  position_order: number
  bay_name?: string
}

interface GridLayout {
  id: string
  name: string
  cols: number
  maxCameras: number
}

// Grid layouts disponíveis
const GRID_LAYOUTS: GridLayout[] = [
  { id: '1x1', name: '1 Câmera', cols: 1, maxCameras: 1 },
  { id: '2x2', name: '4 Câmeras', cols: 2, maxCameras: 4 },
  { id: '3x3', name: '9 Câmeras', cols: 3, maxCameras: 9 },
  { id: '4x4', name: '16 Câmeras', cols: 4, maxCameras: 16 },
]

export default function MonitoringPage() {
  const [allCameras, setAllCameras] = useState<CameraData[]>([])
  const [selectedCameraIds, setSelectedCameraIds] = useState<number[]>([])
  const [loading, setLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [currentLayout, setCurrentLayout] = useState<GridLayout>(GRID_LAYOUTS[2]) // Default 3x3
  const [currentTime, setCurrentTime] = useState(new Date())
  const [showCameraInfo, setShowCameraInfo] = useState(true)
  const [elapsedTimeUpdater, setElapsedTimeUpdater] = useState(0)

  // Refs for camera elements (IntersectionObserver)
  const cameraElementRefs = useRef<Map<number, HTMLDivElement>>(new Map())

  // Virtualized streams management (max 9 active streams)
  const { activeStreams, visibleCameras, activateStream, deactivateStream, isStreamActive, registerCamera } = useVirtualizedStreams({
    maxActiveStreams: 9
  })

  // Stream reconnection with exponential backoff
  const { reconnectingStreams, failedStreams, markStreamFailed, markStreamRecovered, getBackoffTime } = useStreamReconnection({
    maxAttempts: 5,
    initialBackoff: 1000, // 1 second
    maxBackoff: 30000, // 30 seconds
    backoffMultiplier: 2
  })

  // Fetch YOLO data for selected cameras (polls every 3 seconds via Web Worker)
  const { data: yoloData, isReady: yoloReady } = useYOLOWorker(selectedCameraIds, 3000)

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      // Fetch cameras
      const camerasResult = await api.listCameras()
      if (camerasResult.success) {
        const activeCameras = camerasResult.cameras.filter((c: CameraData) => c.is_active)
        setAllCameras(activeCameras)
      }
    } catch (err: any) {
      console.error('Error fetching data:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial data fetch and restore selection
  useEffect(() => {
    // Restore selected cameras from localStorage
    const saved = localStorage.getItem('selectedCameras')
    if (saved) {
      try {
        const savedIds = JSON.parse(saved)
        if (Array.isArray(savedIds) && savedIds.length > 0) {
          setSelectedCameraIds(savedIds)
        }
      } catch (e) {
        console.error('Error parsing saved cameras:', e)
      }
    }

    // Restore layout from localStorage
    const savedLayout = localStorage.getItem('gridLayout')
    if (savedLayout) {
      const layout = GRID_LAYOUTS.find(l => l.id === savedLayout)
      if (layout) {
        setCurrentLayout(layout)
      }
    }

    fetchData()

    // Refresh every 10 seconds
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, []) // Empty dependency array - only run on mount

  // Auto-select cameras if none selected
  useEffect(() => {
    const saved = localStorage.getItem('selectedCameras')
    if (!saved && selectedCameraIds.length === 0 && allCameras.length > 0) {
      const toSelect = allCameras.slice(0, currentLayout.maxCameras).map(c => c.id)
      setSelectedCameraIds(toSelect)
    }
  }, [allCameras, currentLayout.maxCameras, selectedCameraIds.length])

  // Update current time every second
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Force YOLO data refresh every second for real-time elapsed time
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedTimeUpdater(prev => prev + 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Save selected cameras when changed (but not on initial load)
  useEffect(() => {
    if (selectedCameraIds.length > 0 && !loading) {
      localStorage.setItem('selectedCameras', JSON.stringify(selectedCameraIds))
    }
  }, [selectedCameraIds, loading])

  // Save layout when changed
  useEffect(() => {
    localStorage.setItem('gridLayout', currentLayout.id)
  }, [currentLayout])

  // Toggle camera selection
  const toggleCamera = (cameraId: number) => {
    if (selectedCameraIds.includes(cameraId)) {
      // Remove camera (minimum 1)
      if (selectedCameraIds.length > 1) {
        setSelectedCameraIds(prev => prev.filter(id => id !== cameraId))
      }
    } else {
      // Add camera (respect layout limit)
      if (selectedCameraIds.length < currentLayout.maxCameras) {
        setSelectedCameraIds(prev => [...prev, cameraId])
      }
    }
  }

  // Swap cameras in grid
  const swapCameras = (index1: number, index2: number) => {
    const newSelection = [...selectedCameraIds]
    const temp = newSelection[index1]
    newSelection[index1] = newSelection[index2]
    newSelection[index2] = temp
    setSelectedCameraIds(newSelection)
  }

  // Format time
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  // Toggle fullscreen
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen()
    } else {
      document.exitFullscreen()
    }
  }

  // Get selected camera objects
  const selectedCameras = selectedCameraIds
    .map(id => allCameras.find(c => c.id === id))
    .filter((c): c is CameraData => c !== undefined)

  // Fill empty slots with placeholders
  const displayCameras: (CameraData | null)[] = [...selectedCameras]
  while (displayCameras.length < currentLayout.maxCameras) {
    displayCameras.push(null)
  }

  // Register camera elements for IntersectionObserver (virtualization)
  useEffect(() => {
    const cleanupFunctions: Array<() => void> = []

    displayCameras.forEach((camera) => {
      if (!camera) return

      const element = cameraElementRefs.current.get(camera.id)
      if (element) {
        const cleanup = registerCamera(camera.id, element)
        cleanupFunctions.push(cleanup)
      }
    })

    // Cleanup all observers on unmount
    return () => {
      cleanupFunctions.forEach(cleanup => cleanup())
    }
  }, [displayCameras, registerCamera])

  // Update active streams display counter
  const activeStreamCount = activeStreams.size

  if (loading) {
    return (
      <AuthProtected>
        <div className="h-screen bg-black flex items-center justify-center">
          <div className="text-center">
            <Monitor className="w-16 h-16 animate-pulse mx-auto mb-4 text-gray-500" />
            <p className="text-gray-400">Carregando monitoramento...</p>
          </div>
        </div>
      </AuthProtected>
    )
  }

  return (
    <AuthProtected>
      <div className="h-screen bg-black flex flex-col overflow-hidden">
        {/* Top Bar */}
        <div className="bg-gray-900 border-b border-gray-800 px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Monitor className="w-6 h-6 text-blue-500" />
            <h1 className="text-white font-semibold text-lg">Sistema de Monitoramento</h1>
            <span className="text-gray-400">|</span>
            <span className="text-blue-400 font-mono text-xl">{formatTime(currentTime)}</span>
            <span className="text-gray-400">|</span>
            <span className={`text-xs font-mono px-2 py-1 rounded ${activeStreamCount >= 9 ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>
              Streams: {activeStreamCount}/9
            </span>
            {(reconnectingStreams.size > 0 || failedStreams.size > 0) && (
              <>
                <span className="text-gray-400">|</span>
                <div className="flex items-center gap-1 text-xs font-mono">
                  {reconnectingStreams.size > 0 && (
                    <span className="px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400 animate-pulse">
                      Reconectando: {reconnectingStreams.size}
                    </span>
                  )}
                  {failedStreams.size > 0 && (
                    <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">
                      Falhas: {failedStreams.size}
                    </span>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Grid layout selector */}
            <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
              {GRID_LAYOUTS.map(layout => (
                <button
                  key={layout.id}
                  onClick={() => setCurrentLayout(layout)}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    currentLayout.id === layout.id
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-700'
                  }`}
                  title={layout.name}
                >
                  {layout.id === '1x1' && '1x1'}
                  {layout.id === '2x2' && '2x2'}
                  {layout.id === '3x3' && '3x3'}
                  {layout.id === '4x4' && '4x4'}
                </button>
              ))}
            </div>

            <div className="h-6 w-px bg-gray-700" />

            {/* Show camera info toggle */}
            <div className="flex items-center gap-2 px-3">
              <Switch
                checked={showCameraInfo}
                onCheckedChange={setShowCameraInfo}
                className="data-[state=checked]:bg-blue-600"
              />
              <span className="text-gray-400 text-sm">Info</span>
            </div>

            <Button
              onClick={() => setSidebarOpen(true)}
              variant="ghost"
              size="sm"
              className="text-gray-400 hover:text-white"
            >
              <Grid3x3 className="w-4 h-4 mr-2" />
              Selecionar Câmeras
            </Button>

            <Button
              onClick={toggleFullscreen}
              variant="ghost"
              size="sm"
              className="text-gray-400 hover:text-white"
            >
              <Maximize2 className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Camera Grid */}
        <div className="flex-1 p-2 overflow-hidden">
          <div
            className="grid gap-1 h-full"
            style={{
              gridTemplateColumns: `repeat(${currentLayout.cols}, minmax(0, 1fr))`,
              gridTemplateRows: `repeat(${currentLayout.cols}, minmax(0, 1fr))`
            }}
          >
            {displayCameras.map((camera, index) => {
              const yoloInfo = camera ? yoloData.get(camera.id) : null
              const hasCamera = camera !== null

              return (
                <div
                  key={camera?.id || `empty-${index}`}
                  ref={(el) => {
                    if (el && camera) {
                      cameraElementRefs.current.set(camera.id, el)
                    }
                  }}
                  className="relative bg-gray-900 rounded overflow-hidden group"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault()
                    const fromIndex = parseInt(e.dataTransfer.getData('cameraIndex'))
                    if (!isNaN(fromIndex)) {
                      swapCameras(fromIndex, index)
                    }
                  }}
                  draggable={hasCamera}
                  onDragStart={(e) => {
                    e.dataTransfer.setData('cameraIndex', index.toString())
                  }}
                >
                  {hasCamera ? (
                    <>
                      {/* Camera placeholder/background with stream state */}
                      <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-gray-800 to-gray-900">
                        {isStreamActive(camera.id) ? (
                          /* Active stream - show actual content or stream placeholder */
                          camera.rtsp_url ? (
                            <div className="text-center">
                              <Camera className="w-16 h-16 mx-auto mb-3 text-green-500 animate-pulse" />
                              <p className="text-green-500 text-sm font-medium">Stream Ativo</p>
                              <p className="text-gray-500 text-xs mt-1">{camera.rtsp_url}</p>
                            </div>
                          ) : (
                            <div className="text-center">
                              <Camera className="w-16 h-16 mx-auto mb-3 text-green-500 animate-pulse" />
                              <p className="text-green-500 text-sm font-medium">Monitorando</p>
                            </div>
                          )
                        ) : (
                          /* Inactive stream - frozen placeholder */
                          <div className="text-center opacity-50">
                            <Play className="w-12 h-12 mx-auto mb-2 text-gray-600" />
                            <p className="text-gray-600 text-sm">Stream Pausado</p>
                            <p className="text-gray-700 text-xs mt-1">
                              {activeStreams.size >= 9 ? 'Máximo de streams ativos' : 'Fora do viewport'}
                            </p>
                          </div>
                        )}
                      </div>

                      {/* Camera info overlay */}
                      {showCameraInfo && (
                        <div className="absolute top-0 left-0 right-0 bg-gradient-to-b from-black/80 to-transparent p-2">
                          <div className="flex items-start justify-between">
                            <div>
                              <h3 className="text-white text-sm font-semibold">{camera.name}</h3>
                              <p className="text-gray-400 text-xs">{camera.bay_name || `Baia ${camera.bay_id}`}</p>
                            </div>
                            <div className="flex items-center gap-2">
                              {yoloInfo && (
                                <Badge className="bg-red-600 text-white text-xs animate-pulse">
                                  GRAVANDO
                                </Badge>
                              )}
                              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                            </div>
                          </div>
                        </div>
                      )}

                      {/* YOLO Data HUD Overlay */}
                      {camera && (
                        <div className="absolute bottom-0 left-0 right-0 bg-black/70 backdrop-blur-sm p-2 border-t border-blue-500/30">
                          {yoloInfo ? (
                            /* Active detection */
                            <div className="space-y-1">
                              {/* License Plate - Highlighted */}
                              <div className="flex items-center gap-2">
                                <Car className="w-3 h-3 text-amber-400" />
                                <span className="text-gray-400 text-xs">Placa:</span>
                                <span className="font-mono text-sm font-bold text-amber-400 tracking-wide">
                                  {yoloInfo.license_plate || '---'}
                                </span>
                              </div>

                              {/* Items Count */}
                              <div className="flex items-center gap-2">
                                <Package className="w-3 h-3 text-green-400" />
                                <span className="text-gray-400 text-xs">Itens:</span>
                                <span className="font-mono text-sm font-bold text-green-400">
                                  {yoloInfo.item_count}
                                </span>
                              </div>

                              {/* Start Time */}
                              <div className="flex items-center gap-2">
                                <Clock className="w-3 h-3 text-cyan-400" />
                                <span className="text-gray-400 text-xs">Início:</span>
                                <span className="font-mono text-xs text-cyan-400">
                                  {new Date(yoloInfo.truck_entry_time).toLocaleTimeString('pt-BR', {
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  })}
                                </span>
                              </div>

                              {/* Elapsed Time */}
                              <div className="flex items-center gap-2">
                                <Clock className="w-3 h-3 text-blue-400" />
                                <span className="text-gray-400 text-xs">Tempo:</span>
                                <span className="font-mono text-sm font-semibold text-blue-400">
                                  {yoloInfo.elapsed_time_formatted}
                                </span>
                              </div>
                            </div>
                          ) : (
                            /* No detection - Waiting state */
                            <div className="flex items-center justify-center py-1">
                              <span className="text-gray-500 text-xs italic">
                                Aguardando detecção...
                              </span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Timestamp overlay */}
                      {showCameraInfo && (
                        <div className="absolute bottom-20 right-2">
                          <span className="text-white text-xs font-mono bg-black/50 px-2 py-1 rounded">
                            {formatTime(currentTime)}
                          </span>
                        </div>
                      )}

                      {/* Drag handle indicator */}
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Layout className="w-8 h-8 text-white/50" />
                      </div>
                    </>
                  ) : (
                    /* Empty slot */
                    <div className="h-full flex items-center justify-center text-gray-700">
                      <div className="text-center">
                        <Monitor className="w-12 h-12 mx-auto mb-2 opacity-30" />
                        <p className="text-sm">Vazio</p>
                        <p className="text-xs text-gray-600">Posição {index + 1}</p>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Camera Selection Sidebar */}
        {sidebarOpen && (
          <div className="fixed inset-0 z-50 flex">
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setSidebarOpen(false)}
            />

            {/* Sidebar */}
            <div className="relative w-80 bg-gray-900 border-l border-gray-800 h-full flex flex-col">
              <div className="p-4 border-b border-gray-800">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-white font-semibold text-lg">Selecionar Câmeras</h2>
                  <button
                    onClick={() => setSidebarOpen(false)}
                    className="text-gray-400 hover:text-white"
                  >
                    ✕
                  </button>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">
                    {selectedCameraIds.length} / {currentLayout.maxCameras} selecionadas
                  </span>
                  <span className="text-blue-400">{currentLayout.name}</span>
                </div>
              </div>

              <ScrollArea className="flex-1 p-4">
                <div className="space-y-2">
                  {allCameras.map((camera) => {
                    const isSelected = selectedCameraIds.includes(camera.id)
                    const isDisabled = !isSelected && selectedCameraIds.length >= currentLayout.maxCameras
                    const yoloInfo = yoloData.get(camera.id)

                    return (
                      <div
                        key={camera.id}
                        onClick={() => !isDisabled && toggleCamera(camera.id)}
                        className={`
                          p-3 rounded-lg border-2 cursor-pointer transition-all
                          ${isSelected
                            ? 'border-blue-500 bg-blue-500/10'
                            : 'border-gray-700 bg-gray-800 hover:border-gray-600'
                          }
                          ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''}
                        `}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <h3 className="text-white text-sm font-medium">{camera.name}</h3>
                            <p className="text-gray-400 text-xs">{camera.bay_name || `Baia ${camera.bay_id}`}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {yoloInfo && (
                              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" title="Gravando" />
                            )}
                            <div className={`w-2 h-2 rounded-full ${camera.is_active ? 'bg-green-500' : 'bg-gray-500'}`} />
                          </div>
                        </div>

                        {isSelected && (
                          <div className="flex items-center gap-2 text-xs">
                            <span className="text-blue-400 font-medium">Posição:</span>
                            <span className="text-gray-400">
                              {selectedCameraIds.indexOf(camera.id) + 1}
                            </span>
                          </div>
                        )}
                      </div>
                    )
                  })}

                  {allCameras.length === 0 && (
                    <div className="text-center py-8">
                      <Monitor className="w-12 h-12 mx-auto mb-2 text-gray-700" />
                      <p className="text-gray-500 text-sm">Nenhuma câmera disponível</p>
                    </div>
                  )}
                </div>
              </ScrollArea>

              <div className="p-4 border-t border-gray-800">
                <Button
                  onClick={() => setSidebarOpen(false)}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  Concluir
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AuthProtected>
  )
}
