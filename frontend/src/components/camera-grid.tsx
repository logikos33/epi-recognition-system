'use client'

import { useState } from 'react'
import { HLSCameraFeed } from './hls-camera-feed'
import type { Camera } from '@/types/camera'

interface CameraGridProps {
  cameras: Camera[]
}

export function CameraGrid({ cameras }: CameraGridProps) {
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  const primaryCameras = selectedIds.slice(0, 3)
  const thumbnailCameras = selectedIds.slice(3, 12)

  const toggleCamera = (cameraId: number) => {
    if (selectedIds.includes(cameraId)) {
      setSelectedIds(selectedIds.filter(id => id !== cameraId))
    } else if (selectedIds.length < 12) {
      setSelectedIds([...selectedIds, cameraId])
    }
  }

  const selectedCameras = cameras.filter(c => selectedIds.includes(c.id))

  return (
    <div className="space-y-4">
      {/* Camera selector */}
      <div className="flex flex-wrap gap-2">
        {cameras.map(camera => (
          <button key={camera.id} onClick={() => toggleCamera(camera.id)}
            className={`px-3 py-1 rounded text-sm ${
              selectedIds.includes(camera.id) ? 'bg-blue-500 text-white' : 'bg-gray-200'
            }`}>
            {camera.name}
          </button>
        ))}
      </div>

      {/* Primary cameras */}
      {primaryCameras.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {primaryCameras.map(cameraId => {
            const camera = selectedCameras.find(c => c.id === cameraId)
            return camera ? (
              <div key={camera.id} className="space-y-2">
                <h3 className="text-sm font-medium">{camera.name}</h3>
                <HLSCameraFeed cameraId={camera.id} mode="primary" />
              </div>
            ) : null
          })}
        </div>
      )}

      {/* Thumbnail cameras */}
      {thumbnailCameras.length > 0 && (
        <div className="grid grid-cols-3 md:grid-cols-9 gap-2">
          {thumbnailCameras.map(cameraId => {
            const camera = selectedCameras.find(c => c.id === cameraId)
            return camera ? (
              <div key={camera.id}>
                <p className="text-xs">{camera.name}</p>
                <HLSCameraFeed cameraId={camera.id} mode="thumbnail" />
              </div>
            ) : null
          })}
        </div>
      )}
    </div>
  )
}
