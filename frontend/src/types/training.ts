/**
 * Training Type Definitions for EPI Recognition System
 */

/**
 * Training project status
 */
export type TrainingProjectStatus = 'draft' | 'in_progress' | 'training' | 'completed' | 'failed'

/**
 * Training project entity from database
 */
export interface TrainingProject {
  id: string
  user_id: string
  name: string
  description: string | null
  target_classes: string[]
  status: TrainingProjectStatus
  created_at: string
  updated_at: string
}

/**
 * Input for creating a new training project
 */
export interface CreateTrainingProjectRequest {
  name: string
  description?: string
  target_classes: string[]
}

/**
 * Input for updating a training project (all fields optional)
 */
export interface UpdateTrainingProjectRequest {
  name?: string
  description?: string
  target_classes?: string[]
}

/**
 * Training video entity
 */
export interface TrainingVideo {
  id: string
  project_id: string
  filename: string
  storage_path: string
  duration_seconds: number | null
  frame_count: number | null
  fps: number | null
  uploaded_at: string
}

/**
 * Training frame entity
 */
export interface TrainingFrame {
  id: string
  video_id: string
  frame_number: number
  storage_path: string
  is_annotated: boolean
  created_at: string
}

/**
 * Annotation entity
 */
export interface Annotation {
  id: string
  frame_id: string
  class_name: string
  bbox_x: number
  bbox_y: number
  bbox_width: number
  bbox_height: number
  confidence: number | null
  is_ai_generated: boolean
  is_reviewed: boolean
  created_at: string
}

/**
 * Training configuration
 */
export interface TrainingConfig {
  epochs: number
  batch_size: number
  image_size: number
  learning_rate: number
  optimizer: 'sgd' | 'adam' | 'adamw'
  train_val_split: number
}

/**
 * Training project list response from API
 */
export interface TrainingProjectsListResponse {
  success: boolean
  projects: TrainingProject[]
  count: number
}

/**
 * Training project detail response from API
 */
export interface TrainingProjectResponse {
  success: boolean
  project: TrainingProject
  message?: string
}

/**
 * Update status request
 */
export interface UpdateTrainingProjectStatusRequest {
  status: TrainingProjectStatus
}
