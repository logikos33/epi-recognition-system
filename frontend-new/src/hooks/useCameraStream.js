import { useState, useEffect, useCallback } from 'react'

export function useCameraStream(cameraId) {
  const [streamUrl, setStreamUrl] = useState(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)

  const getHeaders = () => {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token')
    return token ? { 'Authorization': `Bearer ${token}` } : {}
  }

  const startStream = useCallback(async () => {
    try {
      const res = await fetch(`/api/cameras/${cameraId}/stream/start`, {
        method: 'POST', headers: getHeaders()
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
      setStreamUrl(data.stream_url || data.hls_url)
      setIsStreaming(true)
      setError(null)
      return data.stream_url || data.hls_url
    } catch (err) {
      setError(err.message)
      throw err
    }
  }, [cameraId])

  const stopStream = useCallback(async () => {
    try {
      await fetch(`/api/cameras/${cameraId}/stream/stop`, {
        method: 'POST', headers: getHeaders()
      })
      setStreamUrl(null)
      setIsStreaming(false)
    } catch (err) {
      setError(err.message)
    }
  }, [cameraId])

  // Polling do status com backoff
  useEffect(() => {
    if (!cameraId) return
    let timeoutId
    let failCount = 0
    let cancelled = false

    const poll = async () => {
      if (cancelled) return
      try {
        const res = await fetch(`/api/cameras/${cameraId}/stream/status`, {
          headers: getHeaders()
        })
        const data = await res.json()
        setStatus(data)
        setIsStreaming(data.active || false)
        failCount = 0
        if (!cancelled) timeoutId = setTimeout(poll, 5000)
      } catch {
        failCount++
        const backoff = Math.min(5000 * Math.pow(2, failCount - 1), 60000)
        if (!cancelled) timeoutId = setTimeout(poll, backoff)
      }
    }

    poll()
    return () => { cancelled = true; clearTimeout(timeoutId) }
  }, [cameraId])

  return { streamUrl, isStreaming, status, error, startStream, stopStream }
}
