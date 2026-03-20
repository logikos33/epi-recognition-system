import { useEffect, useState } from 'react'
import { RealtimeChannel } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import type { Detection } from '@/types/detection'

export function useRealtimeDetections(cameraId?: number) {
  const [detections, setDetections] = useState<Detection[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let channel: RealtimeChannel

    const setupSubscription = async () => {
      setLoading(true)

      // Load initial data
      let query = supabase
        .from('detections')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(50)

      if (cameraId) {
        query = query.eq('camera_id', cameraId)
      }

      const { data } = await query
      if (data) {
        setDetections(data)
      }
      setLoading(false)

      // Subscribe to new detections
      channel = supabase
        .channel('detections-channel')
        .on(
          'postgres_changes',
          {
            event: 'INSERT',
            schema: 'public',
            table: 'detections',
            filter: cameraId ? `camera_id=eq.${cameraId}` : undefined,
          },
          (payload) => {
            setDetections((prev) => [payload.new as Detection, ...prev].slice(0, 50))
          }
        )
        .subscribe()
    }

    setupSubscription()

    return () => {
      channel?.unsubscribe()
    }
  }, [cameraId])

  return { detections, loading }
}
