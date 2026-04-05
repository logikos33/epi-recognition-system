/**
 * JWT Utilities for token validation and management
 */

export interface JWTPayload {
  user_id: string
  email: string
  exp: number
  iat?: number
}

/**
 * Decode JWT token without verification (for client-side validation only)
 */
export function decodeJWT(token: string): JWTPayload | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) {
      return null
    }

    const payload = parts[1]
    const decoded = atob(payload)
    return JSON.parse(decoded) as JWTPayload
  } catch (error) {
    console.error('Failed to decode JWT:', error)
    return null
  }
}

/**
 * Check if JWT token is expired
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeJWT(token)
  if (!payload) {
    return true
  }

  const currentTime = Math.floor(Date.now() / 1000)
  return payload.exp < currentTime
}

/**
 * Get time until token expires (in seconds)
 */
export function getTokenTTL(token: string): number {
  const payload = decodeJWT(token)
  if (!payload) {
    return 0
  }

  const currentTime = Math.floor(Date.now() / 1000)
  return Math.max(0, payload.exp - currentTime)
}

/**
 * Format TTL as human-readable string
 */
export function formatTTL(seconds: number): string {
  if (seconds < 60) {
    return `${seconds} segundos`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    return `${minutes} minuto${minutes !== 1 ? 's' : ''}`
  } else {
    const hours = Math.floor(seconds / 3600)
    const days = Math.floor(hours / 24)
    hours = hours % 24
    if (days > 0) {
      return `${days} dia${days !== 1 ? 's' : ''} e ${hours}h`
    }
    return `${hours}h`
  }
}

/**
 * Validate token and check if it needs refresh
 * Returns: 'valid' | 'expired' | 'expiring-soon' | 'invalid'
 */
export function validateToken(token: string): 'valid' | 'expired' | 'expiring-soon' | 'invalid' {
  const payload = decodeJWT(token)
  if (!payload) {
    return 'invalid'
  }

  const currentTime = Math.floor(Date.now() / 1000)
  const ttl = payload.exp - currentTime

  if (ttl <= 0) {
    return 'expired'
  } else if (ttl < 300) { // Less than 5 minutes
    return 'expiring-soon'
  } else {
    return 'valid'
  }
}
