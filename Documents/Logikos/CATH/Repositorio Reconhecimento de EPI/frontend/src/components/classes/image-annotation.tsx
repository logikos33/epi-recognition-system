'use client'

import { useState, useRef, useEffect } from 'react'
import { Stage, Layer, Rect, Transformer } from 'react-konva'
import { X, Save, Trash2 } from 'lucide-react'

interface Annotation {
  id: string
  x: number
  y: number
  width: number
  height: number
  classId: string
}

interface ImageAnnotationProps {
  imageUrl: string
  annotations: Annotation[]
  classes: any[]
  onUpdateAnnotations: (annotations: Annotation[]) => void
  onClose: () => void
  onSave: () => void
}

export function ImageAnnotation({
  imageUrl,
  annotations,
  classes,
  onUpdateAnnotations,
  onClose,
  onSave
}: ImageAnnotationProps) {
  const [image] = useState<HTMLImageElement | null>(null)
  const [stageSize, setStageSize] = useState({ width: 800, height: 600 })
  const [selectedId, selectShape] = useState<string | null>(null)
  const [newBox, setNewBox] = useState<any>(null)
  const [isDrawing, setIsDrawing] = useState(false)
  const [selectedClassId, setSelectedClassId] = useState(classes[0]?.id || '')
  const imageRef = useRef<HTMLImageElement>(null)
  const stageRef = useRef<any>(null)
  const transformerRef = useRef<any>(null)

  useEffect(() => {
    const img = new window.Image()
    img.src = imageUrl
    img.onload = () => {
      const maxWidth = 800
      const maxHeight = 600
      let width = img.width
      let height = img.height

      if (width > maxWidth) {
        height = (maxWidth / width) * height
        width = maxWidth
      }
      if (height > maxHeight) {
        width = (maxHeight / height) * width
        height = maxHeight
      }

      setStageSize({ width, height })
    }
    imageRef.current = img
  }, [imageUrl])

  useEffect(() => {
    if (selectedId && transformerRef.current) {
      transformerRef.current.nodes([stageRef.current?.findOne(`#${selectedId}`)])
      transformerRef.current.getLayer().batchDraw()
    }
  }, [selectedId])

  const handleMouseDown = (e: any) => {
    if (selectedId) {
      selectShape(null)
      return
    }

    const pos = e.target.getStage().getPointerPosition()
    setNewBox({
      id: Date.now().toString(),
      x: pos.x,
      y: pos.y,
      width: 0,
      height: 0,
      classId: selectedClassId
    })
    setIsDrawing(true)
  }

  const handleMouseMove = (e: any) => {
    if (!isDrawing || !newBox) return

    const pos = e.target.getStage().getPointerPosition()
    setNewBox({
      ...newBox,
      width: pos.x - newBox.x,
      height: pos.y - newBox.y
    })
  }

  const handleMouseUp = () => {
    if (!isDrawing || !newBox) return

    if (Math.abs(newBox.width) > 10 && Math.abs(newBox.height) > 10) {
      const normalizedBox = {
        ...newBox,
        x: newBox.width > 0 ? newBox.x : newBox.x + newBox.width,
        y: newBox.height > 0 ? newBox.y : newBox.y + newBox.height,
        width: Math.abs(newBox.width),
        height: Math.abs(newBox.height)
      }
      onUpdateAnnotations([...annotations, normalizedBox])
    }

    setIsDrawing(false)
    setNewBox(null)
  }

  const handleDelete = () => {
    if (selectedId) {
      onUpdateAnnotations(annotations.filter(a => a.id !== selectedId))
      selectShape(null)
    }
  }

  const getClassColor = (classId: string) => {
    const cls = classes.find(c => c.id === classId)
    return cls?.color || '#FF0000'
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-auto">
        <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-semibold">Anotar Imagem</h2>
            <select
              value={selectedClassId}
              onChange={(e) => setSelectedClassId(e.target.value)}
              className="px-3 py-1 border border-gray-300 rounded-md"
            >
              {classes.map((cls) => (
                <option key={cls.id} value={cls.id}>
                  {cls.display_name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleDelete}
              disabled={!selectedId}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center space-x-2"
            >
              <Trash2 size={18} />
              <span>Excluir</span>
            </button>
            <button
              onClick={onSave}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 flex items-center space-x-2"
            >
              <Save size={18} />
              <span>Salvar</span>
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        <div className="p-4">
          <div className="bg-gray-100 rounded-lg p-4 flex justify-center">
            <Stage
              width={stageSize.width}
              height={stageSize.height}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              ref={stageRef}
            >
              <Layer>
                {image && (
                  <Rect
                    width={stageSize.width}
                    height={stageSize.height}
                    fillPatternImage={image}
                  />
                )}
                {annotations.map((annotation) => (
                  <Rect
                    key={annotation.id}
                    id={annotation.id}
                    x={annotation.x}
                    y={annotation.y}
                    width={annotation.width}
                    height={annotation.height}
                    stroke={getClassColor(annotation.classId)}
                    strokeWidth={2}
                    fill={getClassColor(annotation.classId) + '20'}
                    onClick={() => selectShape(annotation.id)}
                    draggable
                    onDragEnd={(e) => {
                      const newAnnotations = annotations.map(a =>
                        a.id === annotation.id
                          ? { ...a, x: e.target.x(), y: e.target.y() }
                          : a
                      )
                      onUpdateAnnotations(newAnnotations)
                    }}
                    onTransformEnd={(e) => {
                      const node = e.target
                      const scaleX = node.scaleX()
                      const scaleY = node.scaleY()

                      const newAnnotations = annotations.map(a =>
                        a.id === annotation.id
                          ? {
                              ...a,
                              x: node.x(),
                              y: node.y(),
                              width: node.width() * scaleX,
                              height: node.height() * scaleY
                            }
                          : a
                      )
                      onUpdateAnnotations(newAnnotations)
                    }}
                  />
                ))}
                {newBox && (
                  <Rect
                    x={newBox.x}
                    y={newBox.y}
                    width={newBox.width}
                    height={newBox.height}
                    stroke={getClassColor(newBox.classId)}
                    strokeWidth={2}
                    fill={getClassColor(newBox.classId) + '20'}
                  />
                )}
                <Transformer
                  ref={transformerRef}
                  boundBoxFunc={(oldBox, newBox) => {
                    if (newBox.width < 10 || newBox.height < 10) return oldBox
                    return newBox
                  }}
                />
              </Layer>
            </Stage>
          </div>

          <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
            {classes.map((cls) => (
              <div
                key={cls.id}
                className="flex items-center space-x-2 p-2 border rounded-md"
              >
                <div
                  className="w-4 h-4 rounded"
                  style={{ backgroundColor: cls.color }}
                />
                <span className="text-sm">{cls.display_name}</span>
                <span className="text-xs text-gray-500 ml-auto">
                  {annotations.filter(a => a.classId === cls.id).length}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
