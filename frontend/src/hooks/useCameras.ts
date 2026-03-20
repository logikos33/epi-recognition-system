'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import type { Camera } from '@/types/camera'

export function useCameras() {
  const [cameras, setCameras] = useState<Camera[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchCameras = async () => {
      setLoading(true)
      setError(null)

      const { data, error } = await supabase
        .from('cameras')
        .select('*')
        .order('created_at', { ascending: false })

      if (error) {
        setError(error.message)
        setLoading(false)
        return
      }

      setCameras(data || [])
      setLoading(false)
    }

    fetchCameras()
  }, [])

  const createCamera = async (camera: Partial<Camera>) => {
    const { data, error } = await supabase
      .from('cameras')
      .insert(camera)
      .select()
      .single()

    if (error) {
      return { camera: null, error }
    }

    setCameras((prev) => [data, ...prev])
    return { camera: data, error: null }
  }

  const updateCamera = async (id: number, updates: Partial<Camera>) => {
    const { data, error } = await supabase
      .from('cameras')
      .update(updates)
      .eq('id', id)
      .select()
      .single()

    if (error) {
      return { camera: null, error }
    }

    setCameras((prev) => prev.map((c) => (c.id === id ? data : c)))
    return { camera: data, error: null }
  }

  const deleteCamera = async (id: number) => {
    const { error } = await supabase
      .from('cameras')
      .delete()
      .eq('id', id)

    if (error) {
      return { error }
    }

    setCameras((prev) => prev.filter((c) => c.id !== id))
    return { error: null }
  }

  return {
    cameras,
    loading,
    error,
    createCamera,
    updateCamera,
    deleteCamera,
  }
}
