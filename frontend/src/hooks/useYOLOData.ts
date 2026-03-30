// frontend/src/hooks/useYOLOData.ts
'use client'

import { useState, useEffect, useMemo } from 'react'
import { api } from '@/lib/api'

interface YOLOData {
  session_id: string
  license_plate: string | null
  truck_entry_time: string
  products_counted: Record<string, number> | null
  item_count: number
  elapsed_time_formatted: string
  elapsed_seconds: number
  status: 'active' | 'completed' | 'paused'
}

interface UseYOLODataResult {
  data: Map<number, YOLOData>
  loading: boolean
  error: string | null
  refresh: () => void
}

/**
 * Hook to fetch YOLO detection data for cameras
 * Updates every 3 seconds
 * Updates elapsed time every second
 */
export function useYOLOData(cameraIds: number[], enabled: boolean = true): UseYOLODataResult {
  const [rawData, setRawData] = useState<Map<number, YOLOData>>(new Map())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [timeUpdater, setTimeUpdater] = useState(0)

  const calculateElapsedTime = (entryTime: string): { formatted: string; seconds: number } => {
    const now = new Date()
    const entry = new Date(entryTime)
    const elapsedMs = now.getTime() - entry.getTime()
    const elapsedSeconds = Math.floor(elapsedMs / 1000)

    const hours = Math.floor(elapsedSeconds / 3600)
    const minutes = Math.floor((elapsedSeconds % 3600) / 60)
    const seconds = elapsedSeconds % 60

    if (hours > 0) {
      return {
        formatted: `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`,
        seconds: elapsedSeconds
      }
    }

    return {
      formatted: `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`,
      seconds: elapsedSeconds
    }
  }

  const fetchData = async () => {
    if (!enabled || cameraIds.length === 0) {
      setRawData(new Map())
      return
    }

    setLoading(true)
    setError(null)

    try {
      const resultMap = new Map<number, YOLOData>()

      // Fetch active sessions for each camera
      for (const cameraId of cameraIds) {
        try {
          const response = await api.get(`/api/sessions?camera_id=${cameraId}&status=active&limit=1`)

          if (response.success && response.sessions && response.sessions.length > 0) {
            const session = response.sessions[0]

            // Calculate item count from products_counted
            const productsCounted = session.products_counted || {}
            const itemCount = Object.values(productsCounted).reduce((sum: number, count: any) => sum + (count || 0), 0)

            // Calculate elapsed time
            const elapsedInfo = calculateElapsedTime(session.truck_entry_time)

            resultMap.set(cameraId, {
              session_id: session.id,
              license_plate: session.license_plate,
              truck_entry_time: session.truck_entry_time,
              products_counted: productsCounted,
              item_count: itemCount,
              elapsed_time_formatted: elapsedInfo.formatted,
              elapsed_seconds: elapsedInfo.seconds,
              status: session.status
            })
          }
        } catch (err) {
          console.error(`Error fetching YOLO data for camera ${cameraId}:`, err)
        }
      }

      setRawData(resultMap)
    } catch (err: any) {
      console.error('Error fetching YOLO data:', err)
      setError(err?.message || 'Failed to fetch YOLO data')
    } finally {
      setLoading(false)
    }
  }

  // Update elapsed times every second
  useEffect(() => {
    if (!enabled) return

    const interval = setInterval(() => {
      setTimeUpdater(prev => prev + 1)
    }, 1000)

    return () => clearInterval(interval)
  }, [enabled])

  // Recalculate elapsed times based on rawData + timeUpdater
  const data = useMemo(() => {
    const updatedMap = new Map<number, YOLOData>()

    rawData.forEach((yoloData, cameraId) => {
      // Recalculate elapsed time
      const elapsedInfo = calculateElapsedTime(yoloData.truck_entry_time)

      updatedMap.set(cameraId, {
        ...yoloData,
        elapsed_time_formatted: elapsedInfo.formatted,
        elapsed_seconds: elapsedInfo.seconds
      })
    })

    return updatedMap
  }, [rawData, timeUpdater])

  // Initial fetch
  useEffect(() => {
    fetchData()
  }, [cameraIds.join(','), enabled, refreshTrigger])

  // Poll every 3 seconds
  useEffect(() => {
    if (!enabled) return

    const interval = setInterval(() => {
      fetchData()
    }, 3000)

    return () => clearInterval(interval)
  }, [cameraIds.join(','), enabled])

  return {
    data,
    loading,
    error,
    refresh: () => setRefreshTrigger(prev => prev + 1)
  }
}
