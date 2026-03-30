export interface Camera {
  id: number;
  user_id: string;
  name: string;
  manufacturer: 'intelbras' | 'hikvision' | 'generic';
  type: 'ip' | 'dvr' | 'nvr';
  ip: string;
  port: number;
  username: string;
  password: string;
  channel: number;
  subtype: number;
  rtsp_url: string;
  is_active: boolean;
  last_connected_at: string | null;
  connection_error: string | null;
  created_at: string;
}

export interface Detection {
  camera_id: number;
  timestamp: number;
  frame_id: number;
  detections: DetectionBox[];
}

export interface DetectionBox {
  bbox: [number, number, number, number];
  class: string;
  confidence: number;
}

export interface StreamStatus {
  camera_id: number;
  status: 'idle' | 'starting' | 'streaming' | 'error';
  hls_url: string | null;
}

export interface HLSCameraFeedProps {
  cameraId: number;
  mode: 'primary' | 'thumbnail';
}
