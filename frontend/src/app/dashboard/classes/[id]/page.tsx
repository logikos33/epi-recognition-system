'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { usePathname } from 'next/navigation'
import { AuthProtected } from '@/components/auth-protected'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Upload, Loader2, Package, Image as ImageIcon, RefreshCw } from 'lucide-react'
import Link from 'next/link'
import { ImageUpload } from '@/components/classes/image-upload'
import { ImageGrid } from '@/components/classes/image-grid'

interface YOLOClass {
  id: number
  nome: string
  descricao: string | null
  valor_unitario: number
  unidade: string
  cor_hex: string
  ativo: boolean
  class_index: number
  total_imagens: number
  imagens_validadas: number
  total_deteccoes: number
}

export default function ClassDetailPage() {
  const params = useParams()
  const router = useRouter()
  const pathname = usePathname()

  const [cls, setClass] = useState<YOLOClass | null>(null)
  const [allClasses, setAllClasses] = useState<YOLOClass[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showUpload, setShowUpload] = useState(false)

  // Fetch class details
  const fetchClass = async () => {
    setLoading(true)
    try {
      // Get all classes and find the one we need
      const result = await api.get('/api/classes')
      const classes = result.classes || []
      const foundClass = classes.find((c: YOLOClass) => c.id === parseInt(params.id as string))

      setAllClasses(classes)

      if (!foundClass) {
        setError('Classe não encontrada')
      } else {
        setClass(foundClass)
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar classe')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (params.id) {
      fetchClass()
    }
  }, [params.id])

  if (loading) {
    return (
      <AuthProtected>
        <div className="flex items-center justify-center h-screen">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      </AuthProtected>
    )
  }

  if (error || !cls) {
    return (
      <AuthProtected>
        <div className="flex flex-col items-center justify-center h-screen gap-4">
          <Package className="w-16 h-16 text-muted-foreground" />
          <p className="text-muted-foreground">{error || 'Classe não encontrada'}</p>
          <Link href="/dashboard/classes">
            <Button>Voltar para Classes</Button>
          </Link>
        </div>
      </AuthProtected>
    )
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value)
  }

  return (
    <AuthProtected>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Link href="/dashboard/classes">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="w-4 h-4" />
            </Button>
          </Link>

          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{cls.nome}</h1>
              <Badge variant="outline">
                Índice {cls.class_index}
              </Badge>
              <div
                className="w-4 h-4 rounded"
                style={{ backgroundColor: cls.cor_hex, borderColor: cls.cor_hex }}
              />
            </div>
            {cls.descricao && (
              <p className="text-muted-foreground">{cls.descricao}</p>
            )}
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Valor Unitário
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {formatCurrency(cls.valor_unitario)}/{cls.unidade}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total de Imagens
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{cls.total_imagens}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Validadas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{cls.imagens_validadas}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total de Detecções
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{cls.total_deteccoes}</div>
            </CardContent>
          </Card>
        </div>

        {/* Progress Bar */}
        {cls.total_imagens > 0 && (
          <Card>
            <CardContent className="p-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Progresso do Treinamento</span>
                  <span className="font-medium">
                    {cls.imagens_validadas} / {cls.total_imagens} imagens
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{
                      width: `${(cls.imagens_validadas / cls.total_imagens) * 100}%`
                    }}
                  />
                </div>
                {cls.imagens_validadas < 20 && (
                  <p className="text-xs text-orange-600">
                    Mínimo 20 imagens validadas por classe para treinar
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Upload Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Imagens de Treinamento</CardTitle>
              <Button onClick={() => setShowUpload(!showUpload)}>
                <Upload className="w-4 h-4 mr-2" />
                {showUpload ? 'Fechar' : 'Enviar Imagens'}
              </Button>
            </div>
          </CardHeader>
          {showUpload && (
            <CardContent className="p-4">
              <ImageUpload
                classeId={cls.id}
                classeNome={cls.nome}
                onUploadComplete={() => {
                  setShowUpload(false)
                  fetchClass() // Refresh class stats
                }}
              />
            </CardContent>
          )}
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Atividade Recente</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Nenhuma atividade recente
            </p>
          </CardContent>
        </Card>

        {/* Training Images */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Imagens de Treinamento</CardTitle>
              <Button
                onClick={() => setShowUpload(!showUpload)}
                variant="outline"
                size="sm"
              >
                {showUpload ? 'Fechar' : 'Enviar Imagens'}
              </Button>
            </div>
          </CardHeader>
          {showUpload ? (
            <CardContent className="p-4">
              <ImageUpload
                classeId={cls.id}
                classeNome={cls.nome}
                onUploadComplete={() => {
                  setShowUpload(false)
                  fetchClass() // Refresh class stats
                }}
              />
            </CardContent>
          ) : (
            <ImageGrid
              classeId={cls.id}
              classeNome={cls.nome}
              classIndex={cls.class_index}
              classes={allClasses.map(c => ({ id: c.id, nome: c.nome, cor_hex: c.cor_hex }))}
              onAnnotationComplete={() => fetchClass()}
            />
          )}
        </Card>
      </div>
    </AuthProtected>
  )
}
