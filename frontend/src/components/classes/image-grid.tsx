'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CheckCircle, XCircle, Edit } from 'lucide-react'
import { ImageAnnotation } from './image-annotation'
import { api } from '@/lib/api'

interface TrainingImage {
  id: string
  caminho: string
  validada: boolean
  conjunto: string
  criado_em: string | null
}

interface ImageGridProps {
  classeId: number
  classeNome: string
  classIndex: number
  classes: Array<{ id: number; nome: string; cor_hex: string }>
  onAnnotationComplete?: () => void
}

export function ImageGrid({ classeId, classeNome, classIndex, classes, onAnnotationComplete }: ImageGridProps) {
  const [images, setImages] = useState<TrainingImage[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedImage, setSelectedImage] = useState<TrainingImage | null>(null)
  const [showAnnotation, setShowAnnotation] = useState(false)

  const fetchImages = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'}/api/classes/${classeId}/imagens`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      const result = await response.json()
      if (result.success) {
        setImages(result.imagens || [])
      }
    } catch (err: any) {
      console.error('Error fetching images:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchImages()
  }, [classeId])

  const handleAnnotate = (image: TrainingImage) => {
    setSelectedImage(image)
    setShowAnnotation(true)
  }

  const handleSaveAnnotation = async (annotations: string) => {
    if (!selectedImage) return

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'}/api/imagens/${selectedImage.id}/anotacao`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ anotacao_yolo: annotations })
      })

      const result = await response.json()
      if (result.success) {
        setShowAnnotation(false)
        setSelectedImage(null)
        fetchImages()
        if (onAnnotationComplete) {
          onAnnotationComplete()
        }
      }
    } catch (err: any) {
      alert('Erro ao salvar anotação: ' + (err.message || 'Erro desconhecido'))
    }
  }

  if (loading) {
    return (
      <CardContent>
        <div className="text-center py-8 text-muted-foreground">
          Carregando imagens...
        </div>
      </CardContent>
    )
  }

  if (images.length === 0) {
    return (
      <CardContent>
        <div className="text-center py-8 text-muted-foreground">
          <p>Nenhuma imagem enviada ainda.</p>
          <p className="text-sm mt-2">Faça upload de imagens para começar a anotar.</p>
        </div>
      </CardContent>
    )
  }

  if (showAnnotation && selectedImage) {
    return (
      <ImageAnnotation
        imageUrl={selectedImage.caminho}
        imageWidth={640}
        imageHeight={480}
        classIndex={classIndex}
        classes={classes}
        onSave={handleSaveAnnotation}
        onCancel={() => {
          setShowAnnotation(false)
          setSelectedImage(null)
        }}
      />
    )
  }

  return (
    <CardContent>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
        {images.map((image) => (
          <div key={image.id} className="relative group">
            <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
              <img
                src={image.caminho}
                alt=""
                className="w-full h-full object-cover"
              />
            </div>
            <div className="absolute top-2 right-2">
              {image.validada ? (
                <div className="bg-green-500 text-white p-1 rounded-full">
                  <CheckCircle className="w-3 h-3" />
                </div>
              ) : (
                <div className="bg-orange-500 text-white p-1 rounded-full">
                  <XCircle className="w-3 h-3" />
                </div>
              )}
            </div>
            <Button
              variant="secondary"
              size="sm"
              className="absolute bottom-2 left-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={() => handleAnnotate(image)}
            >
              <Edit className="w-3 h-3 mr-1" />
              {image.validada ? 'Editar' : 'Anotar'}
            </Button>
          </div>
        ))}
      </div>
      <div className="mt-4 text-center text-sm text-muted-foreground">
        {images.filter(i => i.validada).length} / {images.length} imagens anotadas
      </div>
    </CardContent>
  )
}
