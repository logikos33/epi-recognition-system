// frontend/src/hooks/useYOLOWorkerPriority.ts
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
  priority?: 'high' | 'medium' | 'low'
}

interface UseYOLOWorkerPriorityResult {
  data: Map<number, YOLOCameraData>
  loading: boolean
  error: string | null
  isReady: boolean
  priorityStats: {
    high: number
    medium: number
    low: number
  }
}

interface WorkerMessage {
  type: 'poll'
  priority: 'high' | 'medium' | 'low'
  data: Map<number, YOLOCameraData>
  timestamp: number
}

interface PriorityPollingRequest {
  type: 'poll'
  priority: 'high' | 'medium' | 'low'
  cameraIds: number[]
  apiBase: string
  token: string | null
  interval: number
}

/**
 * Priority Queue Intervals
 */
const PRIORITY_INTERVALS = {
  high: 3000,    // 3 seconds - visible cameras
  medium: 10000, // 10 seconds - off-screen active cameras
  low: 30000     // 30 seconds - hidden/offline cameras
}

/**
 * Hook to manage YOLO polling via Web Worker with Priority Queues
 * Runs in separate thread - doesn't block UI
 * Distributes polling based on camera visibility and priority
 */
export function useYOLOWorkerPriority(
  allCameraIds: number[],
  visibleCameras: Set<number>,
  activeStreams: Set<number>
): UseYOLOWorkerPriorityResult {
  const [data, setData] = useState<Map<number, YOLOCameraData>>(new Map())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isReady, setIsReady] = useState(false)
  const [priorityStats, setPriorityStats] = useState({
    high: 0,
    medium: 0,
    low: 0
  })

  const workerRef = useRef<Worker | null>(null)
  const intervalsRef = useRef<Map<string, NodeJS.Timeout>>(new Map())
  const lastPollRef = useRef<Map<string, number>>(new Map())

  // Calculate priority for each camera
  const calculatePriorities = useCallback(() => {
    const high: number[] = []
    const medium: number[] = []
    const low: number[] = []

    allCameraIds.forEach(cameraId => {
      if (visibleCameras.has(cameraId)) {
        // Visible cameras = high priority
        high.push(cameraId)
      } else if (activeStreams.has(cameraId)) {
        // Off-screen but active = medium priority
        medium.push(cameraId)
      } else {
        // Hidden/offline = low priority
        low.push(cameraId)
      }
    })

    return { high, medium, low }
  }, [allCameraIds, visibleCameras, activeStreams])

  // Poll function for specific priority
  const pollPriority = useCallback((priority: 'high' | 'medium' | 'low', cameraIds: number[]) => {
    if (!workerRef.current || cameraIds.length === 0) {
      return
    }

    const token = api.getToken()
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

    const message: PriorityPollingRequest = {
      type: 'poll',
      priority,
      cameraIds,
      apiBase,
      token,
      interval: PRIORITY_INTERVALS[priority]
    }

    workerRef.current.postMessage(message)
    lastPollRef.current.set(priority, Date.now())
  }, [])

  // Initialize worker and polling intervals
  useEffect(() => {
    if (typeof window === 'undefined' || allCameraIds.length === 0) {
      return
    }

    try {
      // Create worker
      const workerUrl = '/yolo-worker-priority.js'
      const worker = new Worker(workerUrl)
      workerRef.current = worker

      // Handle messages from worker
      worker.onmessage = (event: MessageEvent<WorkerMessage>) => {
        const { type, priority, data: workerData, timestamp } = event.data

        if (type === 'poll') {
          // Update data with priority info
          setData(prevData => {
            const updatedData = new Map(prevData)

            workerData.forEach((yoloData: YOLOCameraData) => {
              // Recalculate elapsed time
              const now = new Date()
              const entry = new Date(yoloData.truck_entry_time)
              const elapsedMs = now.getTime() - entry.getTime()
              const elapsedSeconds = Math.floor(elapsedMs / 1000)

              const hours = Math.floor(elapsedSeconds / 3600)
              const minutes = Math.floor((elapsedSeconds % 3600) / 60)
              const seconds = elapsedSeconds % 60

              const formatted = hours > 0
                ? `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
                : `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`

              updatedData.set(yoloData.camera_id, {
                ...yoloData,
                elapsed_time_formatted: formatted,
                elapsed_seconds: elapsedSeconds,
                priority
              })
            })

            return updatedData
          })

          setLoading(false)
          setIsReady(true)
        }
      }

      worker.onerror = (error: ErrorEvent) => {
        console.error('[YOLO Worker Priority] Error:', error)
        setError('Worker error')
        setIsReady(false)
      }

      // Start polling intervals for each priority
      const startPolling = () => {
        const { high, medium, low } = calculatePriorities()

        // Update priority stats
        setPriorityStats({ high: high.length, medium: medium.length, low: low.length })

        // Clear existing intervals
        intervalsRef.current.forEach(interval => clearInterval(interval))
        intervalsRef.current.clear()

        // High priority - poll every 3 seconds
        if (high.length > 0) {
          const interval = setInterval(() => {
            const { high: currentHigh } = calculatePriorities()
            pollPriority('high', currentHigh)
          }, PRIORITY_INTERVALS.high)

          intervalsRef.current.set('high', interval)
          // Initial poll
          pollPriority('high', high)
        }

        // Medium priority - poll every 10 seconds
        if (medium.length > 0) {
          const interval = setInterval(() => {
            const { medium: currentMedium } = calculatePriorities()
            pollPriority('medium', currentMedium)
          }, PRIORITY_INTERVALS.medium)

          intervalsRef.current.set('medium', interval)
          // Initial poll (staggered by 3 seconds)
          setTimeout(() => pollPriority('medium', medium), 3000)
        }

        // Low priority - poll every 30 seconds
        if (low.length > 0) {
          const interval = setInterval(() => {
            const { low: currentLow } = calculatePriorities()
            pollPriority('low', currentLow)
          }, PRIORITY_INTERVALS.low)

          intervalsRef.current.set('low', interval)
          // Initial poll (staggered by 6 seconds)
          setTimeout(() => pollPriority('low', low), 6000)
        }
      }

      // Initial start
      startPolling()

      // Recalculate priorities every 5 seconds
      const priorityRecalcInterval = setInterval(() => {
        startPolling()
      }, 5000)

      // Cleanup on unmount
      return () => {
        clearInterval(priorityRecalcInterval)
        intervalsRef.current.forEach(interval => clearInterval(interval))
        intervalsRef.current.clear()

        if (workerRef.current) {
          workerRef.current.postMessage({ type: 'cleanup' })
          workerRef.current.terminate()
          workerRef.current = null
        }
      }

    } catch (err: any) {
      console.error('[YOLO Worker Priority] Failed to initialize:', err)
      setError('Failed to initialize worker')
      setIsReady(false)
    }
  }, [allCameraIds, calculatePriorities, pollPriority])

  return {
    data,
    loading,
    error,
    isReady,
    priorityStats
  }
}
