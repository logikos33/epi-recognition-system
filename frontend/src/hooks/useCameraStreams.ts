// frontend/src/hooks/useCameraStreams.ts
'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '@/lib/api'
import type { Camera, SessionInfo } from '@/types/monitoring'

interface UseCameraStreamsOptions {
  autoRefresh?: boolean;
  refreshInterval?: number; // milliseconds
}

interface CameraStreamState {
  cameras: Camera[];
  selectedCameraIds: number[];
  primaryCameras: number[]; // IDs of 3 expanded cameras
  thumbnailCameras: number[]; // IDs of 9 thumbnail cameras
  loading: boolean;
  error: string | null;
}

/**
 * Hook for managing camera streams and selection
 */
export function useCameraStreams(options: UseCameraStreamsOptions = {}) {
  const {
    autoRefresh = false,
    refreshInterval = 30000 // 30 seconds
  } = options

  const [state, setState] = useState<CameraStreamState>({
    cameras: [],
    selectedCameraIds: [],
    primaryCameras: [],
    thumbnailCameras: [],
    loading: true,
    error: null
  })

  const refreshRef = useRef<NodeJS.Timeout | null>(null)

  /**
   * Fetch all cameras from API
   */
  const fetchCameras = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }))

    try {
      const result = await api.listCameras()

      if (result.success) {
        const activeCameras = result.cameras.filter((c: Camera) => c.is_active)

        setState(prev => ({
          ...prev,
          cameras: activeCameras,
          loading: false
        }))
      } else {
        setState(prev => ({
          ...prev,
          loading: false,
          error: 'Failed to fetch cameras'
        }))
      }
    } catch (err) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Unknown error'
      }))
    }
  }, [])

  /**
   * Set selected cameras (from 1 to 12 max)
   */
  const setSelectedCameras = useCallback((cameraIds: number[]) => {
    const max = Math.min(cameraIds.length, 12)
    const selected = cameraIds.slice(0, max)

    setState(prev => ({
      ...prev,
      selectedCameraIds: selected,
      primaryCameras: selected.slice(0, 3), // First 3 are primary
      thumbnailCameras: selected.slice(3, 12) // Next 9 are thumbnails
    }))
  }, [])

  /**
   * Add camera to selection
   */
  const addCamera = useCallback((cameraId: number) => {
    setState(prev => {
      if (prev.selectedCameraIds.includes(cameraId)) {
        return prev // Already selected
      }

      if (prev.selectedCameraIds.length >= 12) {
        return prev // Max 12 cameras
      }

      const newSelected = [...prev.selectedCameraIds, cameraId]
      return {
        ...prev,
        selectedCameraIds: newSelected,
        primaryCameras: newSelected.slice(0, 3),
        thumbnailCameras: newSelected.slice(3, 12)
      }
    })
  }, [])

  /**
   * Remove camera from selection
   */
  const removeCamera = useCallback((cameraId: number) => {
    setState(prev => {
      const newSelected = prev.selectedCameraIds.filter(id => id !== cameraId)
      return {
        ...prev,
        selectedCameraIds: newSelected,
        primaryCameras: newSelected.slice(0, 3),
        thumbnailCameras: newSelected.slice(3, 12)
      }
    })
  }, [])

  /**
   * Promote thumbnail to primary (swap with last primary)
   */
  const promoteToPrimary = useCallback((cameraId: number) => {
    setState(prev => {
      if (!prev.thumbnailCameras.includes(cameraId)) {
        return prev // Not a thumbnail
      }

      // Remove from thumbnails, add to primaries (keep max 3)
      const newThumbnails = prev.thumbnailCameras.filter(id => id !== cameraId)
      const newPrimaries = [...prev.primaryCameras.slice(0, 2), cameraId] // Keep first 2, add new one

      return {
        ...prev,
        primaryCameras: newPrimaries,
        thumbnailCameras: newThumbnails
      }
    })
  }, [])

  /**
   * Demote primary to thumbnail (swap with first thumbnail)
   */
  const demoteToThumbnail = useCallback((cameraId: number) => {
    setState(prev => {
      if (!prev.primaryCameras.includes(cameraId)) {
        return prev // Not a primary
      }

      // Remove from primaries, add to thumbnails
      const newPrimaries = prev.primaryCameras.filter(id => id !== cameraId)
      const newThumbnails = [cameraId, ...prev.thumbnailCameras.slice(0, 8)]

      return {
        ...prev,
        primaryCameras: newPrimaries,
        thumbnailCameras: newThumbnails
      }
    })
  }, [])

  /**
   * Initialize hook
   */
  useEffect(() => {
    fetchCameras()

    // Auto-refresh if enabled
    if (autoRefresh) {
      refreshRef.current = setInterval(() => {
        fetchCameras()
      }, refreshInterval)
    }

    return () => {
      if (refreshRef.current) {
        clearInterval(refreshRef.current)
      }
    }
  }, [fetchCameras, autoRefresh, refreshInterval])

  return {
    cameras: state.cameras,
    selectedCameraIds: state.selectedCameraIds,
    primaryCameras: state.primaryCameras,
    thumbnailCameras: state.thumbnailCameras,
    loading: state.loading,
    error: state.error,
    fetchCameras,
    setSelectedCameras,
    addCamera,
    removeCamera,
    promoteToPrimary,
    demoteToThumbnail
  }
}