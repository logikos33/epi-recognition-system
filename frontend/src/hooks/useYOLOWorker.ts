// frontend/src/hooks/useYOLOWorker.ts
'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '@/lib/api'

interface YOLOCameraData {
  session_id: string
  camera_id: number
  license_plate: string | null
  truck_entry_time: string
  products_counted: Record<string, number> | null
  item_count: number
  elapsed_time_formatted: string
  elapsed_seconds: number
  status: 'active' | 'completed' | 'paused'
}

interface UseYOLOWorkerResult {
  data: Map<number, YOLOCameraData>
  loading: boolean
  error: string | null
  isReady: boolean
}

interface WorkerMessage {
  type: 'poll'
  data: Map<number, YOLOCameraData>
  timestamp: number
}

/**
 * Hook to manage YOLO polling via Web Worker
 * Runs in separate thread - doesn't block UI
 */
export function useYOLOWorker(cameraIds: number[], interval: number = 3000): UseYOLOWorkerResult {
  const [data, setData] = useState<Map<number, YOLOCameraData>>(new Map())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isReady, setIsReady] = useState(false)

  const workerRef = useRef<Worker | null>(null)
  const currentTimeRef = useRef<number>(Date.now())

  // Initialize worker
  useEffect(() => {
    if (typeof window === 'undefined' || cameraIds.length === 0) {
      return
    }

    try {
      // Create worker from TypeScript file
      const workerUrl = '/yolo-worker.js'
      const worker = new Worker(workerUrl)
      workerRef.current = worker

      // Handle messages from worker
      worker.onmessage = (event: MessageEvent<WorkerMessage>) => {
        const { type, data: workerData, timestamp } = event.data

        if (type === 'poll') {
          // Update current time reference for elapsed time calculation
          currentTimeRef.current = Date.now()

          // Recalculate elapsed times based on current time
          const updatedData = new Map<number, YOLOCameraData>()

          workerData.forEach((yoloData: YOLOCameraData) => {
            // Recalculate elapsed time
            const now = new Date()
            const entry = new Date(yoloData.truck_entry_time)
            const elapsedMs = now.getTime() - entry.getTime()
            const elapsedSeconds = Math.floor(elapsedMs / 1000)

            const hours = Math.floor(elapsedSeconds / 3600)
            const minutes = Math.floor((elapsedSeconds % 3600) / 60)
            const seconds = elapsedSeconds % 60

            let formatted: string
            if (hours > 0) {
              formatted = `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
            } else {
              formatted = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
            }

            updatedData.set(yoloData.camera_id, {
              ...yoloData,
              elapsed_time_formatted: formatted,
              elapsed_seconds: elapsedSeconds
            })
          })

          setData(updatedData)
          setLoading(false)
          setIsReady(true)
        }
      }

      worker.onerror = (error: ErrorEvent) => {
        console.error('[YOLO Worker] Error:', error)
        setError('Worker error')
        setIsReady(false)
      }

      // Start polling
      const token = api.getToken()
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

      const message: PollingRequest = {
        type: 'poll',
        cameraIds,
        apiBase,
        token,
        interval
      }

      worker.postMessage(message)

    } catch (err: any) {
      console.error('[YOLO Worker] Failed to initialize:', err)
      setError('Failed to initialize worker')
      setIsReady(false)
    }

    // Cleanup on unmount
    return () => {
      if (workerRef.current) {
        // Send cleanup message to worker
        workerRef.current.postMessage({ type: 'cleanup' })

        // Terminate worker
        workerRef.current.terminate()
        workerRef.current = null
      }
    }
  }, [cameraIds, interval])

  return {
    data,
    loading,
    error,
    isReady
  }
}

interface PollingRequest {
  type: 'poll'
  cameraIds: number[]
  apiBase: string
  token: string | null
  interval: number
}
