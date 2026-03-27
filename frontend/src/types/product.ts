/**
 * Product Type Definitions for EPI Recognition System
 */

/**
 * Product entity from database
 */
export interface Product {
  id: string
  user_id: string
  name: string
  sku: string | null
  category: string | null
  description: string | null
  image_url: string | null
  detection_threshold: number
  is_active: boolean
  volume_cm3: number | null
  weight_g: number | null
  created_at: string | null
  updated_at: string | null
  // Extra fields from queries
  training_images_count?: number
  annotated_images_count?: number
}

/**
 * Input for creating a new product
 */
export interface CreateProductInput {
  name: string
  sku?: string
  category?: string
  description?: string
  image_url?: string
  detection_threshold?: number
  volume_cm3?: number
  weight_g?: number
}

/**
 * Input for updating a product (all fields optional)
 */
export interface UpdateProductInput {
  name?: string
  sku?: string
  category?: string
  description?: string
  image_url?: string
  detection_threshold?: number
  is_active?: boolean
  volume_cm3?: number
  weight_g?: number
}

/**
 * Product with training statistics
 */
export interface ProductWithStats extends Product {
  training_images_count: number
  annotated_images_count: number
  ready_for_training: boolean
  annotation_progress: number
}

/**
 * Product list response from API
 */
export interface ProductsListResponse {
  success: boolean
  products: Product[]
  count: number
}

/**
 * Product detail response from API
 */
export interface ProductResponse {
  success: boolean
  product: Product
  message?: string
}

/**
 * Product category options
 */
export const PRODUCT_CATEGORIES = [
  'Bebidas',
  'Alimentos',
  'Limpeza',
  'Higiene',
  'Eletrônicos',
  'Vestuário',
  'Ferramentas',
  'Medicamentos',
  'Outros',
] as const

export type ProductCategory = typeof PRODUCT_CATEGORIES[number]
