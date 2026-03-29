// frontend/src/components/monitoring/ThumbnailsList.tsx
'use client'

import { useState } from 'react'
import type { Camera, SessionInfo } from '@/types/monitoring'
import { CameraContainer } from './CameraContainer'
import { ArrowUpToLine, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface ThumbnailsListProps {
  cameras: Camera[]
  sessionsMap: Map<number, SessionInfo | null>
  onPromoteToPrimary: (cameraId: number) => void
  onRemoveCamera: (cameraId: number) => void
}

/**
 * Grid of up to 9 thumbnail cameras with hover controls
 */
export function ThumbnailsList({
  cameras,
  sessionsMap,
  onPromoteToPrimary,
  onRemoveCamera
}: ThumbnailsListProps) {
  const [hoveredCameraId, setHoveredCameraId] = useState<number | null>(null)

  if (cameras.length === 0) {
    return (
      <div className="bg-muted rounded-lg p-8 text-center">
        <p className="text-muted-foreground text-sm">
          Nenhuma câmera em miniatura
        </p>
        <p className="text-muted-foreground/60 text-xs mt-1">
          Adicione mais câmeras para ver miniaturas
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-9 gap-3">
      {cameras.map((camera) => {
        const sessionInfo = sessionsMap.get(camera.id) || null
        const isHovered = hoveredCameraId === camera.id

        return (
          <div
            key={camera.id}
            className="relative group"
            onMouseEnter={() => setHoveredCameraId(camera.id)}
            onMouseLeave={() => setHoveredCameraId(null)}
          >
            {/* Thumbnail container */}
            <div className="aspect-video bg-black rounded-lg overflow-hidden">
              <CameraContainer
                camera={camera}
                sessionInfo={sessionInfo}
                isExpanded={false}
                onToggleExpand={() => {}}
                className="h-full"
              />
            </div>

            {/* Camera name badge */}
            <div className="absolute top-2 left-2">
              <Badge variant="secondary" className="text-xs">
                {camera.name}
              </Badge>
            </div>

            {/* Hover controls */}
            {isHovered && (
              <div className="absolute inset-0 bg-black/60 backdrop-blur-sm rounded-lg flex items-center justify-center gap-2 transition-opacity">
                {/* Promote to primary button */}
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => onPromoteToPrimary(camera.id)}
                  className="bg-white/90 hover:bg-white text-black"
                  title="Promover para primária"
                >
                  <ArrowUpToLine className="w-4 h-4" />
                </Button>

                {/* Remove button */}
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => onRemoveCamera(camera.id)}
                  title="Remover câmera"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            )}

            {/* Session status indicator */}
            {sessionInfo?.status === 'active' && (
              <div className="absolute top-2 right-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
