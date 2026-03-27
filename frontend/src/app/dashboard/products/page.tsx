'use client'

import { useState } from 'react'
import { useProducts } from '@/hooks/useProducts'
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
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Package, Plus, Trash2, Edit, Image as ImageIcon } from 'lucide-react'
import { PRODUCT_CATEGORIES } from '@/types/product'

export default function ProductsPage() {
  const { products, loading, error, createProduct, updateProduct, deleteProduct } = useProducts()
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState<string | null>(null)

  const [formData, setFormData] = useState({
    name: '',
    sku: '',
    category: '',
    description: '',
    detection_threshold: 0.85,
    volume_cm3: '',
    weight_g: '',
  })

  const resetForm = () => {
    setFormData({
      name: '',
      sku: '',
      category: '',
      description: '',
      detection_threshold: 0.85,
      volume_cm3: '',
      weight_g: '',
    })
  }

  const handleCreateProduct = async () => {
    if (!formData.name.trim()) {
      alert('Nome do produto é obrigatório')
      return
    }

    const { product, error: err } = await createProduct({
      name: formData.name,
      sku: formData.sku || undefined,
      category: formData.category || undefined,
      description: formData.description || undefined,
      detection_threshold: formData.detection_threshold,
      volume_cm3: formData.volume_cm3 ? parseFloat(formData.volume_cm3) : undefined,
      weight_g: formData.weight_g ? parseFloat(formData.weight_g) : undefined,
    })

    if (err) {
      alert('Erro ao criar produto: ' + err)
      return
    }

    setIsAddDialogOpen(false)
    resetForm()
  }

  const handleUpdateProduct = async () => {
    if (!editingProduct) return

    const { product, error: err } = await updateProduct(editingProduct, {
      name: formData.name,
      sku: formData.sku || undefined,
      category: formData.category || undefined,
      description: formData.description || undefined,
      detection_threshold: formData.detection_threshold,
      volume_cm3: formData.volume_cm3 ? parseFloat(formData.volume_cm3) : undefined,
      weight_g: formData.weight_g ? parseFloat(formData.weight_g) : undefined,
    })

    if (err) {
      alert('Erro ao atualizar produto: ' + err)
      return
    }

    setEditingProduct(null)
    resetForm()
  }

  const handleDeleteProduct = async (id: string) => {
    if (!confirm('Tem certeza que deseja desativar este produto?')) {
      return
    }

    const { error: err } = await deleteProduct(id)

    if (err) {
      alert('Erro ao desativar produto: ' + err)
    }
  }

  const openEditDialog = (product: typeof products[0]) => {
    setFormData({
      name: product.name,
      sku: product.sku || '',
      category: product.category || '',
      description: product.description || '',
      detection_threshold: product.detection_threshold,
      volume_cm3: product.volume_cm3?.toString() || '',
      weight_g: product.weight_g?.toString() || '',
    })
    setEditingProduct(product.id)
    setIsAddDialogOpen(true)
  }

  const closeDialog = () => {
    setIsAddDialogOpen(false)
    setEditingProduct(null)
    resetForm()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-muted-foreground">Carregando produtos...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Produtos</h1>
          <p className="text-muted-foreground">
            Gerencie o catálogo de produtos para reconhecimento com IA
          </p>
        </div>
        <Dialog open={isAddDialogOpen} onOpenChange={(open) => (open ? setIsAddDialogOpen(true) : closeDialog())}>
          <DialogTrigger asChild>
            <Button onClick={() => setEditingProduct(null)}>
              <Plus className="mr-2 h-4 w-4" />
              Novo Produto
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>{editingProduct ? 'Editar Produto' : 'Novo Produto'}</DialogTitle>
              <DialogDescription>
                {editingProduct
                  ? 'Atualize as informações do produto'
                  : 'Adicione um novo produto ao catálogo para treinamento do modelo de IA'}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Nome do Produto *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Ex: Coca-Cola Lata 350ml"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="sku">SKU (Código)</Label>
                <Input
                  id="sku"
                  value={formData.sku}
                  onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
                  placeholder="Ex: COC-LATA-350"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="category">Categoria</Label>
                <div className="flex flex-wrap gap-2">
                  {PRODUCT_CATEGORIES.map((cat) => (
                    <Badge
                      key={cat}
                      variant={formData.category === cat ? 'default' : 'outline'}
                      className="cursor-pointer"
                      onClick={() => setFormData({ ...formData, category: cat })}
                    >
                      {cat}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="description">Descrição</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Descrição detalhada do produto"
                  rows={3}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="threshold">Threshold de Detecção</Label>
                  <Input
                    id="threshold"
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={formData.detection_threshold}
                    onChange={(e) =>
                      setFormData({ ...formData, detection_threshold: parseFloat(e.target.value) })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Mínimo: 0.0, Máximo: 1.0 (Padrão: 0.85)
                  </p>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="volume">Volume (cm³)</Label>
                  <Input
                    id="volume"
                    type="number"
                    value={formData.volume_cm3}
                    onChange={(e) => setFormData({ ...formData, volume_cm3: e.target.value })}
                    placeholder="Ex: 350"
                  />
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="weight">Peso (g)</Label>
                <Input
                  id="weight"
                  type="number"
                  value={formData.weight_g}
                  onChange={(e) => setFormData({ ...formData, weight_g: e.target.value })}
                  placeholder="Ex: 350"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={closeDialog}>
                Cancelar
              </Button>
              <Button onClick={editingProduct ? handleUpdateProduct : handleCreateProduct}>
                {editingProduct ? 'Atualizar' : 'Criar'} Produto
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Products Table */}
      <Card>
        <CardHeader>
          <CardTitle>Lista de Produtos ({products.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="text-center py-8">
              <p className="text-red-500">Erro: {error}</p>
            </div>
          ) : products.length === 0 ? (
            <div className="text-center py-12">
              <Package className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-semibold">Nenhum produto cadastrado</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Comece adicionando produtos para treinar o modelo de IA
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>SKU</TableHead>
                  <TableHead>Categoria</TableHead>
                  <TableHead>Threshold</TableHead>
                  <TableHead>Imagens de Treino</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {products.map((product) => (
                  <TableRow key={product.id}>
                    <TableCell className="font-medium">{product.name}</TableCell>
                    <TableCell>{product.sku || '-'}</TableCell>
                    <TableCell>
                      {product.category ? (
                        <Badge variant="outline">{product.category}</Badge>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>{(product.detection_threshold * 100).toFixed(0)}%</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <ImageIcon className="h-4 w-4 text-muted-foreground" />
                        <span>{product.training_images_count || 0}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={product.is_active ? 'default' : 'secondary'}>
                        {product.is_active ? 'Ativo' : 'Inativo'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => openEditDialog(product)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteProduct(product.id)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
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

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>Como funciona o reconhecimento de produtos?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>1. Cadastre os produtos que deseja reconhecer</p>
          <p>2. Faça upload de imagens de treinamento para cada produto (mínimo 50 imagens)</p>
          <p>3. Anote as imagens desenhando bounding boxes ao redor dos produtos</p>
          <p>4. Treine um modelo customizado de YOLO com as imagens anotadas</p>
          <p>5. Use o modelo treinado para contar produtos automaticamente em tempo real</p>
        </CardContent>
      </Card>
    </div>
  )
}
