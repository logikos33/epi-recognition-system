// frontend/src/hooks/useVirtualizedStreams.ts
'use client'

import { useState, useEffect, useCallback, useRef } from 'react'

interface VirtualizedStreamsOptions {
  maxActiveStreams?: number
}

interface StreamState {
  cameraId: number
  isActive: boolean
  isVisible: boolean
  lastActive: number
}

interface UseVirtualizedStreamsResult {
  activeStreams: Set<number>
  visibleCameras: Set<number>
  activateStream: (cameraId: number) => void
  deactivateStream: (cameraId: number) => void
  isStreamActive: (cameraId: number) => boolean
  registerCamera: (cameraId: number, element: HTMLElement) => () => void
}

const MAX_ACTIVE_STREAMS = 9 // Grade 3x3
const STREAM_CLEANUP_INTERVAL = 10 * 60 * 1000 // 10 minutes
const STREAM_MAX_AGE = 10 * 60 * 1000 // 10 minutes

/**
 * Hook to manage virtualized camera streams
 * Only loads streams for visible cameras (IntersectionObserver)
 * Limits active streams to prevent browser freeze
 * Automatically recycles streams every 10 minutes to prevent memory leaks
 */
export function useVirtualizedStreams(options: VirtualizedStreamsOptions = {}): UseVirtualizedStreamsResult {
  const { maxActiveStreams = MAX_ACTIVE_STREAMS } = options

  const [activeStreams, setActiveStreams] = useState<Set<number>>(new Set())
  const [visibleCameras, setVisibleCameras] = useState<Set<number>>(new Set())
  const observersRef = useRef<Map<number, IntersectionObserver>>(new Map())
  const streamStatesRef = useRef<Map<number, StreamState>>(new Map())

  /**
   * Activate a camera stream (if under limit)
   */
  const activateStream = useCallback((cameraId: number) => {
    setActiveStreams(prev => {
      // If already active, just update timestamp
      if (prev.has(cameraId)) {
        return prev
      }

      // Check if we can add more streams
      if (prev.size >= maxActiveStreams) {
        // Try to deactivate a non-visible stream first
        const nonVisibleActive = Array.from(prev).find(id => !visibleCameras.has(id))
        if (nonVisibleActive !== undefined) {
          const newSet = new Set(prev)
          newSet.delete(nonVisibleActive)
          newSet.add(cameraId)

          // Update state
          const state = streamStatesRef.current.get(nonVisibleActive)
          if (state) {
            streamStatesRef.current.set(nonVisibleActive, {
              ...state,
              isActive: false,
              lastActive: Date.now()
            })
          }

          return newSet
        }

        // Can't activate - limit reached
        return prev
      }

      // Add to active set
      const newSet = new Set(prev)
      newSet.add(cameraId)

      // Update state
      streamStatesRef.current.set(cameraId, {
        cameraId,
        isActive: true,
        isVisible: visibleCameras.has(cameraId),
        lastActive: Date.now()
      })

      return newSet
    })
  }, [maxActiveStreams, visibleCameras])

  /**
   * Deactivate a camera stream
   */
  const deactivateStream = useCallback((cameraId: number) => {
    setActiveStreams(prev => {
      if (!prev.has(cameraId)) {
        return prev
      }

      const newSet = new Set(prev)
      newSet.delete(cameraId)

      // Update state
      const state = streamStatesRef.current.get(cameraId)
      if (state) {
        streamStatesRef.current.set(cameraId, {
          ...state,
          isActive: false,
          lastActive: Date.now()
        })
      }

      return newSet
    })
  }, [])

  /**
   * Check if a stream is currently active
   */
  const isStreamActive = useCallback((cameraId: number): boolean => {
    return activeStreams.has(cameraId)
  }, [activeStreams])

  /**
   * Register a camera element for visibility tracking
   * Returns cleanup function
   */
  const registerCamera = useCallback((cameraId: number, element: HTMLElement) => (() => {
    // Create IntersectionObserver for this camera
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          const isVisible = entry.isIntersecting && entry.intersectionRatio > 0.1

          if (isVisible) {
            // Camera became visible
            setVisibleCameras(prev => {
              const newSet = new Set(prev)
              newSet.add(cameraId)
              return newSet
            })

            // Activate stream if not already active
            activateStream(cameraId)
          } else {
            // Camera went off screen
            setVisibleCameras(prev => {
              const newSet = new Set(prev)
              newSet.delete(cameraId)
              return newSet
            })

            // Update state visibility
            const state = streamStatesRef.current.get(cameraId)
            if (state) {
              streamStatesRef.current.set(cameraId, {
                ...state,
                isVisible: false
              })
            }

            // Deactivate stream to save resources
            deactivateStream(cameraId)
          }
        })
      },
      {
        threshold: 0.1, // Trigger when 10% visible
        rootMargin: '0px'
      }
    )

    // Store observer
    observersRef.current.set(cameraId, observer)
    observer.observe(element)

    // Initial check
    activateStream(cameraId)

    // Cleanup function
    return () => {
      observer.disconnect()
      observersRef.current.delete(cameraId)
      streamStatesRef.current.delete(cameraId)
      deactivateStream(cameraId)
      setVisibleCameras(prev => {
        const newSet = new Set(prev)
        newSet.delete(cameraId)
        return newSet
      })
    }
  }), [activateStream, deactivateStream])

  /**
   * Memory Cleanup: Recycle streams that have been active for too long
   * Prevents memory leaks from long-running video streams
   */
  useEffect(() => {
    const cleanupInterval = setInterval(() => {
      const now = Date.now()
      const streamsToRecycle: number[] = []

      // Find streams that have been active for more than STREAM_MAX_AGE
      streamStatesRef.current.forEach((state, cameraId) => {
        if (state.isActive && (now - state.lastActive) > STREAM_MAX_AGE) {
          streamsToRecycle.push(cameraId)
        }
      })

      // Recycle old streams (silent reset - deactivate then reactivate)
      if (streamsToRecycle.length > 0) {
        console.log(`[Stream Cleanup] Recycling ${streamsToRecycle.length} old streams`)

        streamsToRecycle.forEach(cameraId => {
          const state = streamStatesRef.current.get(cameraId)
          if (state && state.isVisible) {
            // Only recycle if still visible (silent reset)
            deactivateStream(cameraId)

            // Small delay before reactivating to allow cleanup
            setTimeout(() => {
              activateStream(cameraId)
            }, 100)
          }
        })
      }
    }, STREAM_CLEANUP_INTERVAL)

    return () => clearInterval(cleanupInterval)
  }, [activateStream, deactivateStream])

  return {
    activeStreams,
    visibleCameras,
    activateStream,
    deactivateStream,
    isStreamActive,
    registerCamera
  }
}
