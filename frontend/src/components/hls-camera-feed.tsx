'use client';

import { useEffect, useRef, useState } from 'react';
import { loadScript } from '../utils/script-loader';

interface HLSCameraFeedProps {
  cameraId: number;
  mode?: 'primary' | 'thumbnail';
  onError?: (error: string) => void;
  onStreamActive?: () => void;
}

interface Detection {
  camera_id: number;
  timestamp: number;
  frame_id: number;
  detections: DetectionBox[];
}

interface DetectionBox {
  bbox: [number, number, number, number]; // [x, y, width, height]
  class: string;
  confidence: number;
}

export function HLSCameraFeed({
  cameraId,
  mode = 'primary',
  onError,
  onStreamActive
}: HLSCameraFeedProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hlsRef = useRef<any>(null);
  const socketRef = useRef<any>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);

  const [status, setStatus] = useState<'idle' | 'connecting' | 'streaming' | 'error'>('idle');
  const [detections, setDetections] = useState<DetectionBox[]>([]);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [isOnline, setIsOnline] = useState<boolean>(true);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 3000; // 3 seconds

  // Detect if browser supports HLS natively (Safari)
  const supportsNativeHLS = () => {
    const video = document.createElement('video');
    return video.canPlayType('application/vnd.apple.mpegurl') !== '';
  };

  // Cleanup function
  const cleanup = () => {
    // Clear timeouts
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Destroy HLS instance
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }

    // Disconnect WebSocket
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }
  };

  // Initialize HLS stream with retry logic
  const initializeHLS = async () => {
    const video = videoRef.current;
    if (!video) return;

    setStatus('connecting');
    setErrorMessage('');

    const hlsUrl = `${API_URL}/streams/${cameraId}/stream.m3u8`;

    try {
      // Load hls.js dynamically
      await loadScript('https://cdn.jsdelivr.net/npm/hls.js@latest/dist/hls.min.js');

      if ((window as any).Hls.isSupported()) {
        // Initialize hls.js
        const hls = new (window as any).Hls({
          maxBufferLength: 5,
          maxMaxBufferLength: 30,
          lowLatencyMode: true,
          backBufferLength: 90
        });

        hlsRef.current = hls;

        // Error handling with auto-retry
        hls.on(Hls.Events.ERROR, (event: any, data: any) => {
          console.error('HLS error:', event, data);

          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                console.error('Fatal network error, recovering...');
                setErrorMessage('Erro de conexão. Tentando reconectar...');

                // Try to recover network error
                hls.startLoad();
                break;

              case Hls.ErrorTypes.MEDIA_ERROR:
                console.error('Fatal media error, recovering...');
                setErrorMessage('Erro de mídia. Tentando recuperar...');

                // Try to recover media error
                hls.recoverMediaError();
                break;

              default:
                console.error('Fatal error, cannot recover');
                setErrorMessage('Erro fatal no stream.');
                setStatus('error');
                onError?.('Stream initialization failed');

                // Schedule retry
                scheduleRetry();
                break;
            }
          }
        });

        // Success handling
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          console.log('HLS manifest parsed, playing video');
          setStatus('streaming');
          setErrorMessage('');
          reconnectAttemptsRef.current = 0; // Reset reconnect counter
          onStreamActive?.();
        });

        // Load source
        hls.loadSource(hlsUrl);
        hls.attachMedia(video);
        video.play().catch((err) => {
          console.error('Auto-play failed:', err);
          setErrorMessage('Autoplay bloqueado. Clique no vídeo para iniciar.');
        });

      } else if (supportsNativeHLS()) {
        // Native HLS (Safari)
        video.src = hlsUrl;

        video.addEventListener('loadeddata', () => {
          setStatus('streaming');
          setErrorMessage('');
          reconnectAttemptsRef.current = 0;
          onStreamActive?.();
        });

        video.addEventListener('error', (e: any) => {
          console.error('Video error:', e);
          const errorMsg = getVideoErrorMessage(video);
          setErrorMessage(errorMsg);
          setStatus('error');
          onError?.(errorMsg);
          scheduleRetry();
        });

        video.play().catch((err) => {
          console.error('Auto-play failed:', err);
          setErrorMessage('Autoplay bloqueado. Clique no vídeo para iniciar.');
        });
      } else {
        throw new Error('Seu navegador não suporta HLS.');
      }

    } catch (error) {
      console.error('HLS initialization error:', error);
      const errorMsg = error instanceof Error ? error.message : 'Erro ao inicializar stream';
      setErrorMessage(errorMsg);
      setStatus('error');
      onError?.(errorMsg);
      scheduleRetry();
    }
  };

  // Schedule retry with exponential backoff
  const scheduleRetry = () => {
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      console.error('Max reconnect attempts reached');
      setErrorMessage('Máximo de tentativas de reconexão atingido.');
      return;
    }

    const delay = RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current); // Exponential backoff
    console.log(`Scheduling retry in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${MAX_RECONNECT_ATTEMPTS})`);

    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectAttemptsRef.current++;
      initializeHLS();
    }, delay);
  };

  // Get user-friendly video error message
  const getVideoErrorMessage = (video: HTMLVideoElement): string => {
    const error = video.error;
    if (!error) return 'Erro desconhecido no vídeo';

    switch (error.message) {
      case MediaError.MEDIA_ERR_ABORTED:
        return 'Carregamento do vídeo abortado.';
      case MediaError.MEDIA_ERR_NETWORK:
        return 'Erro de rede ao carregar o vídeo.';
      case MediaError.MEDIA_ERR_DECODE:
        return 'Erro ao decodificar o vídeo.';
      case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
        return 'Formato de vídeo não suportado.';
      default:
        return `Erro no vídeo: ${error.message}`;
    }
  };

  // Initialize WebSocket with reconnection
  const initializeWebSocket = () => {
    try {
      // Get auth token from localStorage
      const token = localStorage.getItem('token');
      if (!token) {
        console.warn('No auth token found, WebSocket may fail');
      }

      // Create socket connection
      const io = require('socket.io-client');
      const socket = io(API_URL, {
        auth: { token },
        reconnection: true,
        reconnectionDelay: RECONNECT_DELAY,
        reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
        timeout: 10000
      });

      socketRef.current = socket;

      // Connection events
      socket.on('connect', () => {
        console.log('WebSocket connected:', socket.id);
        setIsOnline(true);
        reconnectAttemptsRef.current = 0;

        // Subscribe to camera
        socket.emit('subscribe_camera', { camera_id: cameraId });
      });

      socket.on('disconnect', (reason: string) => {
        console.log('WebSocket disconnected:', reason);
        if (reason === 'io server disconnect') {
          // Server disconnected client, try to reconnect
          setIsOnline(false);
          socket.connect();
        }
      });

      socket.on('connect_error', (error: Error) => {
        console.error('WebSocket connection error:', error);
        setIsOnline(false);
        setErrorMessage('WebSocket desconectado. Tentando reconectar...');
      });

      socket.on('reconnect', (attemptNumber: number) => {
        console.log('WebSocket reconnected after', attemptNumber, 'attempts');
        setIsOnline(true);
        setErrorMessage('');
        socket.emit('subscribe_camera', { camera_id: cameraId });
      });

      socket.on('reconnect_attempt', (attemptNumber: number) => {
        console.log('WebSocket reconnect attempt:', attemptNumber);
      });

      socket.on('reconnect_failed', () => {
        console.error('WebSocket reconnection failed');
        setIsOnline(false);
        setErrorMessage('Falha ao reconectar WebSocket.');
      });

      // Detection events
      socket.on('subscribed', (data: { camera_id: number; room: string }) => {
        console.log('Subscribed to camera:', data);
      });

      socket.on('detection', (data: Detection) => {
        if (data.camera_id === cameraId) {
          setDetections(data.detections);
          drawDetections(data.detections);
        }
      });

      socket.on('error', (error: { message: string }) => {
        console.error('WebSocket error:', error);
        setErrorMessage(`Erro no WebSocket: ${error.message}`);
      });

    } catch (error) {
      console.error('Failed to initialize WebSocket:', error);
      setErrorMessage('Erro ao inicializar WebSocket');
      setIsOnline(false);
    }
  };

  // Draw detection boxes on canvas
  const drawDetections = (detectionBoxes: DetectionBox[]) => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear previous drawings
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw boxes
    detectionBoxes.forEach((box) => {
      const [x, y, width, height] = box.bbox;

      // Draw rectangle
      ctx.strokeStyle = '#00ff00';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, width, height);

      // Draw label background
      ctx.fillStyle = 'rgba(0, 255, 0, 0.7)';
      const label = `${box.class} ${(box.confidence * 100).toFixed(1)}%`;
      const textWidth = ctx.measureText(label).width;
      ctx.fillRect(x, y - 20, textWidth + 10, 20);

      // Draw label text
      ctx.fillStyle = '#ffffff';
      ctx.font = '14px Arial';
      ctx.fillText(label, x + 5, y - 5);
    });
  };

  // Initialize on mount
  useEffect(() => {
    console.log(`Initializing HLS feed for camera ${cameraId}`);
    initializeHLS();
    initializeWebSocket();

    // Cleanup on unmount
    return () => {
      console.log(`Cleaning up HLS feed for camera ${cameraId}`);
      cleanup();
    };
  }, [cameraId]);

  // Online/offline detection
  useEffect(() => {
    const handleOnline = () => {
      console.log('Browser online');
      setIsOnline(true);
      if (status !== 'streaming') {
        initializeHLS();
      }
    };

    const handleOffline = () => {
      console.log('Browser offline');
      setIsOnline(false);
      setErrorMessage('Conexão perdida. Aguardando reconexão...');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [status]);

  const size = mode === 'primary' ? 'w-full h-[300px]' : 'w-full h-[120px]';

  return (
    <div className={`relative ${size} bg-black rounded-lg overflow-hidden`}>
      {/* Video element */}
      <video
        ref={videoRef}
        className="w-full h-full object-cover"
        muted
        playsInline
        controls={status === 'error'}
      />

      {/* Canvas overlay for detection boxes */}
      <canvas
        ref={canvasRef}
        className="absolute top-0 left-0 w-full h-full pointer-events-none"
      />

      {/* Status indicator */}
      <div className="absolute top-2 right-2 flex items-center gap-2">
        {/* Status badge */}
        <div className={`
          px-2 py-1 rounded text-xs font-medium
          ${status === 'streaming' ? 'bg-green-500 text-white' : ''}
          ${status === 'connecting' ? 'bg-yellow-500 text-white' : ''}
          ${status === 'error' ? 'bg-red-500 text-white' : ''}
          ${status === 'idle' ? 'bg-gray-500 text-white' : ''}
        `}>
          {status === 'streaming' && 'Ao vivo'}
          {status === 'connecting' && 'Conectando...'}
          {status === 'error' && 'Erro'}
          {status === 'idle' && 'Inativo'}
        </div>

        {/* Online indicator */}
        {isOnline && (
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
        )}
      </div>

      {/* Error message */}
      {errorMessage && (
        <div className="absolute bottom-0 left-0 right-0 bg-red-900/90 text-white p-2 text-sm">
          {errorMessage}
          {reconnectAttemptsRef.current > 0 && (
            <span className="ml-2">({reconnectAttemptsRef.current}/{MAX_RECONNECT_ATTEMPTS} tentativas)</span>
          )}
        </div>
      )}

      {/* Detection count */}
      {detections.length > 0 && status === 'streaming' && (
        <div className="absolute top-2 left-2 bg-blue-600/90 text-white px-2 py-1 rounded text-xs">
          {detections.length} detecções
        </div>
      )}

      {/* Click to play overlay (for autoplay blocked) */}
      {status === 'connecting' && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
          <div className="text-white text-sm">Carregando stream...</div>
        </div>
      )}
    </div>
  );
}
