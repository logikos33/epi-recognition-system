'use client'

import { useState, useEffect } from 'react'
import { Plus, Edit, Trash2, Upload, Download } from 'lucide-react'
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

export default function ClassesPage() {
  const [classes, setClasses] = useState<YOLOClass[]>([])
  const [selectedClass, setSelectedClass] = useState<YOLOClass | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingClass, setEditingClass] = useState<YOLOClass | null>(null)
  const [uploadedImages, setUploadedImages] = useState<string[]>([])
  const [classImages, setClassImages] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)

  useEffect(() => {
    loadClasses()
  }, [])

  const loadClasses = async () => {
    try {
      setIsLoading(true)
      const response = await api.get<{ classes: YOLOClass[] }>('/api/classes')
      setClasses(response.classes)
    } catch (error) {
      console.error('Error loading classes:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleUploadImages = async (files: File[]) => {
    if (!selectedClass) return

    setIsUploading(true)
    try {
      const formData = new FormData()
      files.forEach(file => formData.append('images', file))

      const response = await api.post<{ images: string[] }>(
        `/api/classes/${selectedClass.id}/images`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      )

      setUploadedImages([...uploadedImages, ...response.images])
      await loadClassImages(selectedClass.id)
      await loadClasses()
    } catch (error) {
      console.error('Error uploading images:', error)
      alert('Erro ao fazer upload das imagens')
    } finally {
      setIsUploading(false)
    }
  }

  const loadClassImages = async (classId: string) => {
    try {
      const response = await api.get<{ images: any[] }>(`/api/classes/${classId}/images`)
      setClassImages(response.images)
    } catch (error) {
      console.error('Error loading class images:', error)
    }
  }

  const handleSelectClass = async (cls: YOLOClass) => {
    setSelectedClass(cls)
    await loadClassImages(cls.id)
    setUploadedImages([])
  }

  const handleDeleteClass = async (id: string) => {
    if (!confirm('Tem certeza que deseja excluir esta classe?')) return

    try {
      await api.delete(`/api/classes/${id}`)
      await loadClasses()
      if (selectedClass?.id === id) {
        setSelectedClass(null)
        setClassImages([])
      }
    } catch (error) {
      console.error('Error deleting class:', error)
      alert('Erro ao excluir classe')
    }
  }

  const handleDeleteImage = async (imageId: string) => {
    try {
      await api.delete(`/api/classes/${selectedClass?.id}/images/${imageId}`)
      await loadClassImages(selectedClass?.id || '')
      await loadClasses()
    } catch (error) {
      console.error('Error deleting image:', error)
      alert('Erro ao excluir imagem')
    }
  }

  const handleExportDataset = async () => {
    try {
      const response = await api.get('/api/training/export-dataset')
      window.open(response.download_url, '_blank')
    } catch (error) {
      console.error('Error exporting dataset:', error)
      alert('Erro ao exportar dataset')
    }
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Classes YOLO</h1>
        <button
          onClick={() => {
            setEditingClass(null)
            setIsModalOpen(true)
          }}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          <Plus size={20} />
          <span>Nova Classe</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Classes List */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">Classes</h2>
          {isLoading ? (
            <div className="text-center py-8 text-gray-500">Carregando...</div>
          ) : classes.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              Nenhuma classe cadastrada
            </div>
          ) : (
            <div className="space-y-2">
              {classes.map((cls) => (
                <div
                  key={cls.id}
                  className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                    selectedClass?.id === cls.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => handleSelectClass(cls)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div
                        className="w-4 h-4 rounded"
                        style={{ backgroundColor: cls.color }}
                      />
                      <div>
                        <div className="font-medium">{cls.display_name}</div>
                        <div className="text-sm text-gray-500">{cls.name}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-500">
                        {cls.images_count} imgs
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditingClass(cls)
                          setIsModalOpen(true)
                        }}
                        className="p-1 hover:bg-gray-100 rounded"
                      >
                        <Edit size={16} />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteClass(cls.id)
                        }}
                        className="p-1 hover:bg-red-100 rounded text-red-600"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Class Details */}
        <div className="lg:col-span-2 space-y-6">
          {selectedClass ? (
            <>
              <div className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div
                      className="w-6 h-6 rounded"
                      style={{ backgroundColor: selectedClass.color }}
                    />
                    <div>
                      <h2 className="text-xl font-bold">{selectedClass.display_name}</h2>
                      <p className="text-sm text-gray-500">{selectedClass.name}</p>
                    </div>
                  </div>
                </div>

                {selectedClass.description && (
                  <p className="text-gray-600 mb-4">{selectedClass.description}</p>
                )}

                <div className="border-t pt-4">
                  <div className="flex items-center space-x-2 mb-4">
                    <Upload size={20} />
                    <h3 className="font-semibold">Upload de Imagens</h3>
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
                    <div className="mt-2 text-sm text-blue-600">
                      Fazendo upload...
                    </div>
                  )}
                </div>
              </div>

              {classImages.length > 0 && (
                <div className="bg-white rounded-lg shadow p-4">
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
            </>
          ) : (
            <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
              Selecione uma classe para ver detalhes
            </div>
          )}
        </div>
      </div>

      <ClassFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={loadClasses}
        editingClass={editingClass}
      />
    </div>
  )
}
