/**
 * API client — all requests go to /api/v1/ (new modular backend).
 * Auth token is automatically injected and expiry is validated before each request.
 */
import { getValidToken } from '../lib/jwt'

const API_BASE = ''  // Same-origin via Vite proxy

export class APIError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly data: unknown = null
  ) {
    super(message)
    this.name = 'APIError'
  }
}

async function request<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getValidToken()  // Validates expiry — returns null if expired

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const url = `${API_BASE}${endpoint}`

  try {
    const response = await fetch(url, { ...options, headers })
    let data: unknown
    try {
      data = await response.json()
    } catch {
      data = null
    }

    if (!response.ok) {
      if (response.status === 401) {
        // Clear invalid tokens
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      }
      const msg = (data as { error?: string; message?: string })?.error
        || (data as { message?: string })?.message
        || `HTTP ${response.status}`
      throw new APIError(msg, response.status, data)
    }

    return data as T
  } catch (err) {
    if (err instanceof APIError) throw err
    throw new APIError((err as Error).message || 'Network error', 0)
  }
}

function get<T = unknown>(endpoint: string) {
  return request<T>(endpoint, { method: 'GET' })
}

function post<T = unknown>(endpoint: string, data?: unknown) {
  return request<T>(endpoint, {
    method: 'POST',
    body: data !== undefined ? JSON.stringify(data) : undefined,
  })
}

function put<T = unknown>(endpoint: string, data?: unknown) {
  return request<T>(endpoint, {
    method: 'PUT',
    body: data !== undefined ? JSON.stringify(data) : undefined,
  })
}

function del<T = unknown>(endpoint: string) {
  return request<T>(endpoint, { method: 'DELETE' })
}

// ============================================================================
// Domain API methods — all use /api/v1/ (new backend)
// ============================================================================

interface AuthResponse {
  success: boolean
  data?: { token: string; user: { id: string; email: string; full_name?: string } }
  token?: string
  user?: { id: string; email: string; full_name?: string }
}

export const authApi = {
  login: (email: string, password: string) =>
    post<AuthResponse>('/api/v1/auth/login', { email, password }),
  register: (email: string, password: string, full_name?: string) =>
    post<AuthResponse>('/api/v1/auth/register', { email, password, full_name }),
  logout: () => post('/api/v1/auth/logout'),
  verify: () => get('/api/v1/auth/verify'),
}

export const camerasApi = {
  list: () => get('/api/v1/cameras/'),
  get: (id: string) => get(`/api/v1/cameras/${id}`),
  create: (data: unknown) => post('/api/v1/cameras/', data),
  update: (id: string, data: unknown) => put(`/api/v1/cameras/${id}`, data),
  delete: (id: string) => del(`/api/v1/cameras/${id}`),
  test: (data: unknown) => post('/api/v1/cameras/test', data),
}

export const videosApi = {
  list: () => get('/api/v1/videos/'),
  get: (id: string) => get(`/api/v1/videos/${id}`),
  delete: (id: string) => del(`/api/v1/videos/${id}`),
  upload: async (file: File) => {
    const token = getValidToken()
    const formData = new FormData()
    formData.append('file', file)
    const response = await fetch('/api/v1/videos/', {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    const data = await response.json()
    if (!response.ok) throw new APIError(data.error || 'Upload failed', response.status, data)
    return data
  },
}

export const annotationsApi = {
  listFrames: (videoId?: string) =>
    get(`/api/v1/annotations/frames${videoId ? `?video_id=${videoId}` : ''}`),
  getFrame: (id: string) => get(`/api/v1/annotations/frames/${id}`),
  saveLabels: (frameId: string, labels: unknown[]) =>
    post(`/api/v1/annotations/frames/${frameId}/labels`, { labels }),
  listClasses: () => get('/api/v1/annotations/classes'),
  createClass: (name: string, color: string) =>
    post('/api/v1/annotations/classes', { name, color }),
}

export const trainingApi = {
  listJobs: () => get('/api/v1/training/jobs'),
  createJob: (config: unknown) => post('/api/v1/training/jobs', config),
  getJob: (id: string) => get(`/api/v1/training/jobs/${id}`),
}

export const healthApi = {
  check: () => get('/api/v1/health/'),
  checkDb: () => get('/api/v1/health/db'),
  checkRedis: () => get('/api/v1/health/redis'),
  checkYolo: () => get('/api/v1/health/yolo'),
}
