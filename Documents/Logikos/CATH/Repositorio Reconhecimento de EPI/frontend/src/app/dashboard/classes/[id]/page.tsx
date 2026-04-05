'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Edit, Trash2 } from 'lucide-react'
import { ClassFormModal } from '@/components/classes/class-form-modal'
import { ImageUpload } from '@/components/classes/image-upload'
import { ImageGrid } from '@/components/classes/image-grid'
import { api } from '@/lib/api'

interface YOLOClass {
  id: string
  name: string
  display_name: string
  color: string
  description?: string
  images_count: number
  created_at: string
}

export default function ClassDetailPage() {
  const params = useParams()
  const router = useRouter()
  const classId = params.id as string

  const [cls, setClass] = useState<YOLOClass | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [uploadedImages, setUploadedImages] = useState<string[]>([])
  const [classImages, setClassImages] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)

  useEffect(() => {
    loadClass()
    loadClassImages()
  }, [classId])

  const loadClass = async () => {
    try {
      setIsLoading(true)
      const response = await api.get<{ class: YOLOClass }>(`/api/classes/${classId}`)
      setClass(response.class)
    } catch (error) {
      console.error('Error loading class:', error)
      alert('Erro ao carregar classe')
      router.push('/dashboard/classes')
    } finally {
      setIsLoading(false)
    }
  }

  const loadClassImages = async () => {
    try {
      const response = await api.get<{ images: any[] }>(`/api/classes/${classId}/images`)
      setClassImages(response.images)
    } catch (error) {
      console.error('Error loading class images:', error)
    }
  }

  const handleUploadImages = async (files: File[]) => {
    setIsUploading(true)
    try {
      const formData = new FormData()
      files.forEach(file => formData.append('images', file))

      const response = await api.post<{ images: string[] }>(
        `/api/classes/${classId}/images`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      )

      setUploadedImages([...uploadedImages, ...response.images])
      await loadClassImages()
      await loadClass()
    } catch (error) {
      console.error('Error uploading images:', error)
      alert('Erro ao fazer upload das imagens')
    } finally {
      setIsUploading(false)
    }
  }

  const handleDeleteClass = async () => {
    if (!confirm('Tem certeza que deseja excluir esta classe?')) return

    try {
      await api.delete(`/api/classes/${classId}`)
      router.push('/dashboard/classes')
    } catch (error) {
      console.error('Error deleting class:', error)
      alert('Erro ao excluir classe')
    }
  }

  const handleDeleteImage = async (imageId: string) => {
    try {
      await api.delete(`/api/classes/${classId}/images/${imageId}`)
      await loadClassImages()
      await loadClass()
    } catch (error) {
      console.error('Error deleting image:', error)
      alert('Erro ao excluir imagem')
    }
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="text-center py-8 text-gray-500">Carregando...</div>
      </div>
    )
  }

  if (!cls) {
    return (
      <div className="p-6">
        <div className="text-center py-8 text-gray-500">Classe não encontrada</div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <button
        onClick={() => router.push('/dashboard/classes')}
        className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft size={20} />
        <span>Voltar para Classes</span>
      </button>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <div
              className="w-8 h-8 rounded"
              style={{ backgroundColor: cls.color }}
            />
            <div>
              <h1 className="text-2xl font-bold">{cls.display_name}</h1>
              <p className="text-gray-500">{cls.name}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              <Edit size={18} />
              <span>Editar</span>
            </button>
            <button
              onClick={handleDeleteClass}
              className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
            >
              <Trash2 size={18} />
              <span>Excluir</span>
            </button>
          </div>
        </div>

        {cls.description && (
          <div className="border-t pt-4">
            <h3 className="font-semibold mb-2">Descrição</h3>
            <p className="text-gray-600">{cls.description}</p>
          </div>
        )}

        <div className="border-t pt-4 mt-4">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-blue-600">{cls.images_count}</div>
              <div className="text-sm text-gray-500">Imagens</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">
                {classImages.filter(img => img.is_annotated).length}
              </div>
              <div className="text-sm text-gray-500">Anotadas</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-600">
                classImages.filter(img => !img.is_annotated).length
              </div>
              <div className="text-sm text-gray-500">Pendentes</div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-2 mb-4">
          <h2 className="text-xl font-bold">Upload de Imagens</h2>
        </div>
        <ImageUpload
          onUpload={handleUploadImages}
          images={uploadedImages}
          onRemove={(index) => {
            const newImages = [...uploadedImages]
            newImages.splice(index, 1)
            setUploadedImages(newImages)
          }}
        />
        {isUploading && (
          <div className="mt-2 text-sm text-blue-600">Fazendo upload...</div>
        )}
      </div>

      {classImages.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 mt-6">
          <h2 className="text-xl font-bold mb-4">
            Imagens ({classImages.length})
          </h2>
          <ImageGrid
            images={classImages}
            onAnnotate={(imageId) => {
              // TODO: Open annotation modal
              console.log('Annotate image:', imageId)
            }}
            onDelete={handleDeleteImage}
          />
        </div>
      )}

      <ClassFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => {
          loadClass()
        }}
        editingClass={cls}
      />
    </div>
  )
}
