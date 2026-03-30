'use client'

import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'
import { io } from 'socket.io-client'
import type { HLSCameraFeedProps, Detection } from '@/types/camera'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

export function HLSCameraFeed({ cameraId, mode }: HLSCameraFeedProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [status, setStatus] = useState<'idle' | 'connecting' | 'streaming' | 'error'>('idle')
  const [detections, setDetections] = useState<any[]>([])

  // Initialize HLS
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const hlsUrl = `${API_URL}/streams/${cameraId}/stream.m3u8`
    setStatus('connecting')

    if (Hls.isSupported()) {
      const hls = new Hls({
        maxBufferLength: 5,
        lowLatencyMode: true
      })
      hls.loadSource(hlsUrl)
      hls.attachMedia(video)

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setStatus('streaming')
        video.play().catch(console.error)
      })

      return () => hls.destroy()
    }
  }, [cameraId])

  // WebSocket for detections
  useEffect(() => {
    const socket = io(API_URL)
    socket.emit('subscribe_camera', { camera_id: cameraId })

    socket.on('detection', (data: Detection) => {
      if (data.camera_id === cameraId) {
        setDetections(data.detections)
      }
    })

    return () => socket.disconnect()
  }, [cameraId])

  const sizeClass = mode === 'primary' ? 'min-h-[300px]' : 'min-h-[120px]'

  return (
    <div className={`relative bg-black rounded-lg overflow-hidden ${sizeClass}`}>
      <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
      <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" />
      <div className="absolute top-2 left-2">
        {status === 'streaming' && <span className="bg-green-500 text-white px-2 py-1 rounded text-xs">● Live</span>}
      </div>
    </div>
  )
}
