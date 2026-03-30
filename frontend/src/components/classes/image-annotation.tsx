'use client'

import { useState, useRef, useEffect } from 'react'
import { Stage, Layer, Rect, Line, Text } from 'react-konva'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Save, Undo, Redo, ZoomIn, ZoomOut } from 'lucide-react'

interface BBox {
  x: number
  y: number
  width: number
  height: number
  classIndex: number
}

interface ImageAnnotationProps {
  imageUrl: string
  imageWidth: number
  imageHeight: number
  classIndex: number
  classes: Array<{ id: number; nome: string; cor_hex: string }>
  onSave: (annotations: string) => void
  onCancel: () => void
}

export function ImageAnnotation({
  imageUrl,
  imageWidth,
  imageHeight,
  classIndex,
  classes,
  onSave,
  onCancel
}: ImageAnnotationProps) {
  const [scale, setScale] = useState(1)
  const [bboxes, setBboxes] = useState<BBox[]>([])
  const [currentBBox, setCurrentBBox] = useState<Partial<BBox> | null>(null)
  const [isDrawing, setIsDrawing] = useState(false)
  const stageRef = useRef<Stage>(null)
  const [history, setHistory] = useState<BBox[][]>([])
  const [historyIndex, setHistoryIndex] = useState(0)

  // Calculate scale to fit container
  const containerWidth = 800
  const containerHeight = 600
  const scaleX = containerWidth / imageWidth
  const scaleY = containerHeight / imageHeight
  const displayScale = Math.min(scaleX, scaleY)

  const getMousePos = (e: any) => {
    const transform = stageRef.current?.getAbsoluteTransform().copy()
    return {
      x: (e.clientX - transform.x) / transform.scaleX,
      y: (e.clientY - transform.y) / transform.scaleY
    }
  }

  const handleMouseDown = (e: any) => {
    const pos = getMousePos(e)
    setCurrentBBox({
      x: pos.x,
      y: pos.y,
      width: 0,
      height: 0,
      classIndex
    })
    setIsDrawing(true)
  }

  const handleMouseMove = (e: any) => {
    if (!isDrawing || !currentBBox) return

    const pos = getMousePos(e)
    const width = pos.x - currentBBox.x
    const height = pos.y - currentBBox.y

    setCurrentBBox({
      ...currentBBox,
      width: Math.abs(width),
      height: Math.abs(height),
      x: width < 0 ? pos.x : currentBBox.x,
      y: height < 0 ? pos.y : currentBBox.y
    })
  }

  const handleMouseUp = () => {
    if (currentBBox && currentBBox.width > 5 && currentBBox.height > 5) {
      const newBBox = { ...currentBBox, classIndex } as BBox
      const newHistory = [...history.slice(0, historyIndex + 1), [...bboxes, newBBox]]
      setHistory(newHistory)
      setHistoryIndex(newHistory.length - 1)
      setBboxes([...bboxes, newBBox])
    }
    setIsDrawing(false)
    setCurrentBBox(null)
  }

  const undo = () => {
    if (historyIndex > 0) {
      setHistoryIndex(historyIndex - 1)
      setBboxes(history[historyIndex - 1])
    }
  }

  const redo = () => {
    if (historyIndex < history.length - 1) {
      setHistoryIndex(historyIndex + 1)
      setBboxes(history[historyIndex + 1])
    }
  }

  const deleteBBox = (index: number) => {
    const newBBoxes = bboxes.filter((_, i) => i !== index)
    const newHistory = [...history.slice(0, historyIndex + 1), newBBoxes]
    setHistory(newHistory)
    setHistoryIndex(newHistory.length - 1)
    setBboxes(newBBoxes)
  }

  const saveAnnotations = () => {
    // Convert bboxes to YOLO format
    const annotations = bboxes.map(bbox => {
      const centerX = (bbox.x + bbox.width / 2) / imageWidth
      const centerY = (bbox.y + bbox.height / 2) / imageHeight
      const width = bbox.width / imageWidth
      const height = bbox.height / imageHeight

      return `${bbox.classIndex} ${centerX.toFixed(6)} ${centerY.toFixed(6)} ${width.toFixed(6)} ${height.toFixed(6)}`
    }).join('\n')

    onSave(annotations)
  }

  const selectedClass = classes.find(c => c.id === classIndex)

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={undo}
                disabled={historyIndex === 0}
              >
                <Undo className="w-4 h-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={redo}
                disabled={historyIndex >= history.length - 1}
              >
                <Redo className="w-4 h-4" />
              </Button>
              <div className="h-6 w-px bg-gray-300" />
              <div
                className="px-2 py-1 rounded text-xs"
                style={{ backgroundColor: selectedClass?.cor_hex, color: 'white' }}
              >
                Classe: {selectedClass?.nome || 'N/A'}
              </div>
              <div className="text-xs text-muted-foreground">
                {bboxes.length} anotação{bboxes.length !== 1 ? 's' : ''}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={onCancel}>
                Cancelar
              </Button>
              <Button onClick={saveAnnotations} disabled={bboxes.length === 0}>
                <Save className="w-4 h-4 mr-2" />
                Salvar
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Canvas */}
      <Card>
        <CardContent className="p-4">
          <div
            className="border border-gray-300 rounded bg-gray-50 flex items-center justify-center"
            style={{ width: containerWidth, height: containerHeight }}
          >
            <Stage
              width={containerWidth}
              height={containerHeight}
              scaleX={displayScale}
              scaleY={displayScale}
              ref={stageRef}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
            >
              <Layer>
                {/* Image */}
                <image
                  url={imageUrl}
                  width={imageWidth}
                  height={imageHeight}
                />

                {/* Existing BBoxes */}
                {bboxes.map((bbox, index) => {
                  const cls = classes.find(c => c.id === bbox.classIndex)
                  return (
                    <Rect
                      key={index}
                      x={bbox.x}
                      y={bbox.y}
                      width={bbox.width}
                      height={bbox.height}
                      stroke={cls?.cor_hex || '#00FF00'}
                      strokeWidth={2}
                      fill={cls?.cor_hex || '#00FF00'}
                      opacity={0.2}
                      onClick={() => deleteBBox(index)}
                    />
                  )
                })}

                {/* Current BBox being drawn */}
                {currentBBox && (
                  <Rect
                    x={currentBBox.x}
                    y={currentBBox.y}
                    width={currentBBox.width}
                    height={currentBBox.height}
                    stroke={selectedClass?.cor_hex || '#00FF00'}
                    strokeWidth={2}
                    fill={selectedClass?.cor_hex || '#00FF00'}
                    opacity={0.2}
                  />
                )}
              </Layer>
            </Stage>
          </div>
        </CardContent>
      </Card>

      {/* Instructions */}
      <Card>
        <CardContent className="p-4">
          <h4 className="font-semibold mb-2">Instruções:</h4>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>• Arraste o mouse para desenhar um bounding box ao redor do objeto</li>
            <li>• Clique em uma caixa para excluí-la</li>
            <li>• Use Undo/Redo para corrigir anotações</li>
            <li>• Clique em Salvar para confirmar as anotações</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
