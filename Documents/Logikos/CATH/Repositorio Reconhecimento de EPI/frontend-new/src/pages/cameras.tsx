import { useState } from 'react';
import type { Camera, CameraFormData } from '../types/camera';
import { mockCameras } from '../lib/mock-data';
import {
  Plus,
  Pencil,
  Trash2,
  Search,
  Video,
  VideoOff,
  Settings,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

export function CamerasPage() {
  const [cameras, setCameras] = useState<Camera[]>(mockCameras);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCamera, setEditingCamera] = useState<Camera | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [formData, setFormData] = useState<CameraFormData>({
    name: '',
    ipAddress: '',
    port: 554,
    username: '',
    password: '',
    rtspPath: '/stream1',
    model: '',
    location: '',
  });

  const filteredCameras = cameras.filter(
    (camera) =>
      camera.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      camera.ipAddress.includes(searchTerm) ||
      camera.location?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleCreate = () => {
    setEditingCamera(null);
    setFormData({
      name: '',
      ipAddress: '',
      port: 554,
      username: '',
      password: '',
      rtspPath: '/stream1',
      model: '',
      location: '',
    });
    setIsModalOpen(true);
  };

  const handleEdit = (camera: Camera) => {
    setEditingCamera(camera);
    setFormData({
      name: camera.name,
      ipAddress: camera.ipAddress,
      port: camera.port,
      username: camera.username || '',
      password: camera.password || '',
      rtspPath: camera.rtspPath || '',
      model: camera.model,
      location: camera.location || '',
    });
    setIsModalOpen(true);
  };

  const handleDelete = (id: string) => {
    if (confirm('Tem certeza que deseja excluir esta câmera?')) {
      setCameras(cameras.filter((c) => c.id !== id));
    }
  };

  const handleSave = () => {
    if (editingCamera) {
      setCameras(
        cameras.map((c) =>
          c.id === editingCamera.id
            ? { ...c, ...formData }
            : c
        )
      );
    } else {
      const newCamera: Camera = {
        id: Date.now().toString(),
        ...formData,
        status: 'offline',
        isActive: true,
        createdAt: new Date().toISOString(),
      };
      setCameras([...cameras, newCamera]);
    }
    setIsModalOpen(false);
  };

  const toggleStatus = (id: string) => {
    setCameras(
      cameras.map((c) =>
        c.id === id
          ? {
              ...c,
              isActive: !c.isActive,
              status: c.isActive ? 'offline' : 'online',
            }
          : c
      )
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Gerenciamento de Câmeras</h1>
          <p className="text-text-secondary mt-1">
            Configure e monitore suas câmeras IP para detecção de EPI
          </p>
        </div>
        <Button onClick={handleCreate}>
          <Plus className="w-5 h-5 mr-2" />
          Nova Câmera
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">Total de Câmeras</p>
                <p className="text-3xl font-bold text-text-primary mt-1">{cameras.length}</p>
              </div>
              <Video className="w-12 h-12 text-accent-blue opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">Online</p>
                <p className="text-3xl font-bold text-accent-green mt-1">
                  {cameras.filter((c) => c.status === 'online').length}
                </p>
              </div>
              <Video className="w-12 h-12 text-accent-green opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">Offline</p>
                <p className="text-3xl font-bold text-accent-red mt-1">
                  {cameras.filter((c) => c.status === 'offline').length}
                </p>
              </div>
              <VideoOff className="w-12 h-12 text-accent-red opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">Ativas</p>
                <p className="text-3xl font-bold text-accent-blue mt-1">
                  {cameras.filter((c) => c.isActive).length}
                </p>
              </div>
              <Settings className="w-12 h-12 text-accent-blue opacity-20" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
        <Input
          placeholder="Buscar por nome, IP ou localização..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Camera List */}
      <Card variant="bordered">
        <CardHeader>
          <CardTitle>Câmeras Configuradas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                    Nome
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                    Endereço IP
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                    Modelo
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                    Localização
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                    Status
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredCameras.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-text-secondary">
                      Nenhuma câmera encontrada
                    </td>
                  </tr>
                ) : (
                  filteredCameras.map((camera) => (
                    <tr key={camera.id} className="border-b border-border hover:bg-bg-tertiary/50 transition-colors">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-bg-tertiary flex items-center justify-center">
                            <Video className="w-5 h-5 text-text-secondary" />
                          </div>
                          <div>
                            <p className="font-medium text-text-primary">{camera.name}</p>
                            <p className="text-xs text-text-secondary">
                              {camera.ipAddress}:{camera.port}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <code className="text-sm font-mono text-accent-blue">
                          {camera.ipAddress}
                        </code>
                      </td>
                      <td className="py-3 px-4 text-sm text-text-secondary">
                        {camera.model}
                      </td>
                      <td className="py-3 px-4 text-sm text-text-secondary">
                        {camera.location || '-'}
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant={camera.status === 'online' ? 'success' : 'error'}
                        >
                          {camera.status === 'online' ? 'Online' : 'Offline'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toggleStatus(camera.id)}
                            title={camera.isActive ? 'Desativar' : 'Ativar'}
                          >
                            {camera.isActive ? (
                              <Video className="w-4 h-4" />
                            ) : (
                              <VideoOff className="w-4 h-4" />
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(camera)}
                            title="Editar"
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(camera.id)}
                            title="Excluir"
                            className="text-accent-red hover:text-accent-red hover:bg-accent-red/10"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto scrollbar-thin">
            <CardHeader>
              <CardTitle>
                {editingCamera ? 'Editar Câmera' : 'Nova Câmera'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Nome da Câmera"
                    placeholder="Ex: Câmera Entrada Principal"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                  <Input
                    label="Modelo"
                    placeholder="Ex: Hikvision DS-2CD2042WD"
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                    required
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Input
                    label="Endereço IP"
                    placeholder="192.168.1.100"
                    value={formData.ipAddress}
                    onChange={(e) => setFormData({ ...formData, ipAddress: e.target.value })}
                    required
                  />
                  <Input
                    label="Porta RTSP"
                    type="number"
                    value={formData.port}
                    onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                    required
                  />
                  <Input
                    label="Caminho RTSP"
                    placeholder="/stream1"
                    value={formData.rtspPath}
                    onChange={(e) => setFormData({ ...formData, rtspPath: e.target.value })}
                  />
                </div>

                <Input
                  label="Localização"
                  placeholder="Ex: Entrada Principal"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Usuário (opcional)"
                    placeholder="admin"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  />
                  <Input
                    label="Senha (opcional)"
                    type="password"
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                  <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
                    Cancelar
                  </Button>
                  <Button onClick={handleSave}>
                    {editingCamera ? 'Salvar Alterações' : 'Adicionar Câmera'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
