// ============================================================================
// API Service Layer - EPI Recognition System
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

// ============================================================================
// Error Handling
// ============================================================================

class APIError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

// ============================================================================
// HTTP Helpers
// ============================================================================

async function request(endpoint, options = {}) {
  const token = localStorage.getItem('token');

  const headers = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...options.headers,
  };

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new APIError(
        data.error || data.message || 'Request failed',
        response.status,
        data
      );
    }

    return data;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(
      error.message || 'Network error',
      0,
      null
    );
  }
}

const GET = (endpoint) => request(endpoint, { method: 'GET' });
const POST = (endpoint, data) => request(endpoint, {
  method: 'POST',
  body: JSON.stringify(data),
});
const PUT = (endpoint, data) => request(endpoint, {
  method: 'PUT',
  body: JSON.stringify(data),
});
const DELETE = (endpoint) => request(endpoint, { method: 'DELETE' });

// ============================================================================
// API Methods
// ============================================================================

export const api = {
  // ========================================================================
  // Authentication
  // ========================================================================
  auth: {
    login: async (email, password) => {
      const response = await POST('/api/auth/login', { email, password });
      if (response.success && response.token) {
        localStorage.setItem('token', response.token);
      }
      return response;
    },

    register: async (email, password, full_name, company_name) => {
      return POST('/api/auth/register', {
        email,
        password,
        full_name,
        company_name,
      });
    },

    logout: () => {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    },

    getToken: () => localStorage.getItem('token'),
    isAuthenticated: () => !!localStorage.getItem('token'),
  },

  // ========================================================================
  // Cameras
  // ========================================================================
  cameras: {
    list: async () => {
      const response = await GET('/api/cameras');
      return response.cameras || [];
    },

    getById: async (cameraId) => {
      const response = await GET(`/api/cameras/${cameraId}`);
      return response.camera;
    },

    create: async (cameraData) => {
      const response = await POST('/api/cameras', cameraData);
      return response.camera;
    },

    update: async (cameraId, cameraData) => {
      const response = await PUT(`/api/cameras/${cameraId}`, cameraData);
      return response.camera;
    },

    delete: async (cameraId) => {
      const response = await DELETE(`/api/cameras/${cameraId}`);
      return response;
    },

    testConnection: async (ip, port = 554, username = null, password = null) => {
      const response = await POST('/api/cameras/test', {
        ip,
        port,
        username,
        password,
      });
      return response;
    },

    // Stream control
    startStream: async (cameraId) => {
      const response = await POST(`/api/cameras/${cameraId}/stream/start`);
      return response;
    },

    stopStream: async (cameraId) => {
      const response = await POST(`/api/cameras/${cameraId}/stream/stop`);
      return response;
    },

    getStreamStatus: async (cameraId) => {
      const response = await GET(`/api/cameras/${cameraId}/stream/status`);
      return response;
    },

    // Get HLS stream URL
    getStreamURL: (cameraId) => {
      return `${API_BASE_URL}/streams/${cameraId}/index.m3u8`;
    },
  },

  // ========================================================================
  // Streams (Global)
  // ========================================================================
  streams: {
    getAllStatus: async () => {
      const response = await GET('/api/streams/status');
      return response;
    },

    getHealthReport: async () => {
      const response = await GET('/streams/health');
      return response;
    },
  },

  // ========================================================================
  // Health Check
  // ========================================================================
  health: {
    check: async () => {
      const response = await GET('/health');
      return response;
    },
  },
};

// ============================================================================
// Export
// ============================================================================

export default api;
