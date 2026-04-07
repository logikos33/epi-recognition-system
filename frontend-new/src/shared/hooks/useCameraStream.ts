/**
 * useCameraStream — HLS video stream + real-time YOLO detections
 *
 * Manages:
 * 1. HLS stream lifecycle (start via API, play via hls.js)
 * 2. Real-time detections via useSocket
 * 3. Stream status polling
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useSocket } from './useSocket'

interface Detection {
  camera_id: string
  timestamp: number
  detections: Array<{
    class: string
    confidence: number
    bbox: { x1: number; y1: number; x2: number; y2: number }
  }>
}

interface StreamStatus {
  camera_id: string
  active: boolean
  playlist_url: string | null
}

interface UseCameraStreamOptions {
  cameraId: string
  videoRef: React.RefObject<HTMLVideoElement>
  apiBaseUrl?: string
  autoStart?: boolean
}

interface UseCameraStreamReturn {
  isStreaming: boolean
  isLoading: boolean
  error: string | null
  detections: Detection['detections']
  streamUrl: string | null
  startStream: () => Promise<void>
  stopStream: () => Promise<void>
}

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function useCameraStream({
  cameraId,
  videoRef,
  apiBaseUrl = '',
  autoStart = false,
}: UseCameraStreamOptions): UseCameraStreamReturn {
  const [isStreaming, setIsStreaming] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [streamUrl, setStreamUrl] = useState<string | null>(null)
  const [detections, setDetections] = useState<Detection['detections']>([])
  const hlsRef = useRef<any>(null)

  const { connected, joinCamera, leaveCamera, onDetection } = useSocket({ baseUrl: apiBaseUrl })

  // Listen to detections when connected
  useEffect(() => {
    if (!connected) return
    joinCamera(cameraId)
    const unsubscribe = onDetection(cameraId, (data) => {
      setDetections(data.detections)
    })
    return () => {
      unsubscribe()
      leaveCamera(cameraId)
    }
  }, [connected, cameraId, joinCamera, leaveCamera, onDetection])

  // Initialize HLS player
  const initHls = useCallback(
    (url: string) => {
      const video = videoRef.current
      if (!video) return

      // Try native HLS first (Safari)
      if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = url
        video.play().catch(() => {})
        return
      }

      // Use hls.js for other browsers
      import('hls.js').then(({ default: Hls }) => {
        if (!Hls.isSupported()) {
          setError('HLS not supported in this browser')
          return
        }
        if (hlsRef.current) hlsRef.current.destroy()
        const hls = new Hls({
          enableWorker: true,
          lowLatencyMode: true,
          backBufferLength: 90,
        })
        hls.loadSource(url)
        hls.attachMedia(video)
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          video.play().catch(() => {})
        })
        hls.on(Hls.Events.ERROR, (_: unknown, data: any) => {
          if (data.fatal) {
            setError(`HLS error: ${data.details}`)
            setIsStreaming(false)
          }
        })
        hlsRef.current = hls
      }).catch(() => {
        setError('hls.js not available')
      })
    },
    [videoRef]
  )

  const startStream = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const resp = await fetch(`${apiBaseUrl}/api/v1/cameras/${cameraId}/stream/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      })
      if (!resp.ok) throw new Error(`Start stream failed: ${resp.status}`)

      // Poll for stream status
      let attempts = 0
      const poll = async (): Promise<string | null> => {
        const statusResp = await fetch(
          `${apiBaseUrl}/api/v1/cameras/${cameraId}/stream/status`,
          { headers: getAuthHeader() }
        )
        const status: { data: StreamStatus } = await statusResp.json()
        if (status.data?.active && status.data.playlist_url) return status.data.playlist_url
        if (++attempts < 10) {
          await new Promise((r) => setTimeout(r, 1000))
          return poll()
        }
        return null
      }

      const url = await poll()
      if (url) {
        setStreamUrl(url)
        setIsStreaming(true)
        initHls(url)
      } else {
        setError('Stream did not start within timeout')
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setIsLoading(false)
    }
  }, [cameraId, apiBaseUrl, initHls])

  const stopStream = useCallback(async () => {
    try {
      await fetch(`${apiBaseUrl}/api/v1/cameras/${cameraId}/stream/stop`, {
        method: 'POST',
        headers: getAuthHeader(),
      })
    } catch {}
    if (hlsRef.current) {
      hlsRef.current.destroy()
      hlsRef.current = null
    }
    if (videoRef.current) videoRef.current.src = ''
    setIsStreaming(false)
    setStreamUrl(null)
    setDetections([])
  }, [cameraId, apiBaseUrl, videoRef])

  useEffect(() => {
    if (autoStart) startStream()
    return () => {
      if (hlsRef.current) hlsRef.current.destroy()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart])

  return { isStreaming, isLoading, error, detections, streamUrl, startStream, stopStream }
}
