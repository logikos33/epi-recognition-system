// frontend/src/hooks/useOCR.ts
'use client'

import { useState, useCallback } from 'react'
import { api } from '@/lib/api'

/**
 * OCR Recognition Result
 */
export interface OCRRecognitionResult {
  license_plate: string
  confidence: number
  valid: boolean
}

/**
 * OCR Recognition Error
 */
export interface OCRError {
  message: string
  code?: string
}

/**
 * Result type for recognizeLicensePlate
 */
export type RecognizeLicensePlateResult = OCRRecognitionResult & {
  success: boolean
}

/**
 * useOCR Hook Result Interface
 */
export interface UseOCRResult {
  recognizeLicensePlate: (imageFile: File) => Promise<OCRRecognitionResult>
  loading: boolean
  error: string | null
  clearError: () => void
}

/**
 * Hook for OCR (Optical Character Recognition) operations
 * Provides license plate recognition from images with loading and error states
 *
 * @example
 * const { recognizeLicensePlate, loading, error, clearError } = useOCR()
 *
 * const handleImageUpload = async (file: File) => {
 *   try {
 *     const result = await recognizeLicensePlate(file)
 *     console.log('Plate:', result.license_plate)
 *     console.log('Confidence:', result.confidence)
 *     console.log('Valid:', result.valid)
 *   } catch (err) {
 *     console.error('Recognition failed:', error)
 *   }
 * }
 */
export function useOCR(): UseOCRResult {
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  /**
   * Recognize license plate from image file
   *
   * @param imageFile - Image file to process (jpg, png, jpeg, bmp)
   * @returns Promise with recognition result containing license_plate, confidence, and valid status
   * @throws Error if recognition fails or file is invalid
   */
  const recognizeLicensePlate = useCallback(async (
    imageFile: File
  ): Promise<OCRRecognitionResult> => {
    // Validate file
    if (!imageFile) {
      const errorMsg = 'No image file provided'
      setError(errorMsg)
      throw new Error(errorMsg)
    }

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp']
    if (!allowedTypes.includes(imageFile.type)) {
      const errorMsg = `Invalid file type: ${imageFile.type}. Allowed: JPEG, PNG, BMP`
      setError(errorMsg)
      throw new Error(errorMsg)
    }

    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024 // 10MB in bytes
    if (imageFile.size > maxSize) {
      const errorMsg = `File too large: ${(imageFile.size / 1024 / 1024).toFixed(2)}MB. Max size: 10MB`
      setError(errorMsg)
      throw new Error(errorMsg)
    }

    setLoading(true)
    setError(null)

    try {
      // Upload image to OCR endpoint
      const result = await api.upload('/api/ocr/recognize-license-plate', imageFile)

      if (!result.success) {
        const errorMsg = result.error || 'OCR recognition failed'
        setError(errorMsg)
        throw new Error(errorMsg)
      }

      // Return recognition result
      return {
        license_plate: result.license_plate,
        confidence: result.confidence,
        valid: result.valid
      }
    } catch (err) {
      // Handle different error types
      let errorMsg = 'Failed to recognize license plate'

      if (err instanceof Error) {
        errorMsg = err.message
      } else if (typeof err === 'string') {
        errorMsg = err
      }

      // Check for network errors
      if (errorMsg.includes('fetch') || errorMsg.includes('network')) {
        errorMsg = 'Network error. Please check your connection.'
      }

      // Check for server errors
      if (errorMsg.includes('500') || errorMsg.includes('Internal Server Error')) {
        errorMsg = 'Server error. Please try again later.'
      }

      // Check for auth errors
      if (errorMsg.includes('401') || errorMsg.includes('Unauthorized')) {
        errorMsg = 'Authentication required. Please log in.'
      }

      setError(errorMsg)
      throw new Error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    recognizeLicensePlate,
    loading,
    error,
    clearError
  }
}
