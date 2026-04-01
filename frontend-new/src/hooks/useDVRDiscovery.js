import { useState, useCallback } from 'react'

export function useDVRDiscovery(dvrId) {
  const [channels, setChannels] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const discover = useCallback(async (id) => {
    const targetId = id || dvrId
    if (!targetId) return
    setLoading(true)
    setError(null)
    try {
      const token = localStorage.getItem('token') || sessionStorage.getItem('token')
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
      const res = await fetch(`/api/cameras/dvrs/${targetId}/channels`, { headers })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
      setChannels(data.channels || [])
      return data.channels
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [dvrId])

  return { channels, loading, error, discover }
}
