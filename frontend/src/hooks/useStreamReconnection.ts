// frontend/src/hooks/useStreamReconnection.ts
'use client'

import { useState, useEffect, useRef, useCallback } from 'react'

interface ReconnectionState {
  attempts: number
  lastAttempt: number
  nextRetryIn: number
  isRetrying: boolean
  backoffSeconds: number
}

interface UseStreamReconnectionOptions {
  maxAttempts?: number
  initialBackoff?: number // milliseconds
  maxBackoff?: number // milliseconds
  backoffMultiplier?: number
}

interface UseStreamReconnectionResult {
  reconnectingStreams: Set<number>
  failedStreams: Set<number>
  markStreamFailed: (cameraId: number) => void
  markStreamRecovered: (cameraId: number) => void
  getBackoffTime: (cameraId: number) => number
  resetStream: (cameraId: number) => void
}

const DEFAULT_OPTIONS: Required<UseStreamReconnectionOptions> = {
  maxAttempts: 5,
  initialBackoff: 1000, // 1 second
  maxBackoff: 30000, // 30 seconds max
  backoffMultiplier: 2 // exponential: 1s, 2s, 4s, 8s, 16s, max 30s
}

/**
 * Hook to manage stream reconnection with exponential backoff
 * Prevents spam of reconnection attempts when streams fail
 */
export function useStreamReconnection(
  options: UseStreamReconnectionOptions = {}
): UseStreamReconnectionResult {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  const [reconnectingStreams, setReconnectingStreams] = useState<Set<number>>(new Set())
  const [failedStreams, setFailedStreams] = useState<Set<number>>(new Set())

  const reconnectionStatesRef = useRef<Map<number, ReconnectionState>>(new Map())
  const retryTimersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())

  /**
   * Calculate exponential backoff delay
   */
  const calculateBackoff = useCallback((attempt: number): number => {
    const exponentialDelay = opts.initialBackoff * Math.pow(opts.backoffMultiplier, attempt - 1)
    return Math.min(exponentialDelay, opts.maxBackoff)
  }, [opts.initialBackoff, opts.maxBackoff, opts.backoffMultiplier])

  /**
   * Mark a stream as recovered (clear failure state)
   */
  const markStreamRecovered = useCallback((cameraId: number) => {
    reconnectionStatesRef.current.delete(cameraId)

    const existingTimer = retryTimersRef.current.get(cameraId)
    if (existingTimer) {
      clearTimeout(existingTimer)
      retryTimersRef.current.delete(cameraId)
    }

    setReconnectingStreams(prev => {
      const newSet = new Set(prev)
      newSet.delete(cameraId)
      return newSet
    })

    setFailedStreams(prev => {
      const newSet = new Set(prev)
      newSet.delete(cameraId)
      return newSet
    })
  }, [])

  /**
   * Mark a stream as failed and schedule reconnection
   */
  const markStreamFailed = useCallback((cameraId: number) => {
    const existingState = reconnectionStatesRef.current.get(cameraId)

    if (existingState) {
      // Update existing failed state
      const newAttempts = existingState.attempts + 1

      const newState: ReconnectionState = {
        ...existingState,
        attempts: newAttempts,
        lastAttempt: Date.now(),
        nextRetryIn: calculateBackoff(newAttempts),
        isRetrying: newAttempts < opts.maxAttempts,
        backoffSeconds: calculateBackoff(newAttempts) / 1000
      }

      reconnectionStatesRef.current.set(cameraId, newState)

      // Clear existing retry timer if any
      const existingTimer = retryTimersRef.current.get(cameraId)
      if (existingTimer) {
        clearTimeout(existingTimer)
        retryTimersRef.current.delete(cameraId)
      }

      if (newState.isRetrying) {
        // Schedule retry
        setReconnectingStreams(prev => new Set(prev).add(cameraId))

        const timer = setTimeout(() => {
          // Trigger reconnection attempt here
          console.log(`[Stream Reconnection] Retrying camera ${cameraId} (attempt ${newState.attempts})`)

          // Mark as recovered (will be re-marked as failed if still failing)
          markStreamRecovered(cameraId)
        }, newState.nextRetryIn)

        retryTimersRef.current.set(cameraId, timer)
      } else {
        // Max attempts reached - mark as permanently failed
        console.error(`[Stream Reconnection] Camera ${cameraId} failed after ${newState.attempts} attempts`)
        setFailedStreams(prev => new Set(prev).add(cameraId))
        setReconnectingStreams(prev => {
          const newSet = new Set(prev)
          newSet.delete(cameraId)
          return newSet
        })
      }
    } else {
      // First failure
      const backoffMs = calculateBackoff(1)
      const newState: ReconnectionState = {
        attempts: 1,
        lastAttempt: Date.now(),
        nextRetryIn: backoffMs,
        isRetrying: true,
        backoffSeconds: backoffMs / 1000
      }

      reconnectionStatesRef.current.set(cameraId, newState)

      // Schedule first retry
      setReconnectingStreams(prev => new Set(prev).add(cameraId))

      const timer = setTimeout(() => {
        console.log(`[Stream Reconnection] First retry for camera ${cameraId}`)
        markStreamRecovered(cameraId)
      }, backoffMs)

      retryTimersRef.current.set(cameraId, timer)
    }
  }, [calculateBackoff, opts.maxAttempts, markStreamRecovered])

  /**
   * Get backoff time for a specific camera
   */
  const getBackoffTime = useCallback((cameraId: number): number => {
    const state = reconnectionStatesRef.current.get(cameraId)
    return state?.backoffSeconds || 0
  }, [])

  /**
   * Reset stream state (clear all failure/retry state)
   */
  const resetStream = useCallback((cameraId: number) => {
    markStreamRecovered(cameraId)
    setFailedStreams(prev => {
      const newSet = new Set(prev)
      newSet.delete(cameraId)
      return newSet
    })
  }, [markStreamRecovered])

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      // Clear all retry timers
      retryTimersRef.current.forEach(timer => clearTimeout(timer))
      retryTimersRef.current.clear()
    }
  }, [])

  return {
    reconnectingStreams,
    failedStreams,
    markStreamFailed,
    markStreamRecovered,
    getBackoffTime,
    resetStream
  }
}
