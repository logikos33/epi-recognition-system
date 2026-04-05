'use client'

import { useEffect, useState, useCallback } from 'react'
import { api } from '@/lib/api'
import type { Product, CreateProductInput, UpdateProductInput } from '@/types/product'

interface UseProductsResult {
  products: Product[]
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
  createProduct: (data: CreateProductInput) => Promise<{ product: Product | null; error: string | null }>
  updateProduct: (id: string, data: UpdateProductInput) => Promise<{ product: Product | null; error: string | null }>
  deleteProduct: (id: string) => Promise<{ error: string | null }>
  getProduct: (id: string) => Promise<Product | null>
}

/**
 * Products Management Hook using REST API
 *
 * Provides CRUD operations for products.
 * Follows the same pattern as useCameras but uses REST API instead of Supabase.
 */
export function useProducts(): UseProductsResult {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch products from API
   */
  const fetchProducts = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await api.get('/api/products')

      if (response.success && response.products) {
        setProducts(response.products)
      } else {
        const errorMsg = response.error || 'Failed to fetch products'
        setError(errorMsg)
        setProducts([])
      }
    } catch (err: any) {
      const errorMsg = err?.message || 'Network error while fetching products'
      setError(errorMsg)
      setProducts([])
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch products on mount
  useEffect(() => {
    fetchProducts()
  }, [fetchProducts])

  /**
   * Create new product
   */
  const createProduct = async (data: CreateProductInput): Promise<{ product: Product | null; error: string | null }> => {
    try {
      setError(null)

      const response = await api.post('/api/products', data)

      if (response.success && response.product) {
        // Add new product to the beginning of the list
        setProducts((prev) => [response.product, ...prev])
        return { product: response.product, error: null }
      } else {
        const errorMsg = response.error || 'Failed to create product'
        setError(errorMsg)
        return { product: null, error: errorMsg }
      }
    } catch (err: any) {
      const errorMsg = err?.message || 'Network error while creating product'
      setError(errorMsg)
      return { product: null, error: errorMsg }
    }
  }

  /**
   * Update existing product
   */
  const updateProduct = async (
    id: string,
    data: UpdateProductInput
  ): Promise<{ product: Product | null; error: string | null }> => {
    try {
      setError(null)

      const response = await api.put(`/api/products/${id}`, data)

      if (response.success && response.product) {
        // Update product in the list
        setProducts((prev) =>
          prev.map((p) => (p.id === id ? response.product : p))
        )
        return { product: response.product, error: null }
      } else {
        const errorMsg = response.error || 'Failed to update product'
        setError(errorMsg)
        return { product: null, error: errorMsg }
      }
    } catch (err: any) {
      const errorMsg = err?.message || 'Network error while updating product'
      setError(errorMsg)
      return { product: null, error: errorMsg }
    }
  }

  /**
   * Delete product (soft delete - sets is_active = false)
   */
  const deleteProduct = async (id: string): Promise<{ error: string | null }> => {
    try {
      setError(null)

      const response = await api.delete(`/api/products/${id}`)

      if (response.success) {
        // Remove product from the list
        setProducts((prev) => prev.filter((p) => p.id !== id))
        return { error: null }
      } else {
        const errorMsg = response.error || 'Failed to delete product'
        setError(errorMsg)
        return { error: errorMsg }
      }
    } catch (err: any) {
      const errorMsg = err?.message || 'Network error while deleting product'
      setError(errorMsg)
      return { error: errorMsg }
    }
  }

  /**
   * Get single product by ID
   */
  const getProduct = async (id: string): Promise<Product | null> => {
    try {
      const response = await api.get(`/api/products/${id}`)

      if (response.success && response.product) {
        return response.product
      } else {
        return null
      }
    } catch (err) {
      console.error('Error fetching product:', err)
      return null
    }
  }

  return {
    products,
    loading,
    error,
    refetch: fetchProducts,
    createProduct,
    updateProduct,
    deleteProduct,
    getProduct,
  }
}
