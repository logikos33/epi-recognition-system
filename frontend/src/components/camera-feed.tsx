'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Video, VideoOff, Camera, Circle, Square } from 'lucide-react'

interface CameraFeedProps {
  onCapture?: (imageUrl: string) => void
  cameraId?: number
}

export function CameraFeed({ onCapture, cameraId = 1 }: CameraFeedProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [capturedImage, setCapturedImage] = useState<string | null>(null)
  const [captureCount, setCaptureCount] = useState(0)
  const recordingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const startCamera = async () => {
    try {
      setError(null)
      console.log('=== Iniciando câmera ===')

      // Request camera access
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment', // Use rear camera on mobile
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      })

      console.log('✓ Stream obtido:', mediaStream)
      console.log('✓ Video tracks:', mediaStream.getVideoTracks())

      if (videoRef.current) {
        const videoElement = videoRef.current
        videoElement.srcObject = mediaStream

        // Attach stream directly and play
        videoElement.onloadedmetadata = () => {
          console.log('✓ Video metadata carregado')
          console.log('✓ Video dimensions:', videoElement.videoWidth, 'x', videoElement.videoHeight)

          videoElement.play()
            .then(() => {
              console.log('✓ Video reproduzindo com sucesso!')
              setStream(mediaStream)
              setIsStreaming(true)
            })
            .catch((err) => {
              console.error('✗ Erro ao reproduzir vídeo:', err)
              setError('Erro ao reproduzir vídeo: ' + err.message)
            })
        }

        // Fallback: try playing immediately
        setTimeout(() => {
          if (!isStreaming && videoElement.readyState >= 2) {
            console.log('Tentando reproduzir vídeo (fallback)...')
            videoElement.play()
              .then(() => {
                console.log('✓ Video reproduzindo (fallback)!')
                setStream(mediaStream)
                setIsStreaming(true)
              })
              .catch((err) => {
                console.error('✗ Erro no fallback:', err)
              })
          }
        }, 1000)
      } else {
        console.error('✗ Video ref não disponível')
        setError('Erro interno: elemento de vídeo não encontrado')
      }
    } catch (err) {
      console.error('✗ Error accessing camera:', err)
      if (err instanceof Error) {
        if (err.name === 'NotAllowedError') {
          setError('Permissão de câmera negada. Por favor, permita o acesso à câmera.')
        } else if (err.name === 'NotFoundError') {
          setError('Nenhuma câmera encontrada no dispositivo.')
        } else {
          setError(`Erro ao acessar câmera: ${err.message}`)
        }
      } else {
        setError('Erro desconhecido ao acessar câmera.')
      }
    }
  }

  const stopCamera = () => {
    stopRecording()
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

    // Set canvas size to match video
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    // Draw video frame to canvas
    context.drawImage(video, 0, 0, canvas.width, canvas.height)

    // Convert to data URL
    const imageUrl = canvas.toDataURL('image/jpeg', 0.8)
    setCapturedImage(imageUrl)
    setCaptureCount(prev => prev + 1)

    // Call parent callback
    if (onCapture) {
      onCapture(imageUrl)
    }

    console.log('Imagem capturada:', captureCount + 1)
  }

  const startRecording = () => {
    setIsRecording(true)
    console.log('Iniciando gravação contínua...')

    // Capture every 3 seconds
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
    console.log('Gravação parada')
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera()
    }
  }, [])

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5" />
            Câmera ao Vivo
            {cameraId && <Badge variant="outline" className="ml-2">ID: {cameraId}</Badge>}
          </CardTitle>
          <div className="flex items-center gap-2">
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
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Video Feed */}
        <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
          {isStreaming ? (
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
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
          ) : (
            <div className="absolute inset-0 flex items-center justify-center bg-muted">
              <div className="text-center space-y-4 p-6">
                <VideoOff className="h-16 w-16 mx-auto text-muted-foreground" />
                <p className="text-muted-foreground">
                  Câmera desativada
                </p>
                <p className="text-xs text-muted-foreground">
                  Clique em "Iniciar Câmera" para começar
                </p>
              </div>
            </div>
          )}

          {/* Error Message */}
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

          {/* Recording indicator overlay */}
          {isRecording && (
            <div className="absolute top-4 right-4">
              <div className="flex items-center gap-2 bg-black/70 px-3 py-1 rounded-full">
                <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                <span className="text-white text-sm font-medium">
                  REC
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
                Capturar Manual
              </Button>
              <Button onClick={stopCamera} variant="outline" size="lg">
                <VideoOff className="h-4 w-2 mr-2" />
                Parar
              </Button>
            </>
          )}
        </div>

        {/* Capture Stats */}
        {captureCount > 0 && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              Capturas nesta sessão:
            </span>
            <span className="font-medium">{captureCount}</span>
          </div>
        )}

        {/* Captured Image Preview */}
        {capturedImage && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Última Captura:</p>
            <div className="relative aspect-video bg-black rounded-lg overflow-hidden border">
              <img
                src={capturedImage}
                alt="Captured"
                className="w-full h-full object-contain"
              />
            </div>
          </div>
        )}

        {/* Instructions */}
        <div className="bg-muted/50 rounded-lg p-4 text-sm space-y-2">
          <p className="font-medium">📱 Como usar:</p>
          <ul className="space-y-1 text-muted-foreground list-disc list-inside">
            <li><strong>Iniciar Câmera:</strong> Ativa câmera traseira do celular</li>
            <li><strong>Gravação Contínua:</strong> Captura automática a cada 3 segundos</li>
            <li><strong>Captura Manual:</strong> Tira uma foto quando quiser</li>
            <li><strong>Parar:</strong> Desliga câmera e para gravação</li>
          </ul>
          <p className="text-xs text-muted-foreground mt-2">
            ⚠️ Modo teste: Câmeras CFTV serão implementadas futuramente
          </p>
        </div>
      </CardContent>

      {/* Hidden Canvas for Capture */}
      <canvas ref={canvasRef} className="hidden" />
    </Card>
  )
}
