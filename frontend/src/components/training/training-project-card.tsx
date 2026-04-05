import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Trash2, Edit } from 'lucide-react'
import Link from 'next/link'
import type { TrainingProject } from '@/types/training'

interface TrainingProjectCardProps {
  project: TrainingProject
  onDelete: () => void
}

export function TrainingProjectCard({ project, onDelete }: TrainingProjectCardProps) {
  const statusConfig = {
    draft: { label: 'Rascunho', className: 'bg-gray-100 text-gray-800 hover:bg-gray-200' },
    in_progress: { label: 'Em Andamento', className: 'bg-blue-100 text-blue-800 hover:bg-blue-200' },
    training: { label: 'Treinando', className: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200' },
    completed: { label: 'Concluído', className: 'bg-green-100 text-green-800 hover:bg-green-200' },
    failed: { label: 'Falhou', className: 'bg-red-100 text-red-800 hover:bg-red-200' }
  }

  const status = statusConfig[project.status] || statusConfig.draft

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
  }

  const truncateDescription = (description: string | null, maxLength: number = 100) => {
    if (!description) return 'Sem descrição'
    if (description.length <= maxLength) return description
    return description.substring(0, maxLength) + '...'
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-lg line-clamp-1">{project.name}</CardTitle>
          <Badge variant="outline" className={status.className}>
            {status.label}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground line-clamp-2">
          {truncateDescription(project.description)}
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Target Classes */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">
              Classes ({project.target_classes.length})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {project.target_classes.slice(0, 4).map((cls) => (
                <Badge key={cls} variant="secondary" className="text-xs">
                  {cls}
                </Badge>
              ))}
              {project.target_classes.length > 4 && (
                <Badge variant="secondary" className="text-xs">
                  +{project.target_classes.length - 4}
                </Badge>
              )}
            </div>
          </div>

          {/* Metadata */}
          <div className="text-xs text-muted-foreground">
            Criado em {formatDate(project.created_at)}
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2 border-t">
            <Link href={`/dashboard/training/${project.id}`} className="flex-1">
              <Button variant="outline" size="sm" className="w-full">
                <Edit className="h-4 w-4 mr-1" />
                Ver Detalhes
              </Button>
            </Link>
            <Button
              variant="outline"
              size="sm"
              onClick={onDelete}
              className="text-destructive hover:text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
