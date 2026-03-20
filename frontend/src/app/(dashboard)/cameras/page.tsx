'use client'

import { useState } from 'react'
import { useCameras } from '@/hooks/useCameras'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Camera, Plus, Trash2, Edit, Power, PowerOff } from 'lucide-react'
import type { CameraBrand } from '@/types/camera'
import { Textarea } from '@/components/ui/textarea'

const cameraBrands: { value: CameraBrand; label: string }[] = [
  { value: 'hikvision', label: 'Hikvision' },
  { value: 'dahua', label: 'Dahua' },
  { value: 'intelbras', label: 'Intelbras' },
  { value: 'generic', label: 'Genérico' },
  { value: 'axis', label: 'Axis' },
  { value: 'vivotek', label: 'Vivotek' },
]

export default function CamerasPage() {
  const { cameras, loading, error, createCamera, updateCamera, deleteCamera } =
    useCameras()
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [editingCamera, setEditingCamera] = useState<number | null>(null)

  const [formData, setFormData] = useState({
    name: '',
    location: '',
    ip_address: '',
    rtsp_username: '',
    rtsp_password: '',
    rtsp_port: 554,
    camera_brand: 'generic' as CameraBrand,
  })

  const handleCreateCamera = async () => {
    const { data, error } = await createCamera({
      ...formData,
      is_active: true,
      rtsp_url: null,
    })

    if (error) {
      alert('Erro ao criar câmera: ' + error.message)
      return
    }

    setIsAddDialogOpen(false)
    resetForm()
  }

  const handleUpdateCamera = async () => {
    if (!editingCamera) return

    const { error } = await updateCamera(editingCamera, formData)

    if (error) {
      alert('Erro ao atualizar câmera: ' + error.message)
      return
    }

    setEditingCamera(null)
    resetForm()
  }

  const handleDeleteCamera = async (id: number) => {
    if (!confirm('Tem certeza que deseja excluir esta câmera?')) {
      return
    }

    const { error } = await deleteCamera(id)

    if (error) {
      alert('Erro ao excluir câmera: ' + error.message)
    }
  }

  const toggleCameraStatus = async (camera: typeof cameras[0]) => {
    const { error } = await updateCamera(camera.id, {
      is_active: !camera.is_active,
    })

    if (error) {
      alert('Erro ao atualizar câmera: ' + error.message)
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      location: '',
      ip_address: '',
      rtsp_username: '',
      rtsp_password: '',
      rtsp_port: 554,
      camera_brand: 'generic',
    })
  }

  const openEditDialog = (camera: typeof cameras[0]) => {
    setEditingCamera(camera.id)
    setFormData({
      name: camera.name,
      location: camera.location,
      ip_address: camera.ip_address || '',
      rtsp_username: camera.rtsp_username || '',
      rtsp_password: camera.rtsp_password || '',
      rtsp_port: camera.rtsp_port,
      camera_brand: camera.camera_brand,
    })
  }

  if (loading) {
    return <div>Carregando câmeras...</div>
  }

  if (error) {
    return <div>Erro: {error}</div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Câmeras</h1>
          <p className="text-muted-foreground">
            Gerencie suas câmeras IP e configurações RTSP
          </p>
        </div>
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Adicionar Câmera
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Nova Câmera</DialogTitle>
              <DialogDescription>
                Configure uma nova câmera IP para monitoramento
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nome da Câmera *</Label>
                <Input
                  id="name"
                  placeholder="Ex: Câmera Entrada Principal"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="location">Localização *</Label>
                <Input
                  id="location"
                  placeholder="Ex: Fábrica - Linha A"
                  value={formData.location}
                  onChange={(e) =>
                    setFormData({ ...formData, location: e.target.value })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="ip">Endereço IP *</Label>
                <Input
                  id="ip"
                  placeholder="Ex: 189.0.0.100"
                  value={formData.ip_address}
                  onChange={(e) =>
                    setFormData({ ...formData, ip_address: e.target.value })
                  }
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="username">Usuário RTSP</Label>
                  <Input
                    id="username"
                    placeholder="admin"
                    value={formData.rtsp_username}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        rtsp_username: e.target.value,
                      })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Senha RTSP</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={formData.rtsp_password}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        rtsp_password: e.target.value,
                      })
                    }
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="port">Porta RTSP</Label>
                  <Input
                    id="port"
                    type="number"
                    value={formData.rtsp_port}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        rtsp_port: parseInt(e.target.value) || 554,
                      })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="brand">Marca da Câmera</Label>
                  <select
                    id="brand"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={formData.camera_brand}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        camera_brand: e.target.value as CameraBrand,
                      })
                    }
                  >
                    {cameraBrands.map((brand) => (
                      <option key={brand.value} value={brand.value}>
                        {brand.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setIsAddDialogOpen(false)
                  resetForm()
                }}
              >
                Cancelar
              </Button>
              <Button onClick={handleCreateCamera}>Criar Câmera</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Cameras List */}
      <Card>
        <CardHeader>
          <CardTitle>
            {cameras.length} Câmera{cameras.length !== 1 ? 's' : ''}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {cameras.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Camera className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">
                Nenhuma câmera configurada
              </h3>
              <p className="text-sm text-muted-foreground max-w-md mb-4">
                Adicione sua primeira câmera IP para começar o monitoramento.
              </p>
              <Button onClick={() => setIsAddDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Adicionar Câmera
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Localização</TableHead>
                  <TableHead>Marca</TableHead>
                  <TableHead>IP</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cameras.map((camera) => (
                  <TableRow key={camera.id}>
                    <TableCell className="font-medium">
                      {camera.name}
                    </TableCell>
                    <TableCell>{camera.location}</TableCell>
                    <TableCell className="capitalize">
                      {camera.camera_brand}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {camera.ip_address || 'N/A'}
                    </TableCell>
                    <TableCell>
                      {camera.is_active ? (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Ativa
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          Inativa
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleCameraStatus(camera)}
                          title={camera.is_active ? 'Desativar' : 'Ativar'}
                        >
                          {camera.is_active ? (
                            <PowerOff className="h-4 w-4" />
                          ) : (
                            <Power className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditDialog(camera)}
                          title="Editar"
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteCamera(camera.id)}
                          title="Excluir"
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog
        open={editingCamera !== null}
        onOpenChange={(open) => {
          if (!open) {
            setEditingCamera(null)
            resetForm()
          }
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Editar Câmera</DialogTitle>
            <DialogDescription>
              Atualize as configurações da câmera
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Nome da Câmera</Label>
              <Input
                id="edit-name"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-location">Localização</Label>
              <Input
                id="edit-location"
                value={formData.location}
                onChange={(e) =>
                  setFormData({ ...formData, location: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-ip">Endereço IP</Label>
              <Input
                id="edit-ip"
                value={formData.ip_address}
                onChange={(e) =>
                  setFormData({ ...formData, ip_address: e.target.value })
                }
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-username">Usuário RTSP</Label>
                <Input
                  id="edit-username"
                  value={formData.rtsp_username}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      rtsp_username: e.target.value,
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-password">Senha RTSP</Label>
                <Input
                  id="edit-password"
                  type="password"
                  value={formData.rtsp_password}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      rtsp_password: e.target.value,
                    })
                  }
                />
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => {
                setEditingCamera(null)
                resetForm()
              }}
            >
              Cancelar
            </Button>
            <Button onClick={handleUpdateCamera}>Salvar</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
