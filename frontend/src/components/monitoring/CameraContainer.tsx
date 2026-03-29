// frontend/src/components/monitoring/CameraContainer.tsx
'use client'

import { useRef, useState, useEffect } from 'react'
import type { Camera, SessionInfo } from '@/types/monitoring'
import { InfoOverlay } from './InfoOverlay'
import { Maximize2, Minimize2, Plus, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface CameraContainerProps {
  camera: Camera
  sessionInfo: SessionInfo | null
  isExpanded: boolean
  onToggleExpand: () => void
  onCreateSession?: () => void
  onCompleteSession?: () => void
  canCompleteSession?: boolean
  className?: string
}

/**
 * Container for a single camera feed with overlay
 */
export function CameraContainer({
  camera,
  sessionInfo,
  isExpanded,
  onToggleExpand,
  onCreateSession,
  onCompleteSession,
  canCompleteSession = false,
  className = ''
}: CameraContainerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // For RTSP streams, we would use a different approach
    // For now, using mock with placeholder
    if (!camera.rtsp_url) {
      setError('No RTSP URL configured')
      return
    }

    // TODO: Implement RTSP stream handling
    // For now, just show placeholder
    setError('RTSP stream not yet implemented')

    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop())
      }
    }
  }, [camera, stream])

  return (
    <div className={`relative bg-black rounded-lg overflow-hidden ${className}`}>
      {/* Video/Placeholder */}
      <div className="aspect-video bg-gray-900 flex items-center justify-center">
        {error ? (
          <div className="text-center p-6">
            <p className="text-white/50 mb-2">{camera.name}</p>
            <p className="text-white/30 text-sm">{error}</p>
          </div>
        ) : (
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className="w-full h-full object-cover"
          />
        )}
      </div>

      {/* Session info overlay */}
      <InfoOverlay
        sessionInfo={sessionInfo}
        className="top-0 left-0 right-0"
      />

      {/* Expand/collapse button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={onToggleExpand}
        className="absolute bottom-2 right-2 bg-black/50 hover:bg-black/70 text-white"
      >
        {isExpanded ? (
          <Minimize2 className="w-4 h-4" />
        ) : (
          <Maximize2 className="w-4 h-4" />
        )}
      </Button>

      {/* Create session button (only show if no active session and callback provided) */}
      {!sessionInfo && onCreateSession && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onCreateSession}
          className="absolute bottom-2 left-2 bg-black/50 hover:bg-black/70 text-white"
          title="Criar nova sessão"
        >
          <Plus className="w-4 h-4" />
        </Button>
      )}

      {/* Complete session button (only show if active session and can complete) */}
      {sessionInfo && sessionInfo.status === 'active' && onCompleteSession && canCompleteSession && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onCompleteSession}
          className="absolute bottom-2 left-2 bg-green-600/80 hover:bg-green-700/90 text-white animate-pulse"
          title="Finalizar sessão de abastecimento"
        >
          <CheckCircle2 className="w-5 h-5" />
        </Button>
      )}

      {/* Detection canvas (for YOLO bounding boxes) */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 pointer-events-none"
      />
    </div>
  )
}