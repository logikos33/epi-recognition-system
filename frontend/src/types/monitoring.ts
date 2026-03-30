// frontend/src/types/monitoring.ts

/**
 * Fueling bay (area de abastecimento)
 */
export interface Bay {
  id: number;
  name: string;
  location: string | null;
  scale_integration: boolean;
  created_at: string;
}

/**
 * IP Camera configuration
 */
export interface Camera {
  id: number;
  bay_id: number;
  name: string;
  rtsp_url: string | null;
  is_active: boolean;
  position_order: number;
  created_at: string | null;
  bay_name?: string;
}

/**
 * Fueling session (truck entry/exit)
 */
export interface FuelingSession {
  id: string;
  bay_id: number;
  camera_id: number;
  license_plate: string | null;
  truck_entry_time: string;
  truck_exit_time: string | null;
  duration_seconds: number | null;
  products_counted: Record<string, number>; // {caixas: 120, pallets: 3}
  final_weight: number | null;
  status: 'active' | 'completed';
  created_at: string;
}

/**
 * Counted product entry
 */
export interface CountedProduct {
  id: string;
  session_id: string;
  product_type: string; // "caixa", "pallet", "saco", etc.
  quantity: number;
  confidence: number;
  confirmed_by_user: boolean;
  is_ai_suggestion: boolean;
  corrected_to_type: string | null;
  timestamp: string;
}

/**
 * User camera layout configuration
 */
export interface UserCameraLayout {
  id: string;
  user_id: string;
  layout_name: string;
  selected_cameras: number[];
  camera_configs: CameraConfigMap;
  created_at: string;
}

/**
 * Camera position/size configuration
 */
export interface CameraConfig {
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex: number;
}

/**
 * Map of camera_id -> CameraConfig
 */
export interface CameraConfigMap {
  [cameraId: string]: CameraConfig;
}

/**
 * Live session info for overlay
 */
export interface SessionInfo {
  sessionId: string | null;
  licensePlate: string | null;
  entryTime: Date;
  elapsedTime: string; // "12:45" format
  productCount: number;
  currentWeight: number;
  status: 'active' | 'completed' | 'paused';
}

/**
 * OCR detection result
 */
export interface OCRResult {
  success: boolean;
  plate: string | null;
  confidence: number;
}

/**
 * Scale weight reading
 */
export interface ScaleWeight {
  weight: number;
  unit: string;
  timestamp: string | null;
}

/**
 * Product detection from YOLO
 */
export interface ProductDetection {
  productType: string;
  quantity: number;
  confidence: number;
  bbox: [number, number, number, number]; // [x, y, width, height]
}