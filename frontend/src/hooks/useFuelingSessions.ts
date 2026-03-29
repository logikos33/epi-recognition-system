// frontend/src/hooks/useFuelingSessions.ts
'use client'

import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { FuelingSession, CountedProduct } from '@/types/monitoring'

interface SessionFilters {
  bayId?: number
  status?: 'active' | 'completed'
  limit?: number
}

interface CreateSessionData {
  bayId: number
  cameraId: number
  licensePlate?: string
}

interface UpdateSessionData {
  licensePlate?: string
  truckExitTime?: string
  finalWeight?: number
  status?: 'active' | 'completed'
}

interface AddProductData {
  productType: string
  quantity: number
  confidence?: number
  confirmedByUser?: boolean
}

interface UseFuelingSessionsOptions {
  autoRefresh?: boolean
  refreshInterval?: number // milliseconds
  filters?: SessionFilters
}

/**
 * Hook for managing fueling sessions with React Query
 * Provides caching, auto-refresh, and optimistic updates
 */
export function useFuelingSessions(options: UseFuelingSessionsOptions = {}) {
  const {
    autoRefresh = false,
    refreshInterval = 10000, // 10 seconds default
    filters = {}
  } = options

  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  /**
   * Query key factory for fueling sessions
   */
  const getQueryKeys = {
    all: ['sessions'] as const,
    filtered: (filters: SessionFilters) => ['sessions', filters] as const,
    byId: (id: string) => ['session', id] as const,
    products: (id: string) => ['session', id, 'products'] as const,
  }

  /**
   * Fetch sessions with filters
   */
  const {
    data: sessions = [],
    isLoading: loadingSessions,
    refetch: refetchSessions
  } = useQuery({
    queryKey: getQueryKeys.filtered(filters),
    queryFn: async () => {
      try {
        const result = await api.listSessions(filters)
        if (result.success) {
          setError(null)
          return result.sessions
        }
        setError('Failed to fetch sessions')
        return []
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error'
        setError(errorMessage)
        return []
      }
    },
    refetchInterval: autoRefresh ? refreshInterval : false,
    staleTime: 5000, // Consider data stale after 5 seconds
  })

  /**
   * Active sessions (filtered from sessions list)
   */
  const activeSessions = sessions.filter(s => s.status === 'active')

  /**
   * Create session mutation
   */
  const createSessionMutation = useMutation({
    mutationFn: async (data: CreateSessionData): Promise<FuelingSession> => {
      try {
        const result = await api.createSession({
          bay_id: data.bayId,
          camera_id: data.cameraId,
          license_plate: data.licensePlate
        })

        if (!result.success) {
          throw new Error('Failed to create session')
        }

        setError(null)
        return result.session
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error'
        setError(errorMessage)
        throw err
      }
    },
    onSuccess: (newSession) => {
      // Invalidate and refetch sessions list
      queryClient.invalidateQueries({ queryKey: getQueryKeys.all })
      // Add new session to cache
      queryClient.setQueryData(
        getQueryKeys.byId(newSession.id),
        newSession
      )
    }
  })

  /**
   * Get single session
   */
  const getSession = useCallback(async (sessionId: string): Promise<FuelingSession | null> => {
    try {
      const result = await api.getSession(sessionId)

      if (result.success) {
        setError(null)
        // Cache the session data
        queryClient.setQueryData(
          getQueryKeys.byId(sessionId),
          result.session
        )
        return result.session
      }

      setError('Session not found')
      return null
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      return null
    }
  }, [queryClient, getQueryKeys])

  /**
   * Update session mutation
   */
  const updateSessionMutation = useMutation({
    mutationFn: async ({ sessionId, data }: { sessionId: string; data: UpdateSessionData }): Promise<FuelingSession> => {
      try {
        const result = await api.updateSession(sessionId, data)

        if (!result.success) {
          throw new Error('Failed to update session')
        }

        setError(null)
        return result.session
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error'
        setError(errorMessage)
        throw err
      }
    },
    onSuccess: (updatedSession, { sessionId }) => {
      // Update cache for this session
      queryClient.setQueryData(
        getQueryKeys.byId(sessionId),
        updatedSession
      )
      // Invalidate sessions list
      queryClient.invalidateQueries({ queryKey: getQueryKeys.all })
    }
  })

  /**
   * Complete session mutation
   */
  const completeSessionMutation = useMutation({
    mutationFn: async ({ sessionId, truckExitTime }: { sessionId: string; truckExitTime?: string }): Promise<FuelingSession> => {
      try {
        const result = await api.completeSession(sessionId, truckExitTime)

        if (!result.success) {
          throw new Error('Failed to complete session')
        }

        setError(null)
        return result.session
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error'
        setError(errorMessage)
        throw err
      }
    },
    onSuccess: (completedSession) => {
      // Update cache for this session
      queryClient.setQueryData(
        getQueryKeys.byId(completedSession.id),
        completedSession
      )
      // Invalidate sessions list (will move from active to completed)
      queryClient.invalidateQueries({ queryKey: getQueryKeys.all })
    }
  })

  /**
   * Add counted product mutation
   */
  const addProductMutation = useMutation({
    mutationFn: async ({ sessionId, data }: { sessionId: string; data: AddProductData }): Promise<CountedProduct> => {
      try {
        const result = await api.addCountedProduct(sessionId, {
          product_type: data.productType,
          quantity: data.quantity,
          confidence: data.confidence,
          confirmed_by_user: data.confirmedByUser
        })

        if (!result.success) {
          throw new Error('Failed to add product')
        }

        setError(null)
        return result.product
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error'
        setError(errorMessage)
        throw err
      }
    },
    onSuccess: (newProduct, { sessionId }) => {
      // Invalidate products list for this session
      queryClient.invalidateQueries({ queryKey: getQueryKeys.products(sessionId) })
      // Invalidate sessions list (products_counted may have changed)
      queryClient.invalidateQueries({ queryKey: getQueryKeys.all })
    }
  })

  /**
   * Get session products
   */
  const getSessionProducts = useCallback(async (sessionId: string): Promise<CountedProduct[]> => {
    try {
      const result = await api.getSessionProducts(sessionId)

      if (result.success) {
        setError(null)
        return result.products
      }

      setError('Failed to fetch products')
      return []
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      return []
    }
  }, [])

  /**
   * List sessions with custom filters (overrides default filters)
   */
  const listSessions = useCallback(async (customFilters?: SessionFilters): Promise<void> => {
    try {
      const result = await api.listSessions(customFilters || filters)

      if (result.success) {
        setError(null)
        // Update cache with new filters
        queryClient.setQueryData(
          getQueryKeys.filtered(customFilters || filters),
          result.sessions
        )
      } else {
        setError('Failed to fetch sessions')
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
    }
  }, [filters, queryClient, getQueryKeys])

  /**
   * Wrapper functions to match the required interface
   */
  const createSession = async (data: CreateSessionData): Promise<FuelingSession> => {
    return createSessionMutation.mutateAsync(data)
  }

  const updateSession = async (sessionId: string, data: UpdateSessionData): Promise<FuelingSession> => {
    return updateSessionMutation.mutateAsync({ sessionId, data })
  }

  const completeSession = async (sessionId: string, truckExitTime?: string): Promise<FuelingSession> => {
    return completeSessionMutation.mutateAsync({ sessionId, truckExitTime })
  }

  const addCountedProduct = async (sessionId: string, data: AddProductData): Promise<CountedProduct> => {
    return addProductMutation.mutateAsync({ sessionId, data })
  }

  /**
   * Refetch all session queries
   */
  const refetch = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: getQueryKeys.all })
  }, [queryClient, getQueryKeys])

  return {
    sessions,
    activeSessions,
    loading: loadingSessions,
    error,
    listSessions,
    createSession,
    getSession,
    updateSession,
    completeSession,
    addCountedProduct,
    getSessionProducts,
    refetch,

    // Mutation loading states
    isCreating: createSessionMutation.isPending,
    isUpdating: updateSessionMutation.isPending,
    isCompleting: completeSessionMutation.isPending,
    isAddingProduct: addProductMutation.isPending
  }
}
