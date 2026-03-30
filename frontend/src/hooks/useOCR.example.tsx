// Example usage of useOCR hook
// This file demonstrates how to integrate the useOCR hook in a component

'use client'

import { useOCR } from '@/hooks/useOCR'

export default function LicensePlateRecognizer() {
  const { recognizeLicensePlate, loading, error, clearError } = useOCR()

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      clearError()
      const result = await recognizeLicensePlate(file)

      console.log('License Plate:', result.license_plate)
      console.log('Confidence:', result.confidence)
      console.log('Valid:', result.valid)

      // Use the result...
      if (result.valid && result.confidence > 80) {
        alert(`Recognized: ${result.license_plate} (${result.confidence}% confidence)`)
      } else {
        alert(`Low confidence: ${result.license_plate} (${result.confidence}%). Please verify.`)
      }
    } catch (err) {
      console.error('Recognition failed:', err)
      alert(`Error: ${error}`)
    }
  }

  return (
    <div>
      <h2>License Plate Recognition</h2>

      <input
        type="file"
        accept="image/jpeg,image/jpg,image/png,image/bmp"
        onChange={handleFileChange}
        disabled={loading}
      />

      {loading && <p>Processing image...</p>}

      {error && (
        <div style={{ color: 'red' }}>
          <p>Error: {error}</p>
          <button onClick={clearError}>Clear Error</button>
        </div>
      )}
    </div>
  )
}
