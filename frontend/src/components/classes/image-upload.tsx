'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Upload, X, Image as ImageIcon, Loader2, Check } from 'lucide-react'
import { api } from '@/lib/api'

interface TrainingImage {
  id: string
  classe_id: number
  caminho: string
  validada: boolean
  conjunto: string
}

interface ImageUploadProps {
  classeId: number
  classeNome: string
  onUploadComplete?: () => void
}

export function ImageUpload({ classeId, classeNome, onUploadComplete }: ImageUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [images, setImages] = useState<File[]>([])
  const [uploadedImages, setUploadedImages] = useState<TrainingImage[]>([])
  const [error, setError] = useState('')

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setError('')
    setImages(prev => [...prev, ...acceptedFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpg', '.jpeg', '.png']
    },
    maxFiles: 50
  })

  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index))
  }

  const uploadImages = async () => {
    if (images.length === 0) {
      setError('Selecione pelo menos uma imagem')
      return
    }

    setUploading(true)
    setError('')

    try {
      const formData = new FormData()
      images.forEach(file => {
        formData.append('imagens', file)
      })

      // Upload images to API
      const token = localStorage.getItem('token')
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'}/api/classes/${classeId}/imagens`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      const result = await response.json()

      if (!result.success) {
        throw new Error(result.error || 'Erro ao fazer upload')
      }

      // Reset
      setImages([])
      if (onUploadComplete) {
        onUploadComplete()
      }

      alert(`${result.imagens.length} imagens enviadas com sucesso!`)
    } catch (err: any) {
      setError(err.message || 'Erro ao fazer upload')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <Card>
        <CardContent className="p-6">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragActive ? 'border-primary bg-primary/5' : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <input {...getInputProps()} disabled={uploading} />
            <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-sm text-muted-foreground mb-2">
              Arraste imagens aqui ou clique para selecionar
            </p>
            <p className="text-xs text-muted-foreground">
              JPG, PNG (máx 50 por vez)
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Selected Images Preview */}
      {images.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">
                {images.length} imagem{images.length !== 1 ? 's' : ''} selecionada
                {images.length !== 1 && 's'}
              </h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setImages([])}
              >
                Limpar
              </Button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {images.map((file, index) => (
                <div key={index} className="relative group">
                  <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
                    <img
                      src={URL.createObjectURL(file)}
                      alt={file.name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <Button
                    variant="destructive"
                    size="icon"
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => removeImage(index)}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                  <p className="text-xs text-center mt-1 truncate">
                    {file.name}
                  </p>
                </div>
              ))}
            </div>

            {images.length > 0 && (
              <div className="mt-4 flex gap-2">
                <Button onClick={uploadImages} disabled={uploading}>
                  {uploading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  {uploading ? 'Enviando...' : 'Enviar Imagens'}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Uploaded Images */}
      {uploadedImages.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <h3 className="font-semibold">
              Imagens Enviadas ({uploadedImages.length})
            </h3>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {uploadedImages.map((img) => (
                <div key={img.id} className="relative">
                  <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
                    <img
                      src={img.caminho}
                      alt=""
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="absolute top-2 right-2">
                    {img.validada ? (
                      <div className="bg-green-500 text-white p-1 rounded-full">
                        <Check className="w-3 h-3" />
                      </div>
                    ) : (
                      <div className="bg-yellow-500 text-white p-1 rounded-full text-xs">
                        Pendente
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  )
}
