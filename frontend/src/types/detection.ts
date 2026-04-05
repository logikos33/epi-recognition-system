// Detection Types

export type EPIType = 'helmet' | 'gloves' | 'glasses' | 'vest' | 'boots'

export interface EPIsDetected {
  helmet: boolean
  gloves: boolean
  glasses: boolean
  vest: boolean
  boots: boolean
}

export interface Detection {
  id: number
  camera_id: number
  timestamp: string
  epis_detected: EPIsDetected
  confidence: number
  is_compliant: boolean
  person_count: number
  created_at: string
}

export interface DetectionWithCamera extends Detection {
  camera: {
    id: number
    name: string
    location: string
  }
}

export interface DetectionFilters {
  camera_id?: number
  is_compliant?: boolean
  start_date?: string
  end_date?: string
  min_confidence?: number
}
