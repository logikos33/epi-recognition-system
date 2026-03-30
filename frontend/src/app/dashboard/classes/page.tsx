'use client'

import { useState, useEffect } from 'react'
import { AuthProtected } from '@/components/auth-protected'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Plus, Edit, Trash2, Settings, Package, Loader2 } from 'lucide-react'
import { ClassFormModal } from '@/components/classes/class-form-modal'
import Link from 'next/link'

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

export default function ClassesManagementPage() {
  const [classes, setClasses] = useState<YOLOClass[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [selectedClass, setSelectedClass] = useState<YOLOClass | null>(null)

  // Fetch classes
  const fetchClasses = async () => {
    setLoading(true)
    try {
      const result = await api.get('/api/classes')
      setClasses(result.classes || [])
    } catch (err: any) {
      console.error('Error fetching classes:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchClasses()
  }, [])

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value)
  }

  // Get color badge style
  const getColorBadge = (hex: string) => ({
    backgroundColor: hex,
    borderColor: hex
  })

  // Handle create/edit success
  const handleSuccess = () => {
    fetchClasses()
    setSelectedClass(null)
  }

  // Handle edit click
  const handleEdit = (cls: YOLOClass) => {
    setSelectedClass(cls)
    setShowEditModal(true)
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
            <h1 className="text-3xl font-bold tracking-tight">Gerenciar Classes YOLO</h1>
            <p className="text-muted-foreground">
              Configure classes para detecção automática e cálculo de valores
            </p>
          </div>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Nova Classe
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total de Classes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{classes.length}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Classes Ativas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {classes.filter(c => c.ativo).length}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total de Detecções
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {classes.reduce((sum, c) => sum + (c.total_deteccoes || 0), 0)}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Imagens de Treinamento
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {classes.reduce((sum, c) => sum + (c.total_imagens || 0), 0)}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Classes Table */}
        <Card>
          <CardHeader>
            <CardTitle>Classes Configuradas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {classes.map((cls) => (
                <div
                  key={cls.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    {/* Color indicator */}
                    <div
                      className="w-4 h-4 rounded"
                      style={getColorBadge(cls.cor_hex)}
                    />

                    {/* Class info */}
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{cls.nome}</h3>
                        <Badge variant="outline" className="text-xs">
                          Índice {cls.class_index}
                        </Badge>
                        {!cls.ativo && (
                          <Badge variant="secondary" className="text-xs">
                            Inativa
                          </Badge>
                        )}
                      </div>
                      {cls.descricao && (
                        <p className="text-sm text-muted-foreground">{cls.descricao}</p>
                      )}
                      <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                        <span className="font-semibold text-green-600">
                          {formatCurrency(cls.valor_unitario)}/{cls.unidade}
                        </span>
                        <span>•</span>
                        <span>{cls.total_imagens} imagens</span>
                        <span>•</span>
                        <span>{cls.total_deteccoes} detecções</span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(cls)}
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}

              {classes.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                  <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Nenhuma classe configurada</p>
                  <Button
                    variant="outline"
                    className="mt-4"
                    onClick={() => setShowCreateModal(true)}
                  >
                    Criar Primeira Classe
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Create/Edit Modal */}
        <ClassFormModal
          open={showCreateModal}
          onClose={() => {
            setShowCreateModal(false)
            setSelectedClass(null)
          }}
          classToEdit={null}
          onSuccess={handleSuccess}
        />

        <ClassFormModal
          open={showEditModal}
          onClose={() => {
            setShowEditModal(false)
            setSelectedClass(null)
          }}
          classToEdit={selectedClass}
          onSuccess={handleSuccess}
        />
      </div>
    </AuthProtected>
  )
}
