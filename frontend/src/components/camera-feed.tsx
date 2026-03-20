'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Video, VideoOff, Camera, RefreshCw } from 'lucide-react'

interface CameraFeedProps {
  onCapture?: (imageUrl: string) => void
}

export function CameraFeed({ onCapture }: CameraFeedProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [capturedImage, setCapturedImage] = useState<string | null>(null)

  const startCamera = async () => {
    try {
      setError(null)

      // Request camera access
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment', // Use rear camera on mobile
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      })

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream
        await videoRef.current.play()
        setStream(mediaStream)
        setIsStreaming(true)
      }
    } catch (err) {
      console.error('Error accessing camera:', err)
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

    // Call parent callback
    if (onCapture) {
      onCapture(imageUrl)
    }
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
          </CardTitle>
          <div className="flex items-center gap-2">
            {isStreaming && (
              <Badge variant="outline" className="text-green-600 border-green-600">
                Ao Vivo
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
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center bg-muted">
              <div className="text-center space-y-4 p-6">
                <VideoOff className="h-16 w-16 mx-auto text-muted-foreground" />
                <p className="text-muted-foreground">
                  Câmera desativada
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
        </div>

        {/* Controls */}
        <div className="flex flex-wrap gap-2">
          {!isStreaming ? (
            <Button onClick={startCamera} className="flex-1">
              <Video className="h-4 w-4 mr-2" />
              Iniciar Câmera
            </Button>
          ) : (
            <>
              <Button onClick={captureImage} variant="default" className="flex-1">
                <Camera className="h-4 w-4 mr-2" />
                Capturar
              </Button>
              <Button onClick={stopCamera} variant="destructive">
                <VideoOff className="h-4 w-4 mr-2" />
                Parar
              </Button>
            </>
          )}
        </div>

        {/* Captured Image Preview */}
        {capturedImage && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Última Captura:</p>
            <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
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
            <li>Clique em "Iniciar Câmera" e permita o acesso</li>
            <li>Aponte para você mesmo testando EPIs</li>
            <li>Clique em "Capturar" para registrar</li>
            <li>Funciona com webcam ou celular</li>
          </ul>
        </div>
      </CardContent>

      {/* Hidden Canvas for Capture */}
      <canvas ref={canvasRef} className="hidden" />
    </Card>
  )
}
