// frontend/src/components/monitoring/CameraListSidebar.tsx
'use client'

import { useState } from 'react'
import type { Camera } from '@/types/monitoring'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { X, Check, Video } from 'lucide-react'

interface CameraListSidebarProps {
  allCameras: Camera[]
  selectedCameraIds: number[]
  maxCameras?: number
  onToggleCamera: (cameraId: number) => void
  onClose: () => void
  isOpen: boolean
}

/**
 * Slide-out sidebar for camera selection
 */
export function CameraListSidebar({
  allCameras,
  selectedCameraIds,
  maxCameras = 12,
  onToggleCamera,
  onClose,
  isOpen
}: CameraListSidebarProps) {
  const [filterInactive, setFilterInactive] = useState(false)

  const filteredCameras = filterInactive
    ? allCameras.filter((c) => c.is_active)
    : allCameras

  const isMaxReached = selectedCameraIds.length >= maxCameras

  if (!isOpen) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Sidebar */}
      <div className="relative w-full max-w-md bg-background shadow-xl h-full flex flex-col">
        {/* Header */}
        <div className="border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">Selecionar Câmeras</h2>
              <p className="text-sm text-muted-foreground mt-1">
                {selectedCameraIds.length} / {maxCameras} câmeras selecionadas
              </p>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="w-5 h-5" />
            </Button>
          </div>

          {/* Filter toggle */}
          <div className="flex items-center gap-2 mt-4">
            <Switch
              id="filter-inactive"
              checked={filterInactive}
              onCheckedChange={setFilterInactive}
            />
            <label
              htmlFor="filter-inactive"
              className="text-sm cursor-pointer select-none"
            >
              Mostrar apenas câmeras ativas
            </label>
          </div>

          {/* Max reached warning */}
          {isMaxReached && (
            <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
              <p className="text-sm text-yellow-700 dark:text-yellow-400">
                Limite máximo de {maxCameras} câmeras atingido. Remova uma
                câmera para adicionar outra.
              </p>
            </div>
          )}
        </div>

        {/* Camera list */}
        <ScrollArea className="flex-1">
          <div className="p-4 space-y-2">
            {filteredCameras.length === 0 ? (
              <div className="text-center py-8">
                <Video className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
                <p className="text-muted-foreground">
                  Nenhuma câmera disponível
                </p>
              </div>
            ) : (
              filteredCameras.map((camera) => {
                const isSelected = selectedCameraIds.includes(camera.id)

                return (
                  <div
                    key={camera.id}
                    className={`
                      flex items-center justify-between p-4 rounded-lg border-2 transition-colors
                      ${isSelected
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                      }
                    `}
                  >
                    {/* Camera info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{camera.name}</h3>
                        {!camera.is_active && (
                          <Badge variant="secondary" className="text-xs">
                            Inativa
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {camera.bay_name || `Baia ${camera.bay_id}`}
                      </p>
                      {camera.rtsp_url && (
                        <p className="text-xs text-muted-foreground/70 mt-1 truncate">
                          {camera.rtsp_url}
                        </p>
                      )}
                    </div>

                    {/* Toggle switch */}
                    <button
                      onClick={() => onToggleCamera(camera.id)}
                      disabled={!isSelected && isMaxReached}
                      className={`
                        ml-4 p-2 rounded-full transition-colors
                        ${isSelected
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted hover:bg-muted/80'
                        }
                        ${!isSelected && isMaxReached ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                      `}
                      aria-label={isSelected ? 'Remover câmera' : 'Adicionar câmera'}
                    >
                      {isSelected ? (
                        <Check className="w-5 h-5" />
                      ) : (
                        <Video className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                )
              })
            )}
          </div>
        </ScrollArea>

        {/* Footer */}
        <div className="border-t px-6 py-4">
          <Button onClick={onClose} className="w-full" size="lg">
            Concluir Seleção
          </Button>
        </div>
      </div>
    </div>
  )
}
