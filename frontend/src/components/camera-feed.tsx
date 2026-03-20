'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Video, VideoOff, Camera, Circle, Square, Brain, Activity } from 'lucide-react'

interface CameraFeedProps {
  onCapture?: (imageUrl: string) => void
  cameraId?: number
}

interface DetectedObject {
  bbox: [number, number, number, number] // [x, y, width, height]
  class: string
  score: number
  color: string
}

export function CameraFeed({ onCapture, cameraId = 1 }: CameraFeedProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const detectionCanvasRef = useRef<HTMLCanvasElement>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [capturedImage, setCapturedImage] = useState<string | null>(null)
  const [captureCount, setCaptureCount] = useState(0)
  const [isDetecting, setIsDetecting] = useState(false)
  const [detectedObjects, setDetectedObjects] = useState<DetectedObject[]>([])
  const [detectionStats, setDetectionStats] = useState({
    personCount: 0,
    objectCount: 0,
    episCount: 0
  })

  const recordingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const detectionIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Chamar API Python para detecção YOLO real
  const detectObjectsWithYOLO = async (): Promise<DetectedObject[]> => {
    if (!videoRef.current || !canvasRef.current) return []

    try {
      // Capture frame
      const video = videoRef.current
      const canvas = canvasRef.current
      const context = canvas.getContext('2d')

      if (!context) return []

      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      context.drawImage(video, 0, 0, canvas.width, canvas.height)

      // Get base64 image
      const imageData = canvas.toDataURL('image/jpeg', 0.8)

      // Call Python API
      const response = await fetch('http://localhost:5001/api/detect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image: imageData,
          camera_id: cameraId
        })
      })

      if (!response.ok) {
        console.error('API Error:', response.status)
        return []
      }

      const result = await response.json()

      if (!result.success || !result.detections) {
        console.warn('No detections or API error')
        return []
      }

      // Convert API response to DetectedObject format
      const detectedObjects: DetectedObject[] = result.detections.map((det: any) => {
        const [x1, y1, x2, y2] = det.bbox
        const width = x2 - x1
        const height = y2 - y1

        // Choose color based on class
        let color = '#00ff00' // green default
        if (det.class === 'person') color = '#3b82f6' // blue
        if (det.confidence > 0.8) color = '#10b981' // dark green for high confidence

        return {
          bbox: [x1, y1, width, height],
          class: det.class,
          score: det.confidence,
          color
        }
      })

      console.log(`✅ YOLO detectou ${detectedObjects.length} objetos`)
      return detectedObjects

    } catch (err) {
      console.error('❌ Erro na detecção YOLO:', err)
      return []
    }
  }

  const drawBoundingBoxes = (objects: DetectedObject[]) => {
    const canvas = detectionCanvasRef.current
    const video = videoRef.current

    console.log('🎨 Desenhando bounding boxes...')
    console.log('Canvas:', canvas)
    console.log('Video:', video)
    console.log('Video dimensions:', video?.videoWidth, 'x', video?.videoHeight)
    console.log('Objects to draw:', objects.length)

    if (!canvas || !video) {
      console.error('❌ Canvas ou video não encontrado')
      return
    }

    const ctx = canvas.getContext('2d')
    if (!ctx) {
      console.error('❌ Não foi possível obter contexto 2D')
      return
    }

    // Set canvas size to match video
    canvas.width = video.videoWidth || 1280
    canvas.height = video.videoHeight || 720

    console.log('Canvas size definido:', canvas.width, 'x', canvas.height)

    // Clear previous drawings
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Draw boxes
    objects.forEach((obj, index) => {
      const [x, y, width, height] = obj.bbox
      const label = `${obj.class} ${(obj.score * 100).toFixed(0)}%`

      console.log(`Desenhando objeto ${index + 1}:`, obj.class, 'em', x, y, width, height)

      // Draw box with shadow
      ctx.shadowColor = 'rgba(0, 0, 0, 0.5)'
      ctx.shadowBlur = 10
      ctx.strokeStyle = obj.color
      ctx.lineWidth = 4
      ctx.strokeRect(x, y, width, height)
      ctx.shadowBlur = 0

      // Draw label background
      const textWidth = ctx.measureText(label).width
      ctx.fillStyle = obj.color
      ctx.fillRect(x, y - 30, textWidth + 16, 30)

      // Draw label text
      ctx.fillStyle = '#ffffff'
      ctx.font = 'bold 16px system-ui, -apple-system, sans-serif'
      ctx.fillText(label, x + 8, y - 8)
    })

    console.log('✅ Bounding boxes desenhadas com sucesso!')
  }

  const startDetection = () => {
    setIsDetecting(true)
    console.log('🔍 Iniciando detecção YOLO real...')

    // Pequeno delay para garantir que o vídeo está pronto
    setTimeout(() => {
      // Atualizar detecções a cada 1 segundo (YOLO é mais pesado)
      detectionIntervalRef.current = setInterval(async () => {
        const video = videoRef.current

        if (!video) {
          console.log('⚠️ Video ref não existe')
          return
        }

        if (!video.videoWidth || !video.videoHeight) {
          console.log('⚠️ Video dimensions não definidas ainda')
          return
        }

        console.log('🎯 Enviando frame para YOLO...')

        // Chamar API YOLO real
        const objects = await detectObjectsWithYOLO()

        console.log(`✅ Detectados ${objects.length} objetos:`, objects.map(o => o.class))

        setDetectedObjects(objects)

        // Count objects
        const personCount = objects.filter(o => o.class === 'person').length
        const episCount = objects.filter(o =>
          ['helmet', 'gloves', 'glasses', 'vest'].includes(o.class)
        ).length

        setDetectionStats({
          personCount,
          objectCount: objects.length,
          episCount
        })

        console.log('📊 Stats:', { personCount, objectCount: objects.length, episCount })

        // Draw bounding boxes
        if (objects.length > 0) {
          drawBoundingBoxes(objects)
        }
      }, 1000) // 1 segundo entre detecções (YOLO é mais pesado)
    }, 500)
  }

  const stopDetection = () => {
    if (detectionIntervalRef.current) {
      clearInterval(detectionIntervalRef.current)
      detectionIntervalRef.current = null
    }
    setIsDetecting(false)

    // Clear detection canvas
    const canvas = detectionCanvasRef.current
    if (canvas) {
      const ctx = canvas.getContext('2d')
      ctx?.clearRect(0, 0, canvas.width, canvas.height)
    }

    setDetectedObjects([])
    setDetectionStats({ personCount: 0, objectCount: 0, episCount: 0 })
  }

  const startCamera = async () => {
    console.log('=== startCamera chamado ===')
    console.log('videoRef.current:', videoRef.current)

    if (!videoRef.current) {
      console.error('✗ Video ref is null')
      setError('Erro interno: elemento de vídeo não encontrado. Tente recarregar a página.')
      return
    }

    try {
      setError(null)
      console.log('=== Iniciando câmera ===')

      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      })

      console.log('✓ Stream obtido')

      const videoElement = videoRef.current
      videoElement.srcObject = mediaStream

      videoElement.onloadedmetadata = () => {
        console.log('✓ Video metadata carregado')
        console.log('✓ Video dimensions:', videoElement.videoWidth, 'x', videoElement.videoHeight)
        videoElement.play()
          .then(() => {
            console.log('✓ Video reproduzindo com sucesso!')
            setStream(mediaStream)
            setIsStreaming(true)

            // Pequeno delay para garantir que o vídeo está pronto
            setTimeout(() => {
              console.log('🚀 Iniciando detecção agora...')
              console.log('Video width:', videoElement.videoWidth)
              console.log('Video height:', videoElement.videoHeight)
              console.log('isStreaming:', isStreaming)
              startDetection()
            }, 1000)
          })
          .catch((err) => {
            console.error('✗ Erro ao reproduzir vídeo:', err)
            setError('Erro ao reproduzir vídeo: ' + err.message)
          })
      }
    } catch (err) {
      console.error('✗ Error accessing camera:', err)
      if (err instanceof Error) {
        if (err.name === 'NotAllowedError') {
          setError('Permissão de câmera negada.')
        } else if (err.name === 'NotFoundError') {
          setError('Nenhuma câmera encontrada.')
        } else {
          setError(`Erro ao acessar câmera: ${err.message}`)
        }
      }
    }
  }

  const stopCamera = () => {
    stopRecording()
    stopDetection()
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
      setIsStreaming(false)
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
  }

  const captureImage = () => {
    if (!videoRef.current || !canvasRef.current) return

    const video = videoRef.current
    const canvas = canvasRef.current
    const context = canvas.getContext('2d')

    if (!context) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    // Draw video frame
    context.drawImage(video, 0, 0, canvas.width, canvas.height)

    // Draw detection boxes if detecting
    if (isDetecting && detectionCanvasRef.current) {
      context.drawImage(detectionCanvasRef.current, 0, 0)
    }

    const imageUrl = canvas.toDataURL('image/jpeg', 0.8)
    setCapturedImage(imageUrl)
    setCaptureCount(prev => prev + 1)

    if (onCapture) {
      onCapture(imageUrl)
    }

    console.log('📸 Imagem capturada:', captureCount + 1)
  }

  const startRecording = () => {
    setIsRecording(true)
    console.log('🎥 Iniciando gravação contínua...')

    recordingIntervalRef.current = setInterval(() => {
      captureImage()
    }, 3000)
  }

  const stopRecording = () => {
    if (recordingIntervalRef.current) {
      clearInterval(recordingIntervalRef.current)
      recordingIntervalRef.current = null
    }
    setIsRecording(false)
    console.log('⏹️ Gravação parada')
  }

  // Cleanup on unmount
  useEffect(() => {
    console.log('🎬 CameraFeed montado!')
    console.log('videoRef:', videoRef.current)
    console.log('detectionCanvasRef:', detectionCanvasRef.current)

    return () => {
      console.log('🔚 CameraFeed desmontado')
      stopCamera()
    }
  }, [])

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5" />
            Câmera ao Vivo com IA
            {cameraId && <Badge variant="outline" className="ml-2">ID: {cameraId}</Badge>}
          </CardTitle>
          <div className="flex items-center gap-2 flex-wrap">
            {isDetecting && (
              <Badge variant="outline" className="text-purple-600 border-purple-600">
                <Activity className="h-3 w-3 mr-1 animate-pulse" />
                IA Ativa
              </Badge>
            )}
            {isStreaming && (
              <Badge variant="outline" className="text-green-600 border-green-600">
                ● Ao Vivo
              </Badge>
            )}
            {isRecording && (
              <Badge variant="destructive" className="animate-pulse">
                ● Gravando
              </Badge>
            )}
          </div>
        </div>

        {/* Detection Stats */}
        {isDetecting && detectedObjects.length > 0 && (
          <div className="flex items-center gap-4 text-sm mt-2 flex-wrap">
            <div className="flex items-center gap-1">
              <span className="text-muted-foreground">Objetos:</span>
              <Badge variant="secondary">{detectionStats.objectCount}</Badge>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-muted-foreground">Pessoas:</span>
              <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-200">
                {detectionStats.personCount}
              </Badge>
            </div>
            {detectedObjects.slice(0, 4).map((obj, idx) => (
              <Badge key={idx} variant="outline" className="text-xs">
                {obj.class} {(obj.score * 100).toFixed(0)}%
              </Badge>
            ))}
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Video Feed with Detection Overlay */}
        <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
          {/* Video element */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`w-full h-full object-cover ${isStreaming ? 'block' : 'hidden'}`}
            style={{
              transform: 'scaleX(-1)',
              width: '100%',
              height: '100%',
              backgroundColor: '#000'
            }}
            onError={(e) => {
              console.error('Erro no elemento de vídeo:', e)
              setError('Erro ao carregar vídeo')
            }}
          />

          {/* Detection canvas overlay */}
          {isStreaming && (
            <canvas
              ref={detectionCanvasRef}
              className="absolute inset-0 w-full h-full"
              style={{
                pointerEvents: 'none',
                zIndex: 10,
                opacity: 1
              }}
            />
          )}

          {/* Placeholder when not streaming */}
          {!isStreaming && (
            <div className="absolute inset-0 flex items-center justify-center bg-muted">
              <div className="text-center space-y-4 p-6">
                <VideoOff className="h-16 w-16 mx-auto text-muted-foreground" />
                <p className="text-muted-foreground">Câmera desativada</p>
                <p className="text-xs text-muted-foreground">
                  Clique em "Iniciar Câmera" para começar
                </p>
              </div>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/95 backdrop-blur">
              <div className="text-center space-y-4 p-6">
                <p className="text-destructive font-medium">{error}</p>
                <Button onClick={startCamera} variant="outline" size="sm">
                  Tentar Novamente
                </Button>
              </div>
            </div>
          )}

          {/* Recording indicator */}
          {isRecording && (
            <div className="absolute top-4 right-4">
              <div className="flex items-center gap-2 bg-black/70 px-3 py-1 rounded-full">
                <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                <span className="text-white text-sm font-medium">REC</span>
              </div>
            </div>
          )}

          {/* AI indicator */}
          {isDetecting && (
            <div className="absolute top-4 left-4">
              <div className="flex items-center gap-2 bg-purple-600/90 px-3 py-1 rounded-full">
                <Brain className="h-3 w-3 text-white animate-pulse" />
                <span className="text-white text-xs font-medium">
                  Detectando...
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="flex flex-wrap gap-2">
          {!isStreaming ? (
            <Button onClick={startCamera} className="flex-1" size="lg">
              <Video className="h-4 w-4 mr-2" />
              Iniciar Câmera
            </Button>
          ) : (
            <>
              <Button
                onClick={isRecording ? stopRecording : startRecording}
                variant={isRecording ? "destructive" : "default"}
                className="flex-1"
                size="lg"
              >
                {isRecording ? (
                  <>
                    <Square className="h-4 w-4 mr-2" />
                    Parar Gravação
                  </>
                ) : (
                  <>
                    <Circle className="h-4 w-4 mr-2" />
                    Iniciar Gravação
                  </>
                )}
              </Button>
              <Button onClick={captureImage} variant="outline" disabled={isRecording}>
                <Camera className="h-4 w-4 mr-2" />
                Capturar
              </Button>
              <Button onClick={stopCamera} variant="outline" size="lg">
                <VideoOff className="h-4 w-4 mr-2" />
                Parar
              </Button>
            </>
          )}
        </div>

        {/* Capture stats */}
        {captureCount > 0 && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Capturas nesta sessão:</span>
            <span className="font-medium">{captureCount}</span>
          </div>
        )}

        {/* Captured Image Thumbnail */}
        {capturedImage && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Última Captura:</p>
            <div className="flex gap-4">
              {/* Miniatura */}
              <div className="relative w-32 h-20 bg-black rounded-lg overflow-hidden border flex-shrink-0 cursor-pointer hover:opacity-80 transition-opacity">
                <img
                  src={capturedImage}
                  alt="Captured"
                  className="w-full h-full object-cover"
                  onClick={() => {
                    const win = window.open()
                    if (win) {
                      win.document.write(`<img src="${capturedImage}" style="width: 100%">`)
                    }
                  }}
                />
              </div>
              {/* Detecções na captura */}
              {isDetecting && detectedObjects.length > 0 && (
                <div className="flex-1 text-sm space-y-1">
                  <p className="text-muted-foreground text-xs">Objetos detectados:</p>
                  <div className="flex flex-wrap gap-1">
                    {detectedObjects.map((obj, idx) => (
                      <Badge key={idx} variant="secondary" className="text-xs">
                        {obj.class} {(obj.score * 100).toFixed(0)}%
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Instructions */}
        <div className="bg-muted/50 rounded-lg p-4 text-sm space-y-2">
          <p className="font-medium">📱 Como usar:</p>
          <ul className="space-y-1 text-muted-foreground list-disc list-inside">
            <li><strong>Iniciar Câmera:</strong> Ativa câmera e IA de detecção</li>
            <li><strong>IA Ativa:</strong> Detecta pessoas, EPIs e objetos em tempo real</li>
            <li><strong>Gravação Contínua:</strong> Captura automática a cada 3 segundos</li>
            <li><strong>Capturar:</strong> Tira foto com as detecções marcadas</li>
          </ul>
          <p className="text-xs text-muted-foreground mt-2">
            🎨 Simulação visual para demonstração. Backend Python com YOLO será implementado para detecção real.
          </p>
        </div>
      </CardContent>

      {/* Hidden Canvas for Capture */}
      <canvas ref={canvasRef} className="hidden" />
    </Card>
  )
}
