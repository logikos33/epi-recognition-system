'use client'

import { useState } from 'react'
import { HLSCameraFeed } from './hls-camera-feed'
import type { Camera, SafeCamera } from '@/types/camera'

interface CameraGridProps {
  cameras: SafeCamera[]
}

const MAX_SELECTED_CAMERAS = 12

export function CameraGrid({ cameras }: CameraGridProps) {
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  const primaryCameras = selectedIds.slice(0, 3)
  const thumbnailCameras = selectedIds.slice(3, MAX_SELECTED_CAMERAS)

  const toggleCamera = (cameraId: number) => {
    setSelectedIds((prev) => {
      if (prev.includes(cameraId)) {
        return prev.filter((id) => id !== cameraId)
      } else if (prev.length < MAX_SELECTED_CAMERAS) {
        return [...prev, cameraId]
      }
      // Max reached, don't add
      return prev
    })
  }

  const selectedCameras = cameras.filter((c) => selectedIds.includes(c.id))

  return (
    <div className="space-y-4">
      {/* Camera selector */}
      <div className="flex flex-wrap gap-2">
        {cameras.map((camera) => (
          <button
            key={camera.id}
            onClick={() => toggleCamera(camera.id)}
            disabled={!selectedIds.includes(camera.id) && selectedIds.length >= MAX_SELECTED_CAMERAS}
            className={`px-3 py-1 rounded text-sm transition-colors ${
              selectedIds.includes(camera.id)
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            } ${
              !selectedIds.includes(camera.id) && selectedIds.length >= MAX_SELECTED_CAMERAS
                ? 'opacity-50 cursor-not-allowed'
                : 'cursor-pointer'
            }`}
            aria-label={`Toggle camera ${camera.name}`}
            aria-pressed={selectedIds.includes(camera.id)}
          >
            {camera.name}
          </button>
        ))}
      </div>

      {/* Selection count */}
      {selectedIds.length > 0 && (
        <p className="text-sm text-gray-600">
          {selectedIds.length} / {MAX_SELECTED_CAMERAS} cameras selected
        </p>
      )}

      {/* Primary cameras */}
      {primaryCameras.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {primaryCameras.map((cameraId) => {
            const camera = selectedCameras.find((c) => c.id === cameraId)
            if (!camera) return null
            return (
              <div key={camera.id} className="space-y-2">
                <h3 className="text-sm font-medium">{camera.name}</h3>
                <HLSCameraFeed cameraId={camera.id} mode="primary" />
              </div>
            )
          })}
        </div>
      )}

      {/* Thumbnail cameras */}
      {thumbnailCameras.length > 0 && (
        <div className="grid grid-cols-3 md:grid-cols-9 gap-2">
          {thumbnailCameras.map((cameraId) => {
            const camera = selectedCameras.find((c) => c.id === cameraId)
            if (!camera) return null
            return (
              <div key={camera.id} className="space-y-1">
                <p className="text-xs truncate">{camera.name}</p>
                <HLSCameraFeed cameraId={camera.id} mode="thumbnail" />
              </div>
            )
          })}
        </div>
      )}

      {/* Empty state */}
      {selectedIds.length === 0 && cameras.length > 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>Select cameras above to view streams</p>
        </div>
      )}
    </div>
  )
}
