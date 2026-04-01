import { useState, useEffect, useCallback } from 'react'

export function useCameraList() {
  const [cameras, setCameras] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchCameras = useCallback(async () => {
    try {
      const token = localStorage.getItem('token') || sessionStorage.getItem('token')
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
      const res = await fetch('/api/cameras', { headers })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setCameras(Array.isArray(data) ? data : data.cameras || [])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let timeoutId
    let failCount = 0
    let cancelled = false

    const poll = async () => {
      if (cancelled) return
      try {
        await fetchCameras()
        failCount = 0
        if (!cancelled) timeoutId = setTimeout(poll, 10000)
      } catch {
        failCount++
        const backoff = Math.min(10000 * Math.pow(2, failCount - 1), 60000)
        if (!cancelled) timeoutId = setTimeout(poll, backoff)
      }
    }

    poll()
    return () => { cancelled = true; clearTimeout(timeoutId) }
  }, [fetchCameras])

  return { cameras, loading, error, refresh: fetchCameras }
}
