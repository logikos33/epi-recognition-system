'use client'

import { useTrainingProjects, useDeleteTrainingProject } from '@/hooks/useTrainingProjects'
import { TrainingProjectCard } from '@/components/training/training-project-card'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Plus, Brain } from 'lucide-react'
import Link from 'next/link'

export default function TrainingProjectsPage() {
  const { data: projects, isLoading, error } = useTrainingProjects()
  const deleteProject = useDeleteTrainingProject()

  const handleDeleteProject = async (projectId: string) => {
    if (!confirm('Tem certeza que deseja excluir este projeto de treinamento?')) {
      return
    }

    deleteProject.mutate(projectId, {
      onError: (error) => {
        alert('Erro ao excluir projeto: ' + error.message)
      }
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-muted-foreground">Carregando projetos de treinamento...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive text-center">
          <p className="text-lg font-semibold mb-2">Erro ao carregar projetos</p>
          <p className="text-sm text-muted-foreground">{error.message}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projetos de Treinamento</h1>
          <p className="text-muted-foreground">
            Crie e gerencie modelos customizados do YOLOv8 para detecção de EPIs
          </p>
        </div>
        <Link href="/dashboard/training/new">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Novo Projeto
          </Button>
        </Link>
      </div>

      {/* Projects List */}
      {!projects || projects.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Brain className="h-16 w-16 text-muted-foreground mb-4" />
            <h3 className="text-xl font-semibold mb-2">Nenhum projeto de treinamento</h3>
            <p className="text-sm text-muted-foreground text-center max-w-md mb-6">
              Crie seu primeiro projeto para começar a treinar modelos customizados de detecção de EPIs
              como capacetes, coletes, luvas e outros equipamentos de proteção.
            </p>
            <div className="space-y-2 text-sm text-muted-foreground text-left max-w-lg mb-6">
              <p className="font-medium">O fluxo de trabalho inclui:</p>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li>Fazer upload de vídeos de carregamento de caminhões</li>
                <li>Extrair frames para anotação manual</li>
                <li>Desenhar bounding boxes ao redor dos EPIs</li>
                <li>Exportar no formato YOLO</li>
                <li>Treinar modelo customizado</li>
              </ul>
            </div>
            <Link href="/dashboard/training/new">
              <Button size="lg">
                <Plus className="h-4 w-4 mr-2" />
                Criar Primeiro Projeto
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {projects.length} {projects.length === 1 ? 'projeto' : 'projetos'}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project) => (
              <TrainingProjectCard
                key={project.id}
                project={project}
                onDelete={() => handleDeleteProject(project.id)}
              />
            ))}
          </div>
        </>
      )}

      {/* Info Card */}
      <Card>
        <CardContent className="pt-6">
          <h3 className="font-semibold mb-3">Como funciona o treinamento customizado?</h3>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>1. <strong>Crie um projeto</strong> definindo as classes de EPIs que deseja detectar</p>
            <p>2. <strong>Faça upload de vídeos</strong> mostrando o carregamento de caminhões</p>
            <p>3. <strong>Anote os frames</strong> desenhando bounding boxes ao redor dos EPIs</p>
            <p>4. <strong>Exporte o dataset</strong> no formato YOLOv8</p>
            <p>5. <strong>Treine o modelo</strong> com as configurações desejadas</p>
            <p>6. <strong>Use o modelo treinado</strong> para contar EPIs automaticamente</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
