/**
 * useSocket — WebSocket connection via Socket.IO
 *
 * Connects to the Flask-SocketIO backend.
 * Workers publish to Redis → SocketIO emits to rooms → this hook receives.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

interface Detection {
  camera_id: string
  timestamp: number
  detections: Array<{
    class: string
    confidence: number
    bbox: { x1: number; y1: number; x2: number; y2: number }
  }>
}

interface UseSocketOptions {
  /** Auto-connect on mount (default: true) */
  autoConnect?: boolean
  /** API base URL (default: empty = same origin) */
  baseUrl?: string
}

interface UseSocketReturn {
  connected: boolean
  joinCamera: (cameraId: string) => void
  leaveCamera: (cameraId: string) => void
  onDetection: (cameraId: string, callback: (d: Detection) => void) => () => void
  connect: () => void
  disconnect: () => void
}

export function useSocket(options: UseSocketOptions = {}): UseSocketReturn {
  const { autoConnect = true, baseUrl = '' } = options
  const socketRef = useRef<any>(null)
  const [connected, setConnected] = useState(false)
  const listenersRef = useRef<Map<string, Set<(d: Detection) => void>>>(new Map())

  const connect = useCallback(() => {
    if (socketRef.current?.connected) return
    try {
      // Dynamic import to avoid build errors if socket.io-client not installed
      import('socket.io-client').then(({ io }) => {
        const socket = io(baseUrl || window.location.origin, {
          transports: ['websocket', 'polling'],
          reconnectionAttempts: 5,
          reconnectionDelay: 2000,
        })

        socket.on('connect', () => {
          console.debug('[useSocket] Connected:', socket.id)
          setConnected(true)
        })

        socket.on('disconnect', () => {
          console.debug('[useSocket] Disconnected')
          setConnected(false)
        })

        socket.on('detection', (data: Detection) => {
          const handlers = listenersRef.current.get(data.camera_id)
          if (handlers) {
            handlers.forEach((cb) => cb(data))
          }
        })

        socketRef.current = socket
      }).catch((err: Error) => {
        console.warn('[useSocket] socket.io-client not available:', err.message)
        setConnected(false)
      })
    } catch (err) {
      console.warn('[useSocket] Connection failed (degraded):', err)
    }
  }, [baseUrl])

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect()
      socketRef.current = null
      setConnected(false)
    }
  }, [])

  const joinCamera = useCallback((cameraId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('join_camera', { camera_id: cameraId })
      console.debug('[useSocket] Joined camera room:', cameraId)
    }
  }, [])

  const leaveCamera = useCallback((cameraId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('leave_camera', { camera_id: cameraId })
    }
  }, [])

  const onDetection = useCallback(
    (cameraId: string, callback: (d: Detection) => void): (() => void) => {
      if (!listenersRef.current.has(cameraId)) {
        listenersRef.current.set(cameraId, new Set())
      }
      listenersRef.current.get(cameraId)!.add(callback)

      return () => {
        listenersRef.current.get(cameraId)?.delete(callback)
      }
    },
    []
  )

  useEffect(() => {
    if (autoConnect) connect()
    return () => disconnect()
  }, [autoConnect, connect, disconnect])

  return { connected, joinCamera, leaveCamera, onDetection, connect, disconnect }
}
