'use client'

import { useState, useEffect, useRef, useCallback } from 'react'

// Types
interface BoundingBox {
  id: string
  class_id: number
  class_name: string
  x_center: number  // 0-1 normalized
  y_center: number  // 0-1 normalized
  width: number     // 0-1 normalized
  height: number    // 0-1 normalized
  confidence?: number
  is_suggestion?: boolean
}

interface Frame {
  id: string
  frame_number: number
  storage_path: string
  is_annotated: boolean
  annotation_count: number
  created_at: string
}

interface TrainingClass {
  id: number
  name: string
  color: string
}

const DEFAULT_CLASSES: TrainingClass[] = [
  { id: 1, name: 'Produto', color: '#22c55e' },
  { id: 2, name: 'Caminhão', color: '#f59e0b' },
  { id: 3, name: 'Placa', color: '#3b82f6' },
  { id: 4, name: 'Capacete', color: '#8b5cf6' },
  { id: 5, name: 'Colete', color: '#ec4899' },
  { id: 6, name: 'Sem EPI', color: '#ef4444' },
]

type ToolMode = 'draw' | 'select' | 'delete'

export function AnnotationInterface({ videoId, onBack }: { videoId: string, onBack: () => void }) {
  // Early return if no videoId
  if (!videoId) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: 'calc(100vh - 100px)',
        background: '#0d1117',
        color: 'rgba(255, 255, 255, 0.5)',
        fontSize: '14px'
      }}>
        Nenhum vídeo selecionado
      </div>
    )
  }

  // Frame management
  const [frames, setFrames] = useState<Frame[]>([])
  const [selectedFrame, setSelectedFrame] = useState<Frame | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Annotations
  const [annotations, setAnnotations] = useState<BoundingBox[]>([])
  const [selectedAnnotation, setSelectedAnnotation] = useState<string | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  // Helper to update annotations and mark as unsaved
  const updateAnnotations = (newAnnotations: BoundingBox[] | ((prev: BoundingBox[]) => BoundingBox[])) => {
    setAnnotations(newAnnotations)
    setHasUnsavedChanges(true)
  }

  // Tools
  const [toolMode, setToolMode] = useState<ToolMode>('draw')
  const [activeClass, setActiveClass] = useState<TrainingClass>(DEFAULT_CLASSES[0])
  const [classes, setClasses] = useState<TrainingClass[]>(DEFAULT_CLASSES)

  // Drawing state
  const [isDrawing, setIsDrawing] = useState(false)
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null)
  const [drawEnd, setDrawEnd] = useState<{ x: number; y: number } | null>(null)

  // Auto-detect
  const [detecting, setDetecting] = useState(false)
  const [suggestions, setSuggestions] = useState<BoundingBox[]>([])

  // Image container
  const imageContainerRef = useRef<HTMLDivElement>(null)
  const timelineRef = useRef<HTMLDivElement>(null)

  // Load frames on mount
  useEffect(() => {
    loadFrames()
    loadClasses()
  }, [videoId])

  // Load annotations when frame changes - COM DEBOUNCE
  useEffect(() => {
    if (!selectedFrame) return

    // Debounce: esperar 300ms após última mudança antes de carregar
    const timer = setTimeout(() => {
      loadAnnotations(selectedFrame.id)
      setSuggestions([]) // Clear suggestions on frame change
    }, 300)

    return () => clearTimeout(timer)  // Limpar timer se mudar novamente
  }, [selectedFrame])

  // Scroll selected frame into view
  useEffect(() => {
    if (selectedFrame && timelineRef.current) {
      const timeline = timelineRef.current
      const selectedElement = timeline.querySelector(`[data-frame-id="${selectedFrame.id}"]`) as HTMLElement
      if (selectedElement) {
        selectedElement.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
      }
    }
  }, [selectedFrame])

  const loadFrames = async () => {
    if (!videoId) return

    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/training/videos/${videoId}/frames`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      const result = await response.json()
      if (result.success && result.frames) {
        setFrames(result.frames || [])  // Fallback para array vazio
        if (result.frames && result.frames.length > 0) {
          setSelectedFrame(result.frames[0])
        }
      } else {
        setFrames([])  // Garantir array vazio em caso de erro
      }
    } catch (error) {
      console.error('Error loading frames:', error)
      setFrames([])  // Garantir array vazio em caso de erro
    } finally {
      setLoading(false)
    }
  }

  const loadClasses = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/classes', {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      const result = await response.json()
      if (result.success && result.classes && result.classes.length > 0) {
        setClasses(result.classes)
        setActiveClass(result.classes[0])
      }
    } catch (error) {
      console.error('Using default classes')
    }
  }

  const loadAnnotations = async (frameId: string) => {
    if (!frameId) return

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/training/frames/${frameId}/annotations`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      // Tratar erros HTTP sem loggar (evitar flood do console)
      if (!response.ok) {
        setAnnotations([])
        setHasUnsavedChanges(false)
        return
      }

      const result = await response.json()
      if (result.success && result.annotations) {
        setAnnotations(result.annotations)
        setHasUnsavedChanges(false)  // Reset when loading existing annotations
      } else {
        setAnnotations([])
        setHasUnsavedChanges(false)
      }
    } catch (error) {
      // Silencioso - não logar erros de network/backend
      setAnnotations([])
      setHasUnsavedChanges(false)
    }
  }

  const saveAnnotations = async (frameId: string, annotationsToSave: BoundingBox[]) => {
    setSaving(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/training/frames/${frameId}/annotations`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ annotations: annotationsToSave })
      })

      const result = await response.json()
      if (result.success) {
        // Update frame annotation status
        setFrames(prev => prev.map(f =>
          f.id === frameId ? { ...f, is_annotated: true } : f
        ))
        setHasUnsavedChanges(false)  // Reset unsaved flag
        console.log('✓ Saved')
      }
    } catch (error) {
      console.error('Error saving annotations:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleFrameChange = (newFrame: Frame) => {
    // REMOVIDO: Auto-save ao trocar de frame (causava excesso de requests)
    // Agora o usuário deve clicar no botão "Salvar" manualmente
    setSelectedFrame(newFrame)
  }

  const handlePrevFrame = () => {
    if (!selectedFrame || !frames || frames.length === 0) return
    const currentIndex = frames.findIndex(f => f.id === selectedFrame.id)
    if (currentIndex > 0) {
      handleFrameChange(frames[currentIndex - 1])
    }
  }

  const handleNextFrame = () => {
    if (!selectedFrame || !frames || frames.length === 0) return
    const currentIndex = frames.findIndex(f => f.id === selectedFrame.id)
    if (currentIndex < frames.length - 1) {
      handleFrameChange(frames[currentIndex + 1])
    }
  }

  const handleAutoDetect = async () => {
    if (!selectedFrame) return

    setDetecting(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/training/frames/${selectedFrame.id}/predict`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      const result = await response.json()
      if (result.success && result.predictions) {
        const suggestionsWithIds = result.predictions.map((p: any, i: number) => ({
          id: `suggestion-${i}`,
          class_id: p.class_id,
          class_name: p.class_name || classes.find(c => c.id === p.class_id)?.name || 'Unknown',
          x_center: p.x_center,
          y_center: p.y_center,
          width: p.width,
          height: p.height,
          confidence: p.confidence,
          is_suggestion: true
        }))
        setSuggestions(suggestionsWithIds)
      }
    } catch (error) {
      console.error('Error running auto-detect:', error)
    } finally {
      setDetecting(false)
    }
  }

  const confirmSuggestion = (suggestion: BoundingBox) => {
    const confirmed = { ...suggestion, id: `annotation-${Date.now()}`, is_suggestion: false }
    updateAnnotations(prev => [...prev, confirmed])
    setSuggestions(prev => prev.filter(s => s.id !== suggestion.id))
  }

  const confirmAllSuggestions = () => {
    const confirmed = suggestions.map(s => ({
      ...s,
      id: `annotation-${Date.now()}-${Math.random()}`,
      is_suggestion: false
    }))
    updateAnnotations(prev => [...prev, ...confirmed])
    setSuggestions([])
  }

  const discardAllSuggestions = () => {
    setSuggestions([])
  }

  // Mouse handlers for drawing
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (toolMode !== 'draw' || !imageContainerRef.current) return

    const rect = imageContainerRef.current.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width
    const y = (e.clientY - rect.top) / rect.height

    setIsDrawing(true)
    setDrawStart({ x, y })
    setDrawEnd({ x, y })
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDrawing || !imageContainerRef.current) return

    const rect = imageContainerRef.current.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width
    const y = (e.clientY - rect.top) / rect.height

    setDrawEnd({ x, y })
  }

  const handleMouseUp = () => {
    if (!isDrawing || !drawStart || !drawEnd) return

    const x_center = (drawStart.x + drawEnd.x) / 2
    const y_center = (drawStart.y + drawEnd.y) / 2
    const width = Math.abs(drawEnd.x - drawStart.x)
    const height = Math.abs(drawEnd.y - drawStart.y)

    // Only add if box is large enough (5% minimum)
    if (width > 0.05 && height > 0.05) {
      const newAnnotation: BoundingBox = {
        id: `annotation-${Date.now()}`,
        class_id: activeClass.id,
        class_name: activeClass.name,
        x_center,
        y_center,
        width,
        height
      }
      updateAnnotations(prev => [...prev, newAnnotation])
    }

    setIsDrawing(false)
    setDrawStart(null)
    setDrawEnd(null)
  }

  const handleAnnotationClick = (annotationId: string, e: React.MouseEvent) => {
    e.stopPropagation()

    if (toolMode === 'delete') {
      updateAnnotations(prev => prev.filter(a => a.id !== annotationId))
      setSelectedAnnotation(null)
    } else if (toolMode === 'select') {
      setSelectedAnnotation(annotationId)
    }
  }

  const handleBackgroundClick = () => {
    if (toolMode === 'select') {
      setSelectedAnnotation(null)
    }
  }

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        handlePrevFrame()
      } else if (e.key === 'ArrowRight') {
        handleNextFrame()
      } else if (e.key >= '1' && e.key <= '9') {
        const classIndex = parseInt(e.key) - 1
        if (classIndex < classes.length) {
          setActiveClass(classes[classIndex])
          setToolMode('draw')
        }
      } else if ((e.key === 'Delete' || e.key === 'Backspace') && selectedAnnotation) {
        updateAnnotations(prev => prev.filter(a => a.id !== selectedAnnotation))
        setSelectedAnnotation(null)
      } else if (e.key === ' ') {
        e.preventDefault()
        setToolMode(prev => prev === 'draw' ? 'select' : 'draw')
      } else if (e.key === 'Escape') {
        setSelectedAnnotation(null)
        setIsDrawing(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedFrame, frames, classes, selectedAnnotation, toolMode])

  // Render bounding boxes on image
  const renderBoundingBoxes = () => {
    const container = imageContainerRef.current
    if (!container) return null

    const rect = container.getBoundingClientRect()
    const allBoxes = [...annotations, ...suggestions]

    return allBoxes.map(box => {
      const left = (box.x_center - box.width / 2) * 100
      const top = (box.y_center - box.height / 2) * 100
      const width = box.width * 100
      const height = box.height * 100
      const classColor = classes.find(c => c.id === box.class_id)?.color || '#ffffff'
      const isSelected = selectedAnnotation === box.id

      return (
        <div
          key={box.id}
          onClick={(e) => handleAnnotationClick(box.id, e)}
          style={{
            position: 'absolute',
            left: `${left}%`,
            top: `${top}%`,
            width: `${width}%`,
            height: `${height}%`,
            border: box.is_suggestion
              ? `2px dashed ${classColor}`
              : `2px solid ${isSelected ? '#ffffff' : classColor}`,
            backgroundColor: box.is_suggestion
              ? `${classColor}20`
              : isSelected
                ? `${classColor}30`
                : 'transparent',
            cursor: toolMode === 'delete' ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s',
            zIndex: isSelected ? 10 : 1
          }}
        >
          {/* Label */}
          <div style={{
            position: 'absolute',
            top: '-16px',
            left: '-2px',
            backgroundColor: classColor,
            color: '#fff',
            fontSize: '10px',
            padding: '1px 4px',
            borderRadius: '2px',
            whiteSpace: 'nowrap'
          }}>
            {box.class_name}
            {box.confidence && ` ${Math.round(box.confidence * 100)}%`}
          </div>
        </div>
      )
    })
  }

  // Render drawing preview
  const renderDrawingPreview = () => {
    if (!isDrawing || !drawStart || !drawEnd) return null

    const left = Math.min(drawStart.x, drawEnd.x) * 100
    const top = Math.min(drawStart.y, drawEnd.y) * 100
    const width = Math.abs(drawEnd.x - drawStart.x) * 100
    const height = Math.abs(drawEnd.y - drawStart.y) * 100

    return (
      <div style={{
        position: 'absolute',
        left: `${left}%`,
        top: `${top}%`,
        width: `${width}%`,
        height: `${height}%`,
        border: '2px dashed #2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.1)',
        pointerEvents: 'none',
        zIndex: 20
      }} />
    )
  }

  const formatTimestamp = (frameNumber: number, fps: number = 1) => {
    const seconds = Math.floor(frameNumber / fps)
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const currentFrameIndex = selectedFrame && frames ? frames.findIndex(f => f.id === selectedFrame.id) : -1

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 100px)',
      background: '#0d1117'
    }}>
      {/* A) Header */}
      <div style={{
        background: '#161b22',
        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
        padding: '12px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <button
          onClick={onBack}
          style={{
            padding: '8px 16px',
            background: 'transparent',
            color: 'rgba(255, 255, 255, 0.7)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '6px',
            fontSize: '13px',
            cursor: 'pointer',
            transition: 'all 0.15s'
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
        >
          ← Voltar
        </button>

        <h2 style={{
          fontSize: '16px',
          fontWeight: '600',
          color: '#fff',
          margin: 0
        }}>
          Anotação de Frames — Vídeo {videoId ? videoId.slice(0, 8) : 'Unknown'}
        </h2>

        <button
          onClick={() => selectedFrame && saveAnnotations(selectedFrame.id, annotations.filter(a => !a.is_suggestion))}
          disabled={saving}
          style={{
            padding: '8px 16px',
            background: hasUnsavedChanges ? 'rgba(245, 158, 11, 0.9)' : 'rgba(37, 99, 235, 0.8)',
            color: '#fff',
            border: hasUnsavedChanges ? '1px solid rgba(245, 158, 11, 1)' : 'none',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: '500',
            cursor: saving ? 'wait' : 'pointer',
            opacity: saving ? 0.6 : 1,
            transition: 'all 0.15s'
          }}
          onMouseEnter={(e) => !saving && ((e.currentTarget as HTMLButtonElement).style.background = hasUnsavedChanges ? 'rgba(245, 158, 11, 1)' : 'rgba(37, 99, 235, 1)')}
          onMouseLeave={(e) => (e.currentTarget as HTMLButtonElement).style.background = hasUnsavedChanges ? 'rgba(245, 158, 11, 0.9)' : 'rgba(37, 99, 235, 0.8)'}
        >
          {saving ? 'Salvando...' : hasUnsavedChanges ? '💾 Salvar*' : '💾 Salvar'}
        </button>
      </div>

      {/* B) Toolbar + Classes */}
      <div style={{
        background: '#161b22',
        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
        padding: '8px 24px',
        display: 'flex',
        gap: '16px',
        alignItems: 'center'
      }}>
        {/* Tool buttons */}
        <div style={{ display: 'flex', gap: '8px' }}>
          {[
            { mode: 'draw' as ToolMode, label: 'Desenhar' },
            { mode: 'select' as ToolMode, label: 'Selecionar' },
            { mode: 'delete' as ToolMode, label: 'Apagar' }
          ].map(tool => (
            <button
              key={tool.mode}
              onClick={() => setToolMode(tool.mode)}
              style={{
                padding: '8px 16px',
                background: toolMode === tool.mode
                  ? 'rgba(37, 99, 235, 0.8)'
                  : 'transparent',
                color: toolMode === tool.mode
                  ? '#fff'
                  : 'rgba(255, 255, 255, 0.5)',
                border: toolMode === tool.mode
                  ? 'none'
                  : '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'all 0.15s'
              }}
              onMouseEnter={(e) => {
                if (toolMode !== tool.mode) {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                }
              }}
              onMouseLeave={(e) => {
                if (toolMode !== tool.mode) {
                  e.currentTarget.style.background = 'transparent'
                }
              }}
            >
              {tool.label}
            </button>
          ))}

          <button
            onClick={handleAutoDetect}
            disabled={detecting}
            style={{
              padding: '8px 16px',
              background: 'transparent',
              color: 'rgba(255, 255, 255, 0.5)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: '500',
              cursor: detecting ? 'wait' : 'pointer',
              opacity: detecting ? 0.6 : 1,
              transition: 'all 0.15s'
            }}
          >
            {detecting ? 'Detectando...' : 'Auto-Detect'}
          </button>
        </div>

        <div style={{
          width: '1px',
          height: '24px',
          background: 'rgba(255, 255, 255, 0.1)'
        }} />

        {/* Classes */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {classes.map((cls, idx) => (
            <button
              key={cls.id}
              onClick={() => {
                setActiveClass(cls)
                setToolMode('draw')
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                background: activeClass.id === cls.id
                  ? `${cls.color}20`
                  : 'transparent',
                border: activeClass.id === cls.id
                  ? `1px solid ${cls.color}`
                  : '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '6px',
                fontSize: '12px',
                color: activeClass.id === cls.id
                  ? '#fff'
                  : 'rgba(255, 255, 255, 0.7)',
                cursor: 'pointer',
                transition: 'all 0.15s'
              }}
              onMouseEnter={(e) => {
                if (activeClass.id !== cls.id) {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                }
              }}
              onMouseLeave={(e) => {
                if (activeClass.id !== cls.id) {
                  e.currentTarget.style.background = 'transparent'
                }
              }}
            >
              <span style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: cls.color
              }} />
              <span style={{ fontWeight: activeClass.id === cls.id ? '600' : '400' }}>
                {idx + 1}. {cls.name}
              </span>
            </button>
          ))}
        </div>

        {/* Suggestion actions */}
        {suggestions.length > 0 && (
          <>
            <div style={{
              width: '1px',
              height: '24px',
              background: 'rgba(255, 255, 255, 0.1)'
            }} />
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={confirmAllSuggestions}
                style={{
                  padding: '6px 12px',
                  background: 'rgba(34, 197, 94, 0.8)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.15s'
                }}
              >
                ✓ Confirmar Todas ({suggestions.length})
              </button>
              <button
                onClick={discardAllSuggestions}
                style={{
                  padding: '6px 12px',
                  background: 'transparent',
                  color: 'rgba(239, 68, 68, 0.8)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '6px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.15s'
                }}
              >
                ✕ Descartar
              </button>
            </div>
          </>
        )}
      </div>

      {/* C) Área da imagem */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        overflow: 'hidden',
        background: '#0d1117'
      }}>
        {loading ? (
          <div style={{ color: 'rgba(255, 255, 255, 0.5)', fontSize: '14px' }}>
            Carregando frames...
          </div>
        ) : selectedFrame ? (
          <div
            ref={imageContainerRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onClick={handleBackgroundClick}
            style={{
              position: 'relative',
              maxWidth: '100%',
              maxHeight: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <img
              src={`/api/training/frames/${selectedFrame.id}/image`}
              alt={`Frame ${selectedFrame.frame_number}`}
              style={{
                maxWidth: '100%',
                maxHeight: 'calc(100vh - 350px)',
                display: 'block',
                userSelect: 'none'
              }}
            />

            {/* Bounding boxes */}
            {renderBoundingBoxes()}

            {/* Drawing preview */}
            {renderDrawingPreview()}

            {/* Instructions overlay */}
            {annotations.length === 0 && suggestions.length === 0 && !isDrawing && (
              <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                background: 'rgba(0, 0, 0, 0.7)',
                color: '#fff',
                padding: '16px 24px',
                borderRadius: '8px',
                fontSize: '13px',
                textAlign: 'center',
                pointerEvents: 'none'
              }}>
                <div style={{ fontWeight: '600', marginBottom: '8px' }}>Modo {toolMode === 'draw' ? 'Desenhar' : toolMode === 'select' ? 'Selecionar' : 'Apagar'}</div>
                <div style={{ fontSize: '12px', opacity: 0.8 }}>
                  {toolMode === 'draw' && 'Clique e arraste para desenhar caixas'}
                  {toolMode === 'select' && 'Clique em uma caixa para selecioná-la'}
                  {toolMode === 'delete' && 'Clique em uma caixa para removê-la'}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{ color: 'rgba(255, 255, 255, 0.5)', fontSize: '14px' }}>
            Nenhum frame disponível
          </div>
        )}
      </div>

      {/* D) Barra de progresso */}
      <div style={{
        background: '#161b22',
        borderTop: '1px solid rgba(255, 255, 255, 0.06)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
        padding: '8px 24px',
        fontFamily: "'DM Mono', monospace",
        fontSize: '12px',
        color: 'rgba(255, 255, 255, 0.6)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <button
          onClick={handlePrevFrame}
          disabled={!selectedFrame || currentFrameIndex === 0}
          style={{
            padding: '4px 12px',
            background: 'transparent',
            color: selectedFrame && currentFrameIndex > 0
              ? 'rgba(255, 255, 255, 0.7)'
              : 'rgba(255, 255, 255, 0.2)',
            border: '1px solid transparent',
            borderRadius: '4px',
            fontSize: '12px',
            cursor: selectedFrame && currentFrameIndex > 0 ? 'pointer' : 'default',
            transition: 'all 0.15s'
          }}
        >
          ← Frame {currentFrameIndex + 1}/{frames.length}
        </button>

        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <span>Boxes: {annotations.length}</span>
          {saving && <span style={{ color: '#22c55e' }}>Salvando...</span>}
        </div>

        <button
          onClick={handleNextFrame}
          disabled={!selectedFrame || currentFrameIndex === frames.length - 1}
          style={{
            padding: '4px 12px',
            background: 'transparent',
            color: selectedFrame && currentFrameIndex < frames.length - 1
              ? 'rgba(255, 255, 255, 0.7)'
              : 'rgba(255, 255, 255, 0.2)',
            border: '1px solid transparent',
            borderRadius: '4px',
            fontSize: '12px',
            cursor: selectedFrame && currentFrameIndex < frames.length - 1 ? 'pointer' : 'default',
            transition: 'all 0.15s'
          }}
        >
          Boxes: {annotations.length} →
        </button>
      </div>

      {/* E) Timeline */}
      <div style={{
        background: '#0d1117',
        height: '130px',
        borderTop: '1px solid rgba(255, 255, 255, 0.06)',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Timeline scroll area */}
        <div
          ref={timelineRef}
          style={{
            flex: 1,
            display: 'flex',
            gap: '4px',
            padding: '12px 24px',
            overflowX: 'auto',
            overflowY: 'hidden'
          }}
        >
          {(frames || []).map((frame, idx) => (
            <div
              key={frame.id}
              data-frame-id={frame.id}
              onClick={() => handleFrameChange(frame)}
              style={{
                position: 'relative',
                flexShrink: 0,
                width: '80px',
                height: '50px',
                border: selectedFrame?.id === frame.id
                  ? '2px solid #2563eb'
                  : '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '4px',
                overflow: 'hidden',
                cursor: 'pointer',
                transform: selectedFrame?.id === frame.id
                  ? 'scale(1.08)'
                  : 'scale(1)',
                transition: 'all 0.15s',
                zIndex: selectedFrame?.id === frame.id ? 2 : 1,
                background: '#161b22'
              }}
              onMouseEnter={(e) => {
                if (selectedFrame?.id !== frame.id) {
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)'
                }
              }}
              onMouseLeave={(e) => {
                if (selectedFrame?.id !== frame.id) {
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)'
                }
              }}
            >
              <img
                src={`/api/training/frames/${frame.id}/image`}
                alt={`Frame ${frame.frame_number}`}
                loading="lazy"
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  display: 'block'
                }}
              />

              {/* Annotated indicator */}
              {frame.is_annotated && (
                <div style={{
                  position: 'absolute',
                  top: '4px',
                  right: '4px',
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: '#2563eb',
                  boxShadow: '0 0 4px rgba(37, 99, 235, 0.5)'
                }} />
              )}
            </div>
          ))}
        </div>

        {/* Timestamps */}
        <div style={{
          padding: '0 24px 8px',
          display: 'flex',
          gap: '80px',
          overflowX: 'auto',
          fontFamily: "'DM Mono', monospace",
          fontSize: '9px',
          color: 'rgba(255, 255, 255, 0.25)'
        }}>
          {frames.filter((_, idx) => idx % 10 === 0).map((frame, idx) => (
            <span key={frame.id} style={{ flexShrink: 0, minWidth: '80px', textAlign: 'center' }}>
              {formatTimestamp(frame.frame_number)}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
