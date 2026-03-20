// Supabase Database Types
// These types match your Supabase schema

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      cameras: {
        Row: {
          id: number
          name: string
          location: string
          rtsp_url: string | null
          ip_address: string | null
          rtsp_username: string | null
          rtsp_password: string | null
          rtsp_port: number
          camera_brand: string
          is_active: boolean
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: number
          name: string
          location: string
          rtsp_url?: string | null
          ip_address?: string | null
          rtsp_username?: string | null
          rtsp_password?: string | null
          rtsp_port?: number
          camera_brand?: string
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: number
          name?: string
          location?: string
          rtsp_url?: string | null
          ip_address?: string | null
          rtsp_username?: string | null
          rtsp_password?: string | null
          rtsp_port?: number
          camera_brand?: string
          is_active?: boolean
          updated_at?: string
        }
      }
      detections: {
        Row: {
          id: number
          camera_id: number
          timestamp: string
          epis_detected: Json
          confidence: number
          is_compliant: boolean
          person_count: number
          created_at: string
        }
        Insert: {
          id?: number
          camera_id: number
          timestamp?: string
          epis_detected: Json
          confidence?: number
          is_compliant?: boolean
          person_count?: number
          created_at?: string
        }
        Update: {
          camera_id?: number
          epis_detected?: Json
          confidence?: number
          is_compliant?: boolean
          person_count?: number
        }
      }
      worker_status: {
        Row: {
          worker_id: string
          status: string
          active_cameras: number[]
          last_heartbeat: string
          created_at: string
          updated_at: string
        }
        Insert: {
          worker_id: string
          status?: string
          active_cameras?: number[]
          last_heartbeat?: string
          created_at?: string
          updated_at?: string
        }
        Update: {
          status?: string
          active_cameras?: number[]
          last_heartbeat?: string
          updated_at?: string
        }
      }
    }
  }
}
