'use client'

import { useState, useEffect } from 'react'
import { AuthProtected } from '@/components/auth-protected'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Brain, Upload, CheckCircle, XCircle, Loader2, Download, Play } from 'lucide-react'
import Link from 'next/link'

interface TrainingClass {
  id: number
  nome: string
  descricao: string | null
  valor_unitario: number
  unidade: string
  cor_hex: string
  class_index: number
  ativo: boolean
  total_imagens: number
  imagens_validadas: number
  pronta_para_treinar: boolean
  progresso: number
}

interface TrainingStatus {
  classes: TrainingClass[]
  pode_iniciar_treinamento: boolean
  total_imagens_validadas: number
  classes_prontas: number
  classes_total: number
}

export default function TrainingPanelPage() {
  const [status, setStatus] = useState<TrainingStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [training, setTraining] = useState(false)

  const fetchStatus = async () => {
    setLoading(true)
    try {
      const result = await api.get('/api/treinamento/status')
      setStatus(result)
    } catch (err: any) {
      console.error('Error fetching training status:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
  }, [])

  const handleExport = async () => {
    setExporting(true)
    try {
      const result = await api.post('/api/treinamento/exportar-dataset', {})
      alert(result.mensagem)
    } catch (err: any) {
      alert('Erro ao exportar dataset: ' + (err.message || 'Erro desconhecido'))
    } finally {
      setExporting(false)
    }
  }

  const handleStartTraining = async () => {
    if (!status?.pode_iniciar_treinamento) {
      alert('Você precisa de pelo menos 20 imagens validadas por classe para iniciar o treinamento.')
      return
    }

    if (!confirm('Deseja iniciar o treinamento do modelo YOLO? Este processo pode levar várias horas.')) {
      return
    }

    setTraining(true)
    try {
      // First export the dataset
      await api.post('/api/treinamento/exportar-dataset', {})

      // TODO: Implement actual training endpoint
      // For now, just show a message
      alert('Treinamento iniciado! Esta funcionalidade será implementada em breve.')
    } catch (err: any) {
      alert('Erro ao iniciar treinamento: ' + (err.message || 'Erro desconhecido'))
    } finally {
      setTraining(false)
    }
  }

  if (loading) {
    return (
      <AuthProtected>
        <div className="flex items-center justify-center h-screen">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      </AuthProtected>
    )
  }

  return (
    <AuthProtected>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Painel de Treinamento YOLO</h1>
            <p className="text-muted-foreground">
              Gerencie o treinamento do modelo de detecção customizado
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={fetchStatus}>
              Atualizar
            </Button>
          </div>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Classes Configuradas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{status?.classes_total || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Classes Prontas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {status?.classes_prontas || 0} / {status?.classes_total || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Imagens Validadas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{status?.total_imagens_validadas || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Status do Treinamento
              </CardTitle>
            </CardHeader>
            <CardContent>
              {status?.pode_iniciar_treinamento ? (
                <Badge variant="default" className="bg-green-600">
                  Pronto para Treinar
                </Badge>
              ) : (
                <Badge variant="secondary">
                  Aguardando Imagens
                </Badge>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Classes Progress */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Progresso por Classe</CardTitle>
              <Link href="/dashboard/classes">
                <Button variant="outline" size="sm">
                  Gerenciar Classes
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {status?.classes.map((classe) => (
                <div key={classe.id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-4 h-4 rounded"
                        style={{ backgroundColor: classe.cor_hex }}
                      />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{classe.nome}</span>
                          <Badge variant="outline" className="text-xs">
                            Índice {classe.class_index}
                          </Badge>
                          {classe.pronta_para_treinar ? (
                            <CheckCircle className="w-4 h-4 text-green-600" />
                          ) : (
                            <XCircle className="w-4 h-4 text-orange-600" />
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {classe.imagens_validadas} / 20 imagens validadas
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium">{classe.progresso.toFixed(0)}%</div>
                      <Link href={`/dashboard/classes/${classe.id}`}>
                        <Button variant="ghost" size="sm">
                          Ver Detalhes
                        </Button>
                      </Link>
                    </div>
                  </div>
                  <Progress value={classe.progresso} className="h-2" />
                </div>
              ))}
            </div>

            {status && status.classes.length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
                <Brain className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Nenhuma classe configurada</p>
                <Link href="/dashboard/classes">
                  <Button variant="outline" className="mt-4">
                    Criar Primeira Classe
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Instructions */}
        <Card>
          <CardHeader>
            <CardTitle>Instruções de Treinamento</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 text-sm">
              <div>
                <h4 className="font-semibold mb-2">1. Configure as Classes</h4>
                <p className="text-muted-foreground">
                  Adicione todas as classes YOLO que deseja treinar em "Gerenciar Classes".
                </p>
              </div>

              <div>
                <h4 className="font-semibold mb-2">2. Faça Upload das Imagens</h4>
                <p className="text-muted-foreground">
                  Para cada classe, faça upload de pelo menos 20 imagens de treinamento.
                  O mínimo recomendado é 50-100 imagens por classe para melhores resultados.
                </p>
              </div>

              <div>
                <h4 className="font-semibold mb-2">3. Anote as Imagens</h4>
                <p className="text-muted-foreground">
                  Desenhe bounding boxes ao redor dos objetos em cada imagem.
                  O sistema irá salvar as anotações no formato YOLO.
                </p>
              </div>

              <div>
                <h4 className="font-semibold mb-2">4. Exporte o Dataset</h4>
                <p className="text-muted-foreground">
                  Clique em "Exportar Dataset" para gerar o arquivo data.yaml necessário para o treinamento.
                </p>
              </div>

              <div>
                <h4 className="font-semibold mb-2">5. Inicie o Treinamento</h4>
                <p className="text-muted-foreground">
                  Quando todas as classes estiverem prontas (20+ imagens validadas),
                  clique em "Iniciar Treinamento" para começar o treinamento do modelo.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Ações de Treinamento</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              <Button
                onClick={handleExport}
                disabled={exporting || !status || status.total_imagens_validadas === 0}
              >
                {exporting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                <Download className="w-4 h-4 mr-2" />
                Exportar Dataset
              </Button>

              <Button
                onClick={handleStartTraining}
                disabled={training || !status?.pode_iniciar_treinamento}
                variant="default"
              >
                {training && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                <Play className="w-4 h-4 mr-2" />
                Iniciar Treinamento
              </Button>
            </div>

            {!status?.pode_iniciar_treinamento && status?.classes_total > 0 && (
              <p className="text-sm text-orange-600 mt-4">
                Você precisa de pelo menos 20 imagens validadas por classe para iniciar o treinamento.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </AuthProtected>
  )
}
