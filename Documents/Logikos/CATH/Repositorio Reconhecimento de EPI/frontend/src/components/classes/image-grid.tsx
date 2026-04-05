'use client'

import { useState } from 'react'
import { Image as ImageIcon, Edit } from 'lucide-react'

interface ImageGridProps {
  images: any[]
  onAnnotate: (imageId: string) => void
  onDelete: (imageId: string) => void
}

export function ImageGrid({ images, onAnnotate, onDelete }: ImageGridProps) {
  const [selectedImages, setSelectedImages] = useState<Set<string>>(new Set())

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedImages)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedImages(newSelected)
  }

  const toggleSelectAll = () => {
    if (selectedImages.size === images.length) {
      setSelectedImages(new Set())
    } else {
      setSelectedImages(new Set(images.map(img => img.id)))
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">
          {images.length} {images.length === 1 ? 'imagem' : 'imagens'}
        </h3>
        <button
          onClick={toggleSelectAll}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          {selectedImages.size === images.length ? 'Desmarcar todas' : 'Selecionar todas'}
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {images.map((image) => (
          <div
            key={image.id}
            className={`relative group aspect-square rounded-lg border-2 overflow-hidden cursor-pointer transition-all ${
              selectedImages.has(image.id)
                ? 'border-blue-500 ring-2 ring-blue-500 ring-opacity-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => toggleSelect(image.id)}
          >
            {image.url ? (
              <img
                src={image.url}
                alt={image.filename || 'Imagem'}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full bg-gray-100 flex items-center justify-center">
                <ImageIcon className="text-gray-400" size={32} />
              </div>
            )}

            <div className="absolute top-0 left-0 p-1">
              <input
                type="checkbox"
                checked={selectedImages.has(image.id)}
                onChange={() => toggleSelect(image.id)}
                className="w-4 h-4"
                onClick={(e) => e.stopPropagation()}
              />
            </div>

            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-opacity flex items-center justify-center">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onAnnotate(image.id)
                }}
                className="opacity-0 group-hover:opacity-100 bg-white px-3 py-1 rounded-md shadow-lg text-sm font-medium flex items-center space-x-1"
              >
                <Edit size={16} />
                <span>Anotar</span>
              </button>
            </div>

            {image.annotation_count > 0 && (
              <div className="absolute bottom-0 right-0 bg-green-500 text-white text-xs px-2 py-1 rounded-tl-md">
                {image.annotation_count}
              </div>
            )}

            {image.is_annotated && (
              <div className="absolute top-0 right-0 bg-blue-500 text-white text-xs px-2 py-1 rounded-bl-md">
                Pronta
              </div>
            )}
          </div>
        ))}
      </div>

      {selectedImages.size > 0 && (
        <div className="flex justify-end space-x-2 p-4 bg-gray-50 rounded-lg">
          <span className="text-sm text-gray-600 self-center">
            {selectedImages.size} {selectedImages.size === 1 ? 'imagem selecionada' : 'imagens selecionadas'}
          </span>
          <button
            onClick={() => {
              if (confirm(`Excluir ${selectedImages.size} imagens?`)) {
                selectedImages.forEach(id => onDelete(id))
                setSelectedImages(new Set())
              }
            }}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm"
          >
            Excluir Selecionadas
          </button>
        </div>
      )}
    </div>
  )
}
