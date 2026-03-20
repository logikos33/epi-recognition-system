// Camera Types

export type CameraBrand =
  | 'hikvision'
  | 'dahua'
  | 'intelbras'
  | 'generic'
  | 'axis'
  | 'vivotek'

export type CameraType =
  | 'cctv'          // Câmera CFTV/IP com RTSP
  | 'webcam'        // Webcam USB
  | 'mobile'        // Câmera do celular
  | 'ipcamera'      // Câmera IP standalone

export type StreamProtocol =
  | 'rtsp'          // RTSP para CFTV
  | 'http'          // HTTP stream
  | 'webrtc'        // WebRTC
  | 'hls'           // HLS stream

export interface Camera {
  id: number
  name: string
  location: string
  rtsp_url: string | null
  ip_address: string | null
  rtsp_username: string | null
  rtsp_password: string | null        // Note: Use vault in production
  rtsp_port: number
  camera_brand: CameraBrand
  camera_type: CameraType
  stream_protocol: StreamProtocol
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
  camera_type?: CameraType
  stream_protocol?: StreamProtocol
}

export interface ConnectionTest {
  success: boolean
  message: string
  resolution?: string
  latency?: number
  stream_url?: string
}

// Interface para câmera CFTV futura
export interface CCTVCamera extends Camera {
  camera_type: 'cctv'
  stream_protocol: 'rtsp' | 'http' | 'hls'
  rtsp_url: string  // Obrigatório para CFTV
  channels?: number  // Número de canais (ex: câmeras com múltiplas saídas)
}

// Interface para câmera mobile/webcam atual
export interface WebCamera extends Omit<Camera, 'rtsp_url' | 'rtsp_username' | 'rtsp_password' | 'rtsp_port'> {
  camera_type: 'webcam' | 'mobile'
  stream_protocol: 'webrtc'
  device_id?: string  // Para múltiplas câmeras
}

