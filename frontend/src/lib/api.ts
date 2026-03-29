/**
 * REST API Client for EPI Recognition System
 *
 * This centralized client handles all communication with the backend API.
 * Replaces Supabase client with REST API calls.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

class APIClient {
  private token: string | null = null

  /**
   * Set authentication token for subsequent requests
   */
  setToken(token: string | null): void {
    this.token = token
  }

  /**
   * Get current token
   */
  getToken(): string | null {
    return this.token
  }

  /**
   * Clear authentication token
   */
  clearToken(): void {
    this.token = null
  }

  /**
   * Build headers for request
   */
  private buildHeaders(customHeaders: HeadersInit = {}): HeadersInit {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(customHeaders as Record<string, string>),
    }

    // Add Authorization header if token exists
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    return headers as HeadersInit
  }

  /**
   * Handle response and extract JSON data
   */
  private async handleResponse(response: Response): Promise<any> {
    if (!response.ok) {
      // Try to parse error message from response
      let errorMessage = `HTTP ${response.status}`
      try {
        const errorData = await response.json()
        errorMessage = errorData.error || errorData.message || errorMessage
      } catch {
        // If JSON parsing fails, use status text
        errorMessage = response.statusText || errorMessage
      }
      throw new Error(errorMessage)
    }

    // Some endpoints return 204 No Content
    if (response.status === 204) {
      return null
    }

    return response.json()
  }

  /**
   * Make HTTP request
   */
  private async request(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<any> {
    const url = `${API_BASE}${endpoint}`

    const config: RequestInit = {
      ...options,
      headers: this.buildHeaders(options.headers),
    }

    try {
      const response = await fetch(url, config)
      return await this.handleResponse(response)
    } catch (error) {
      // Re-throw network errors
      if (error instanceof Error) {
        throw error
      }
      throw new Error('An unknown error occurred')
    }
  }

  /**
   * GET request
   */
  async get(endpoint: string, options: Omit<RequestInit, 'method' | 'body'> = {}): Promise<any> {
    return this.request(endpoint, { ...options, method: 'GET' })
  }

  /**
   * POST request
   */
  async post(endpoint: string, data?: any, options: Omit<RequestInit, 'method'> = {}): Promise<any> {
    const config: RequestInit = {
      ...options,
      method: 'POST',
    }

    // Add body if data is provided
    if (data !== undefined) {
      config.body = JSON.stringify(data)
    }

    return this.request(endpoint, config)
  }

  /**
   * PUT request
   */
  async put(endpoint: string, data?: any, options: Omit<RequestInit, 'method'> = {}): Promise<any> {
    const config: RequestInit = {
      ...options,
      method: 'PUT',
    }

    // Add body if data is provided
    if (data !== undefined) {
      config.body = JSON.stringify(data)
    }

    return this.request(endpoint, config)
  }

  /**
   * PATCH request
   */
  async patch(endpoint: string, data?: any, options: Omit<RequestInit, 'method'> = {}): Promise<any> {
    const config: RequestInit = {
      ...options,
      method: 'PATCH',
    }

    // Add body if data is provided
    if (data !== undefined) {
      config.body = JSON.stringify(data)
    }

    return this.request(endpoint, config)
  }

  /**
   * DELETE request
   */
  async delete(endpoint: string, options: Omit<RequestInit, 'method' | 'body'> = {}): Promise<any> {
    return this.request(endpoint, { ...options, method: 'DELETE' })
  }

  /**
   * Upload file
   */
  async upload(endpoint: string, file: File | Blob, options: {
    method?: 'POST' | 'PUT'
    fields?: Record<string, string>
  } = {}): Promise<any> {
    const formData = new FormData()

    // Add file to form data
    if (file instanceof File) {
      formData.append('file', file)
    } else {
      // For Blob, create a fake file name
      formData.append('file', file, 'upload')
    }

    // Add additional fields
    if (options.fields) {
      Object.entries(options.fields).forEach(([key, value]) => {
        formData.append(key, value)
      })
    }

    // Build headers (don't set Content-Type for FormData, browser does it automatically with boundary)
    const headers: Record<string, string> = {}
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const url = `${API_BASE}${endpoint}`

    try {
      const response = await fetch(url, {
        method: options.method || 'POST',
        headers,
        body: formData,
      })

      return await this.handleResponse(response)
    } catch (error) {
      if (error instanceof Error) {
        throw error
      }
      throw new Error('Upload failed')
    }
  }

  /**
   * Download file
   */
  async download(endpoint: string): Promise<Blob> {
    const headers: Record<string, string> = {}
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const url = `${API_BASE}${endpoint}`

    const response = await fetch(url, { headers })

    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`)
    }

    return response.blob()
  }

  /**
   * ==============================
   * CAMERA MANAGEMENT
   * ==============================
   */

  /**
   * List all cameras
   */
  async listCameras(): Promise<{ success: boolean; cameras: any[] }> {
    return this.get('/api/cameras')
  }

  /**
   * Create a new camera
   */
  async createCamera(data: {
    bay_id: number;
    name: string;
    rtsp_url?: string;
    is_active?: boolean;
    position_order?: number;
  }): Promise<{ success: boolean; camera: any }> {
    return this.post('/api/cameras', data)
  }

  /**
   * Get camera by ID
   */
  async getCamera(cameraId: number): Promise<{ success: boolean; camera: any }> {
    return this.get(`/api/cameras/${cameraId}`)
  }

  /**
   * Update camera
   */
  async updateCamera(
    cameraId: number,
    data: {
      name?: string;
      rtsp_url?: string;
      is_active?: boolean;
      position_order?: number;
    }
  ): Promise<{ success: boolean; camera: any }> {
    return this.put(`/api/cameras/${cameraId}`, data)
  }

  /**
   * Delete camera
   */
  async deleteCamera(cameraId: number): Promise<{ success: boolean; message: string }> {
    return this.delete(`/api/cameras/${cameraId}`)
  }

  /**
   * Get cameras by bay
   */
  async getCamerasByBay(bayId: number): Promise<{ success: boolean; cameras: any[] }> {
    return this.get(`/api/cameras/by-bay/${bayId}`)
  }

  /**
   * List all bays
   */
  async listBays(): Promise<{ success: boolean; bays: any[] }> {
    return this.get('/api/bays')
  }
}

// Export singleton instance
export const api = new APIClient()

/**
 * API endpoints constants
 */
export const API_ENDPOINTS = {
  // Auth
  AUTH_REGISTER: '/api/auth/register',
  AUTH_LOGIN: '/api/auth/login',
  AUTH_LOGOUT: '/api/auth/logout',
  AUTH_VERIFY: '/api/auth/verify',
  AUTH_ME: '/api/auth/me',

  // Products
  PRODUCTS: '/api/products',
  PRODUCT: (id: string) => `/api/products/${id}`,

  // Cameras
  CAMERAS: '/api/cameras',
  CAMERA: (id: string) => `/api/cameras/${id}`,

  // Detections
  DETECTIONS: '/api/detections',
  DETECT: '/api/detect',

  // Counting Sessions
  COUNTING_SESSIONS: '/api/counting/sessions',
  COUNTING_SESSION: (id: string) => `/api/counting/sessions/${id}`,
  COUNTING_ACTIVE: '/api/counting/sessions/active',
  COUNTING_START_STREAM: '/api/counting/start-stream',
  COUNTING_STOP_STREAM: '/api/counting/stop-stream',

  // Training Projects
  TRAINING_PROJECTS: '/api/training/projects',
  TRAINING_PROJECT: (id: string) => `/api/training/projects/${id}`,
  TRAINING_PROJECT_STATUS: (id: string) => `/api/training/projects/${id}/status`,

  // Training Videos
  TRAINING_VIDEOS: (projectId: string) => `/api/training/projects/${projectId}/videos`,
  TRAINING_VIDEO: (projectId: string, videoId: string) => `/api/training/projects/${projectId}/videos/${videoId}`,

  // Training
  TRAINING_IMAGES: '/api/training/images',
  TRAINING_IMAGE: (id: string) => `/api/training/images/${id}`,
  TRAINING_ANNOTATIONS: '/api/training/annotations',
  TRAINING_EXPORT_DATASET: '/api/training/export-dataset',
  TRAINING_DOWNLOAD_DATASET: '/api/training/download-dataset',

  // Models
  MODELS: '/api/models',
  MODEL_UPLOAD: '/api/models/upload',
  MODEL_ACTIVATE: (id: string) => `/api/models/${id}/activate`,

  // Verification
  VERIFICATION_QUEUE: '/api/verification/queue',
  VERIFICATION_APPROVE: (id: string) => `/api/verification/${id}/approve`,
  VERIFICATION_REJECT: (id: string) => `/api/verification/${id}/reject`,
  VERIFICATION_CORRECT: (id: string) => `/api/verification/${id}/correct`,
  VERIFICATION_STATS: '/api/verification/stats',

  // Export
  EXPORT_SESSION: (id: string) => `/api/export/session/${id}`,
  EXPORT_DOWNLOAD: (fileId: string) => `/api/export/download/${fileId}`,

  // Health
  HEALTH: '/health',
} as const

/**
 * Training Projects API Functions
 */

/**
 * Create a new training project
 */
export async function createTrainingProject(request: {
  name: string
  description?: string
  target_classes: string[]
}) {
  return api.post(API_ENDPOINTS.TRAINING_PROJECTS, request)
}

/**
 * List all training projects for the current user
 */
export async function listTrainingProjects() {
  return api.get(API_ENDPOINTS.TRAINING_PROJECTS)
}

/**
 * Get a specific training project by ID
 */
export async function getTrainingProject(id: string) {
  return api.get(API_ENDPOINTS.TRAINING_PROJECT(id))
}

/**
 * Update a training project
 */
export async function updateTrainingProject(id: string, request: {
  name?: string
  description?: string
  target_classes?: string[]
}) {
  return api.put(API_ENDPOINTS.TRAINING_PROJECT(id), request)
}

/**
 * Delete a training project
 */
export async function deleteTrainingProject(id: string) {
  return api.delete(API_ENDPOINTS.TRAINING_PROJECT(id))
}

/**
 * Update training project status
 */
export async function updateTrainingProjectStatus(id: string, status: string) {
  return api.patch(API_ENDPOINTS.TRAINING_PROJECT_STATUS(id), { status })
}

/**
 * Upload a training video for a project
 */
export async function uploadTrainingVideo(projectId: string, file: File) {
  return api.upload(API_ENDPOINTS.TRAINING_VIDEOS(projectId), file)
}
