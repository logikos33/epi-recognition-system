import { useState, useCallback } from 'react'

export function useCameraConnection() {
  const [testing, setTesting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const test = useCallback(async (config) => {
    setTesting(true)
    setResult(null)
    setError(null)
    try {
      const token = localStorage.getItem('token') || sessionStorage.getItem('token')
      const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      }
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 15000)
      const res = await fetch('/api/cameras/test-url', {
        method: 'POST',
        headers,
        body: JSON.stringify(config),
        signal: controller.signal
      })
      clearTimeout(timeout)
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
      setResult(data)
      return data
    } catch (err) {
      const msg = err.name === 'AbortError'
        ? 'Timeout: câmera não respondeu em 15s'
        : err.message
      setError(msg)
      throw err
    } finally {
      setTesting(false)
    }
  }, [])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
    setTesting(false)
  }, [])

  return { test, testing, result, snapshotBase64: result?.snapshot_base64, error, reset }
}
