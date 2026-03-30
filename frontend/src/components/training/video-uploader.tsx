'use client'

import { useState, useCallback, useRef } from 'react'
import { api } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Upload, X, Film, FileVideo, AlertCircle } from 'lucide-react'

interface VideoMetadata {
  name: string
  size: number
  type: string
  duration?: number
}

interface VideoUploaderProps {
  projectId: string
  onUploadComplete: (videoId: string, frameCount: number) => void
}

export function VideoUploader({ projectId, onUploadComplete }: VideoUploaderProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [metadata, setMetadata] = useState<VideoMetadata | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const validateFile = (file: File): string | null => {
    // Check file size (max 500MB)
    const MAX_SIZE = 500 * 1024 * 1024
    if (file.size > MAX_SIZE) {
      return 'O tamanho do arquivo não pode exceder 500MB'
    }

    // Check file type
    const validTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska', 'video/msvideo']
    if (!validTypes.includes(file.type) && !file.name.match(/\.(mp4|avi|mov|mkv)$/i)) {
      return 'Formato de arquivo não suportado. Use MP4, AVI, MOV ou MKV'
    }

    return null
  }

  const extractVideoMetadata = useCallback((file: File): Promise<VideoMetadata> => {
    return new Promise((resolve) => {
      const video = document.createElement('video')
      video.preload = 'metadata'

      video.onloadedmetadata = () => {
        URL.revokeObjectURL(video.src)
        resolve({
          name: file.name,
          size: file.size,
          type: file.type,
          duration: video.duration
        })
      }

      video.onerror = () => {
        URL.revokeObjectURL(video.src)
        resolve({
          name: file.name,
          size: file.size,
          type: file.type
        })
      }

      video.src = URL.createObjectURL(file)
    })
  }, [])

  const handleFileSelect = useCallback(async (file: File) => {
    setError('')

    // Validate file
    const validationError = validateFile(file)
    if (validationError) {
      setError(validationError)
      return
    }

    setSelectedFile(file)
    setMetadata(await extractVideoMetadata(file))
  }, [extractVideoMetadata])

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }, [handleFileSelect])

  const handleDrag = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0])
    }
  }, [handleFileSelect])

  const uploadFile = async () => {
    if (!selectedFile) return

    setUploading(true)
    setProgress(0)
    setError('')

    const formData = new FormData()
    formData.append('video', selectedFile)

    try {
      const endpoint = `/api/training/projects/${projectId}/videos`
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

      const xhr = new XMLHttpRequest()

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          setProgress(Math.round((e.loaded / e.total) * 100))
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status === 201) {
          const response = JSON.parse(xhr.responseText)
          onUploadComplete(response.video.id, response.extracted_frames || 0)
          setSelectedFile(null)
          setMetadata(null)
          setProgress(0)
        } else {
          let errorMsg = 'Falha no upload'
          try {
            const errorResponse = JSON.parse(xhr.responseText)
            errorMsg = errorResponse.error || errorResponse.message || errorMsg
          } catch {
            errorMsg = xhr.statusText || errorMsg
          }
          setError(errorMsg)
        }
        setUploading(false)
      })

      xhr.addEventListener('error', () => {
        setError('Falha na conexão. Verifique sua rede.')
        setUploading(false)
      })

      xhr.addEventListener('abort', () => {
        setError('Upload cancelado')
        setUploading(false)
      })

      xhr.open('POST', `${API_BASE}${endpoint}`)

      // Add auth token
      const token = localStorage.getItem('auth_token')
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      }

      xhr.send(formData)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha no upload')
      setUploading(false)
    }
  }

  const clearSelection = () => {
    setSelectedFile(null)
    setMetadata(null)
    setError('')
    setProgress(0)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <Card>
      <CardContent className="pt-6">
        {!selectedFile ? (
          // Upload Zone
          <div
            className={`relative flex items-center justify-center w-full transition-colors ${
              dragActive ? 'bg-primary/10 border-primary' : 'bg-muted hover:bg-muted/80'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <label
              htmlFor="video-upload"
              className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-lg cursor-pointer"
            >
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <Upload className="w-12 h-12 mb-4 text-muted-foreground" />
                <p className="mb-2 text-sm text-muted-foreground">
                  <span className="font-semibold">Clique para enviar</span> ou arraste e solte
                </p>
                <p className="text-xs text-muted-foreground">
                  MP4, AVI, MOV ou MKV (máx. 500MB)
                </p>
                {error && (
                  <div className="flex items-center gap-2 mt-4 text-sm text-destructive">
                    <AlertCircle className="w-4 h-4" />
                    <span>{error}</span>
                  </div>
                )}
              </div>
              <input
                ref={fileInputRef}
                id="video-upload"
                type="file"
                className="hidden"
                accept="video/mp4,video/avi,video/quicktime,video/x-matroska,.mp4,.avi,.mov,.mkv"
                onChange={handleInputChange}
                disabled={uploading}
              />
            </label>
          </div>
        ) : (
          // File Preview & Upload
          <div className="space-y-4">
            {/* File Info */}
            <div className="flex items-start gap-4 p-4 border rounded-lg">
              <div className="flex-shrink-0">
                <FileVideo className="w-12 h-12 text-muted-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-medium truncate">{metadata?.name}</h3>
                <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-xs text-muted-foreground">
                  <span>{formatFileSize(metadata?.size || 0)}</span>
                  {metadata?.duration && (
                    <span>Duração: {formatDuration(metadata.duration)}</span>
                  )}
                </div>
              </div>
              {!uploading && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={clearSelection}
                  className="flex-shrink-0 text-destructive hover:text-destructive"
                >
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>

            {/* Upload Progress */}
            {uploading ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Enviando vídeo...</span>
                  <span className="font-medium">{progress}%</span>
                </div>
                <Progress value={progress} className="w-full" />
                <p className="text-xs text-muted-foreground text-center">
                  Isso pode levar alguns minutos dependendo do tamanho do arquivo
                </p>
              </div>
            ) : (
              // Upload Button
              <div className="space-y-3">
                <div className="text-sm text-muted-foreground">
                  <p>O vídeo será processado automaticamente após o upload:</p>
                  <ul className="list-disc list-inside mt-2 space-y-1">
                    <li>Extração de metadados (duração, FPS, resolução)</li>
                    <li>Extração de quadros para anotação</li>
                  </ul>
                </div>
                <Button
                  onClick={uploadFile}
                  className="w-full"
                  size="lg"
                >
                  <Film className="w-4 h-4 mr-2" />
                  Enviar Vídeo
                </Button>
              </div>
            )}

            {/* Error during upload */}
            {error && uploading === false && (
              <div className="flex items-start gap-2 p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}
          </div>
        )}

        {/* Instructions */}
        {!selectedFile && !uploading && (
          <div className="mt-4 p-4 bg-muted/50 rounded-lg">
            <h4 className="text-sm font-medium mb-2">Instruções:</h4>
            <ul className="text-xs text-muted-foreground space-y-1">
              <li>• Envie vídeos do processo de carregamento de caminhões</li>
              <li>• Certifique-se de que os EPIs estão visíveis no vídeo</li>
              <li>• Vídeos mais curtos (1-5 min) são processados mais rapidamente</li>
              <li>• Formatos aceitos: MP4, AVI, MOV, MKV</li>
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
