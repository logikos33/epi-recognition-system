import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import type { Detection, DetectionWithCamera, DetectionFilters } from '@/types/detection'

export function useDetections(filters?: DetectionFilters) {
  const [detections, setDetections] = useState<DetectionWithCamera[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchDetections = async () => {
      setLoading(true)
      setError(null)

      let query = supabase
        .from('detections')
        .select(`
          *,
          camera (
            id,
            name,
            location
          )
        `)
        .order('timestamp', { ascending: false })
        .limit(50)

      // Apply filters
      if (filters?.camera_id) {
        query = query.eq('camera_id', filters.camera_id)
      }

      if (filters?.is_compliant !== undefined) {
        query = query.eq('is_compliant', filters.is_compliant)
      }

      const { data, error } = await query

      if (error) {
        setError(error.message)
        setLoading(false)
        return
      }

      setDetections(data || [])
      setLoading(false)
    }

    fetchDetections()
  }, [filters])

  return { detections, loading, error }
}
