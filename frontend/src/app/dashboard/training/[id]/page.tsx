'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useTrainingProject } from '@/hooks/useTrainingProjects'
import { VideoUploader } from '@/components/training/video-uploader'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Loader2 } from 'lucide-react'
import Link from 'next/link'
import type { TrainingVideo } from '@/types/training'

export default function TrainingProjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { data: project, isLoading, error } = useTrainingProject(params.id as string)
  const [videos, setVideos] = useState<TrainingVideo[]>([])

  // Fetch project videos
  useEffect(() => {
    const fetchVideos = async () => {
      if (!params.id) return

      try {
        // For now, we'll just show the uploader
        // In a real implementation, you'd fetch existing videos here
        // TODO: Implement videos fetch
      } catch (err) {
        console.error('Failed to fetch videos:', err)
      }
    }

    fetchVideos()
  }, [params.id])

  const handleUploadComplete = (videoId: string, frameCount: number) => {
    // Refresh videos list
    // For now, just show a success message
    alert(`Vídeo enviado com sucesso! ${frameCount} quadros extraídos.`)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-muted-foreground">Projeto não encontrado</p>
        <Link href="/dashboard/training">
          <Button>Voltar para Treinamentos</Button>
        </Link>
      </div>
    )
  }

  const statusConfig = {
    draft: { label: 'Rascunho', className: 'bg-gray-100 text-gray-800' },
    in_progress: { label: 'Em Andamento', className: 'bg-blue-100 text-blue-800' },
    training: { label: 'Treinando', className: 'bg-yellow-100 text-yellow-800' },
    completed: { label: 'Concluído', className: 'bg-green-100 text-green-800' },
    failed: { label: 'Falhou', className: 'bg-red-100 text-red-800' }
  }

  const status = statusConfig[project.status as keyof typeof statusConfig] || statusConfig.draft

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/dashboard/training">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{project.name}</h1>
            <Badge variant="outline" className={status.className}>
              {status.label}
            </Badge>
          </div>
          <p className="text-muted-foreground">{project.description || 'Sem descrição'}</p>
        </div>
      </div>

      {/* Project Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Classes de Alvo
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {project.target_classes.map((cls: string) => (
                <Badge key={cls} variant="secondary">
                  {cls}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Vídeos Enviados
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{videos.length}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Quadros Anotados
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">0</p>
          </CardContent>
        </Card>
      </div>

      {/* Video Upload Section */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Adicionar Vídeo de Treinamento</h2>
        <VideoUploader
          projectId={project.id}
          onUploadComplete={handleUploadComplete}
        />
      </div>

      {/* Existing Videos */}
      {videos.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Vídeos do Projeto</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {videos.map(video => (
              <Card key={video.id}>
                <CardHeader>
                  <CardTitle className="text-lg line-clamp-1">{video.filename}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <p>Duração: {video.duration_seconds}s</p>
                    <p>Quadros: {video.frame_count}</p>
                    <p>FPS: {video.fps}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
