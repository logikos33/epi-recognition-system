'use client'

import { useRef, useEffect, useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { ZoomIn, ZoomOut, Maximize2, Undo, Trash2, Save, ChevronLeft, ChevronRight } from 'lucide-react'

/**
 * Bounding box in pixel coordinates
 */
export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
  class: string
  id?: string
}

interface AnnotationCanvasProps {
  imageUrl: string
  annotations: BoundingBox[]
  onAnnotationAdd: (bbox: BoundingBox) => void
  onAnnotationDelete: (index: number) => void
  onAnnotationUpdate?: (index: number, bbox: BoundingBox) => void
  targetClasses: string[]
  onSave?: () => void
  onNextFrame?: () => void
  onPreviousFrame?: () => void
  currentFrameNumber?: number
  totalFrames?: number
  loading?: boolean
}

/**
 * Manual annotation canvas for YOLO training
 * Features:
 * - Draw bounding boxes with mouse (click-drag-release)
 * - Edit existing boxes (select, move, resize)
 * - Delete boxes (Delete key or button)
 * - Zoom and pan support
 * - Class selector for each box
 * - Navigate between frames
 */
export function AnnotationCanvas({
  imageUrl,
  annotations,
  onAnnotationAdd,
  onAnnotationDelete,
  onAnnotationUpdate,
  targetClasses,
  onSave,
  onNextFrame,
  onPreviousFrame,
  currentFrameNumber,
  totalFrames,
  loading = false
}: AnnotationCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const imageRef = useRef<HTMLImageElement | null>(null)

  const [selectedClass, setSelectedClass] = useState(targetClasses[0] || '')
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDrawing, setIsDrawing] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [isPanning, setIsPanning] = useState(false)
  const [isResizing, setIsResizing] = useState(false)
  const [resizeHandle, setResizeHandle] = useState<string | null>(null)
  const [startPos, setStartPos] = useState({ x: 0, y: 0 })
  const [currentPos, setCurrentPos] = useState({ x: 0, y: 0 })
  const [selectedAnnotation, setSelectedAnnotation] = useState<number | null>(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })

  // Color palette for classes
  const getClassColor = (className: string): string => {
    const colors = [
      '#00ff00', '#ff0000', '#0000ff', '#ffff00', '#ff00ff',
      '#00ffff', '#ff8800', '#8800ff', '#00ff88', '#ff0088'
    ]
    const index = targetClasses.indexOf(className)
    return colors[index % colors.length]
  }

  // Load image
  useEffect(() => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      imageRef.current = img
      drawCanvas()
    }
    img.src = imageUrl
  }, [imageUrl])

  // Redraw canvas when annotations or state changes
  useEffect(() => {
    if (imageRef.current) {
      drawCanvas()
    }
  }, [annotations, isDrawing, currentPos, selectedAnnotation, zoom, pan])

  /**
   * Draw the canvas with image and annotations
   */
  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container || !imageRef.current) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const img = imageRef.current

    // Set canvas size to match container
    canvas.width = container.clientWidth
    canvas.height = container.clientHeight

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Apply transformations
    ctx.save()
    ctx.translate(pan.x, pan.y)
    ctx.scale(zoom, zoom)

    // Draw image centered
    const x = (canvas.width / zoom - img.width) / 2
    const y = (canvas.height / zoom - img.height) / 2
    ctx.drawImage(img, x, y)

    // Draw existing annotations
    annotations.forEach((anno, index) => {
      const isSelected = selectedAnnotation === index
      const color = getClassColor(anno.class)

      // Draw box
      ctx.strokeStyle = isSelected ? '#ffffff' : color
      ctx.lineWidth = isSelected ? 3 : 2
      ctx.setLineDash(isSelected ? [5, 5] : [])
      ctx.strokeRect(x + anno.x, y + anno.y, anno.width, anno.height)
      ctx.setLineDash([])

      // Draw fill for selected box
      if (isSelected) {
        ctx.fillStyle = color + '20' // 20 = low opacity
        ctx.fillRect(x + anno.x, y + anno.y, anno.width, anno.height)

        // Draw resize handles
        const handleSize = 8 / zoom
        ctx.fillStyle = '#ffffff'
        ctx.strokeStyle = color
        ctx.lineWidth = 2 / zoom

        const handles = [
          { x: anno.x, y: anno.y }, // top-left
          { x: anno.x + anno.width, y: anno.y }, // top-right
          { x: anno.x, y: anno.y + anno.height }, // bottom-left
          { x: anno.x + anno.width, y: anno.y + anno.height }, // bottom-right
          { x: anno.x + anno.width / 2, y: anno.y }, // top-center
          { x: anno.x + anno.width / 2, y: anno.y + anno.height }, // bottom-center
          { x: anno.x, y: anno.y + anno.height / 2 }, // left-center
          { x: anno.x + anno.width, y: anno.y + anno.height / 2 } // right-center
        ]

        handles.forEach(handle => {
          ctx.fillRect(
            x + handle.x - handleSize / 2,
            y + handle.y - handleSize / 2,
            handleSize,
            handleSize
          )
          ctx.strokeRect(
            x + handle.x - handleSize / 2,
            y + handle.y - handleSize / 2,
            handleSize,
            handleSize
          )
        })
      }

      // Draw label background
      const label = `${anno.class}`
      ctx.font = `${12 / zoom}px sans-serif`
      const textWidth = ctx.measureText(label).width
      ctx.fillStyle = color
      ctx.fillRect(x + anno.x, y + anno.y - 16 / zoom, textWidth + 8 / zoom, 16 / zoom)

      // Draw label text
      ctx.fillStyle = '#ffffff'
      ctx.fillText(label, x + anno.x + 4 / zoom, y + anno.y - 4 / zoom)
    })

    // Draw current drawing box
    if (isDrawing) {
      ctx.strokeStyle = '#ffff00'
      ctx.lineWidth = 2 / zoom
      ctx.setLineDash([5 / zoom, 5 / zoom])
      const width = currentPos.x - startPos.x
      const height = currentPos.y - startPos.y
      ctx.strokeRect(x + startPos.x, y + startPos.y, width, height)
      ctx.setLineDash([])
    }

    ctx.restore()
  }, [annotations, isDrawing, startPos, currentPos, selectedAnnotation, zoom, pan, targetClasses])

  /**
   * Get mouse position relative to image
   */
  const getMousePos = (e: React.MouseEvent<HTMLCanvasElement>): { x: number; y: number } => {
    const canvas = canvasRef.current
    if (!canvas || !imageRef.current) return { x: 0, y: 0 }

    const rect = canvas.getBoundingClientRect()
    const img = imageRef.current

    // Calculate image position (centered)
    const canvasX = (canvas.width / zoom - img.width) / 2
    const canvasY = (canvas.height / zoom - img.height) / 2

    return {
      x: (e.clientX - rect.left - pan.x) / zoom - canvasX,
      y: (e.clientY - rect.top - pan.y) / zoom - canvasY
    }
  }

  /**
   * Check if point is inside a box
   */
  const isInsideBox = (x: number, y: number, box: BoundingBox): boolean => {
    return x >= box.x && x <= box.x + box.width && y >= box.y && y <= box.y + box.height
  }

  /**
   * Check if point is on resize handle
   */
  const getResizeHandle = (x: number, y: number, box: BoundingBox): string | null => {
    const handleSize = 10

    // Check corners and edges
    if (Math.abs(x - box.x) < handleSize && Math.abs(y - box.y) < handleSize) return 'tl'
    if (Math.abs(x - (box.x + box.width)) < handleSize && Math.abs(y - box.y) < handleSize) return 'tr'
    if (Math.abs(x - box.x) < handleSize && Math.abs(y - (box.y + box.height)) < handleSize) return 'bl'
    if (Math.abs(x - (box.x + box.width)) < handleSize && Math.abs(y - (box.y + box.height)) < handleSize) return 'br'
    if (Math.abs(x - (box.x + box.width / 2)) < handleSize && Math.abs(y - box.y) < handleSize) return 'tc'
    if (Math.abs(x - (box.x + box.width / 2)) < handleSize && Math.abs(y - (box.y + box.height)) < handleSize) return 'bc'
    if (Math.abs(x - box.x) < handleSize && Math.abs(y - (box.y + box.height / 2)) < handleSize) return 'lc'
    if (Math.abs(x - (box.x + box.width)) < handleSize && Math.abs(y - (box.y + box.height / 2)) < handleSize) return 'rc'

    return null
  }

  /**
   * Handle mouse down
   */
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const pos = getMousePos(e)

    // Check if clicking on resize handle of selected box
    if (selectedAnnotation !== null) {
      const box = annotations[selectedAnnotation]
      const handle = getResizeHandle(pos.x, pos.y, box)
      if (handle) {
        setIsResizing(true)
        setResizeHandle(handle)
        setStartPos({ x: box.x, y: box.y, width: box.width, height: box.height } as any)
        setCurrentPos(pos)
        return
      }
    }

    // Check if clicking on existing box
    for (let i = annotations.length - 1; i >= 0; i--) {
      if (isInsideBox(pos.x, pos.y, annotations[i])) {
        setSelectedAnnotation(i)
        setIsDragging(true)
        setDragOffset({
          x: pos.x - annotations[i].x,
          y: pos.y - annotations[i].y
        })
        return
      }
    }

    // Start drawing new box
    if (e.button === 0) { // Left click
      setIsDrawing(true)
      setSelectedAnnotation(null)
      setStartPos(pos)
      setCurrentPos(pos)
    }
  }

  /**
   * Handle mouse move
   */
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const pos = getMousePos(e)

    if (isResizing && selectedAnnotation !== null && onAnnotationUpdate) {
      // Resize selected box
      const box = { ...annotations[selectedAnnotation] }
      const start = startPos as any

      switch (resizeHandle) {
        case 'tl':
          box.width = start.width + (start.x - pos.x)
          box.height = start.height + (start.y - pos.y)
          box.x = pos.x
          box.y = pos.y
          break
        case 'tr':
          box.width = pos.x - start.x
          box.height = start.height + (start.y - pos.y)
          box.y = pos.y
          break
        case 'bl':
          box.width = start.width + (start.x - pos.x)
          box.height = pos.y - start.y
          box.x = pos.x
          break
        case 'br':
          box.width = pos.x - start.x
          box.height = pos.y - start.y
          break
        case 'tc':
          box.height = start.height + (start.y - pos.y)
          box.y = pos.y
          break
        case 'bc':
          box.height = pos.y - start.y
          break
        case 'lc':
          box.width = start.width + (start.x - pos.x)
          box.x = pos.x
          break
        case 'rc':
          box.width = pos.x - start.x
          break
      }

      // Ensure minimum size
      if (box.width > 10 && box.height > 10) {
        onAnnotationUpdate(selectedAnnotation, box)
      }
    } else if (isDragging && selectedAnnotation !== null && onAnnotationUpdate) {
      // Move selected box
      const box = { ...annotations[selectedAnnotation] }
      box.x = pos.x - dragOffset.x
      box.y = pos.y - dragOffset.y

      // Clamp to image bounds
      if (!imageRef.current) return
      box.x = Math.max(0, Math.min(box.x, imageRef.current.width - box.width))
      box.y = Math.max(0, Math.min(box.y, imageRef.current.height - box.height))

      onAnnotationUpdate(selectedAnnotation, box)
    } else if (isDrawing) {
      setCurrentPos(pos)
    }
  }

  /**
   * Handle mouse up
   */
  const handleMouseUp = () => {
    if (isDrawing) {
      const width = currentPos.x - startPos.x
      const height = currentPos.y - startPos.y

      // Only add if box is large enough
      if (Math.abs(width) > 10 && Math.abs(height) > 10) {
        onAnnotationAdd({
          x: width > 0 ? startPos.x : currentPos.x,
          y: height > 0 ? startPos.y : currentPos.y,
          width: Math.abs(width),
          height: Math.abs(height),
          class: selectedClass
        })
      }
    }

    setIsDrawing(false)
    setIsDragging(false)
    setIsResizing(false)
    setResizeHandle(null)
  }

  /**
   * Handle mouse wheel for zooming
   */
  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault()

    if (e.ctrlKey || e.metaKey) {
      // Zoom
      const delta = e.deltaY > 0 ? -0.1 : 0.1
      setZoom(z => Math.max(0.5, Math.min(3, z + delta)))
    } else {
      // Pan
      setPan(p => ({
        x: p.x - e.deltaX,
        y: p.y - e.deltaY
      }))
    }
  }

  /**
   * Handle keyboard shortcuts
   */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedAnnotation !== null && !e.shiftKey && document.activeElement?.tagName !== 'INPUT') {
          e.preventDefault()
          onAnnotationDelete(selectedAnnotation)
          setSelectedAnnotation(null)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedAnnotation, onAnnotationDelete])

  /**
   * Delete selected annotation
   */
  const handleDeleteSelected = () => {
    if (selectedAnnotation !== null) {
      onAnnotationDelete(selectedAnnotation)
      setSelectedAnnotation(null)
    }
  }

  /**
   * Reset zoom and pan
   */
  const handleResetView = () => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Class Selector */}
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Classe:</label>
          <select
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            className="flex h-10 w-48 rounded-md border border-input bg-background px-3 py-2 text-sm"
            disabled={loading}
          >
            {targetClasses.map(cls => (
              <option key={cls} value={cls}>{cls}</option>
            ))}
          </select>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setZoom(z => Math.max(0.5, z - 0.25))}
            disabled={loading}
            title="Diminuir zoom"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={handleResetView}
            disabled={loading}
            title="Resetar visualização"
          >
            <Maximize2 className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setZoom(z => Math.min(3, z + 0.25))}
            disabled={loading}
            title="Aumentar zoom"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          <span className="text-xs text-muted-foreground w-12 text-center">
            {Math.round(zoom * 100)}%
          </span>
        </div>

        {/* Frame Navigation */}
        {(onPreviousFrame || onNextFrame) && (
          <div className="flex items-center gap-1 border-l pl-4">
            <Button
              variant="outline"
              size="icon"
              onClick={onPreviousFrame}
              disabled={loading || currentFrameNumber === 0}
              title="Quadro anterior"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm text-muted-foreground px-2">
              {currentFrameNumber! + 1} / {totalFrames}
            </span>
            <Button
              variant="outline"
              size="icon"
              onClick={onNextFrame}
              disabled={loading || currentFrameNumber! >= totalFrames! - 1}
              title="Próximo quadro"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-1 border-l pl-4 ml-auto">
          {selectedAnnotation !== null && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleDeleteSelected}
              disabled={loading}
              className="text-destructive"
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Excluir
            </Button>
          )}
          {onSave && (
            <Button
              variant="default"
              size="sm"
              onClick={onSave}
              disabled={loading}
            >
              <Save className="h-4 w-4 mr-1" />
              Salvar
            </Button>
          )}
        </div>
      </div>

      {/* Canvas Container */}
      <Card>
        <CardContent className="p-0">
          <div
            ref={containerRef}
            className="relative w-full h-[600px] bg-muted rounded-lg overflow-hidden"
          >
            {loading ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <p className="text-muted-foreground">Carregando imagem...</p>
              </div>
            ) : (
              <canvas
                ref={canvasRef}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onWheel={handleWheel}
                className="w-full h-full cursor-crosshair"
                style={{ cursor: isDrawing ? 'crosshair' : 'default' }}
              />
            )}

            {/* Instructions overlay */}
            {annotations.length === 0 && !isDrawing && !loading && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="text-center p-6 bg-background/80 backdrop-blur rounded-lg">
                  <p className="text-sm font-medium mb-2">Como anotar:</p>
                  <ul className="text-xs text-muted-foreground space-y-1 text-left">
                    <li>• Clique e arraste para desenhar caixas delimitadoras</li>
                    <li>• Selecione uma classe antes de desenhar</li>
                    <li>• Clique em uma caixa para selecioná-la</li>
                    <li>• Arraste para mover, use alças para redimensionar</li>
                    <li>• Pressione Delete para excluir a seleção</li>
                    <li>• Use Ctrl + roda do mouse para zoom</li>
                  </ul>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Annotations List */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium">
                Anotações ({annotations.length})
              </h3>
              {annotations.length > 0 && (
                <Badge variant="secondary">
                  {targetClasses.join(', ')}
                </Badge>
              )}
            </div>

            {annotations.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                Nenhuma anotação ainda. Desenhe caixas na imagem acima.
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {annotations.map((anno, index) => (
                  <div
                    key={index}
                    className={`flex items-center justify-between p-2 border rounded cursor-pointer transition-colors ${
                      selectedAnnotation === index
                        ? 'border-primary bg-primary/10'
                        : 'hover:bg-muted/50'
                    }`}
                    onClick={() => setSelectedAnnotation(index)}
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <div
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: getClassColor(anno.class) }}
                      />
                      <span className="text-sm font-medium truncate">{anno.class}</span>
                      <span className="text-xs text-muted-foreground">
                        {Math.round(anno.width)}×{Math.round(anno.height)}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 flex-shrink-0"
                      onClick={(e) => {
                        e.stopPropagation()
                        onAnnotationDelete(index)
                        if (selectedAnnotation === index) {
                          setSelectedAnnotation(null)
                        }
                      }}
                    >
                      <Trash2 className="h-3 w-3 text-destructive" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
