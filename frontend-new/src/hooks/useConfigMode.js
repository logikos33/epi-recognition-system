import { useState, useEffect, useRef, useCallback } from 'react'

const CONFIG_DURATION = 600 // 10 minutos

export function useConfigMode() {
  const [isActive, setIsActive] = useState(false)
  const [secondsRemaining, setSecondsRemaining] = useState(0)
  const [token, setToken] = useState(null)
  const timerRef = useRef(null)
  const countdownRef = useRef(null)

  const exit = useCallback(async () => {
    if (timerRef.current) clearTimeout(timerRef.current)
    if (countdownRef.current) clearInterval(countdownRef.current)
    setIsActive(false)
    setToken(null)
    setSecondsRemaining(0)
    try {
      const authToken = localStorage.getItem('token') || sessionStorage.getItem('token')
      await fetch('/api/cameras/config/exit', {
        method: 'POST',
        headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
      })
    } catch { /* silencioso */ }
  }, [])

  const enter = useCallback(async () => {
    try {
      const authToken = localStorage.getItem('token') || sessionStorage.getItem('token')
      const res = await fetch('/api/cameras/config/enter', {
        method: 'POST',
        headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Erro ao ativar modo configuração')
      setToken(data.token)
      setIsActive(true)
      setSecondsRemaining(CONFIG_DURATION)

      // Auto-expirar após CONFIG_DURATION segundos
      timerRef.current = setTimeout(() => {
        setIsActive(false)
        setToken(null)
        setSecondsRemaining(0)
      }, CONFIG_DURATION * 1000)

      // Countdown visual
      countdownRef.current = setInterval(() => {
        setSecondsRemaining(s => {
          if (s <= 1) {
            clearInterval(countdownRef.current)
            return 0
          }
          return s - 1
        })
      }, 1000)

      return data.token
    } catch (err) {
      throw err
    }
  }, [])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      if (countdownRef.current) clearInterval(countdownRef.current)
    }
  }, [])

  return { isActive, secondsRemaining, token, enter, exit }
}
