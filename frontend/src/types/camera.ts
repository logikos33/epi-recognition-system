// Camera Types

export type CameraBrand =
  | 'hikvision'
  | 'dahua'
  | 'intelbras'
  | 'generic'
  | 'axis'
  | 'vivotek'

export interface Camera {
  id: number
  name: string
  location: string
  rtsp_url: string | null
  ip_address: string | null
  rtsp_username: string | null
  rtsp_password: string | null
  rtsp_port: number
  camera_brand: CameraBrand
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CameraFormData {
  name: string
  location: string
  ip_address: string
  rtsp_username: string
  rtsp_password: string
  rtsp_port: number
  camera_brand: CameraBrand
}

export interface ConnectionTest {
  success: boolean
  message: string
  resolution?: string
  latency?: number
}
