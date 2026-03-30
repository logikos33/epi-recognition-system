'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { Loader2 } from 'lucide-react'
import { HexColorPicker } from 'react-colorful'
import { api } from '@/lib/api'

interface YOLOClass {
  id: number
  nome: string
  descricao: string | null
  valor_unitario: number
  unidade: string
  cor_hex: string
  ativo: boolean
  class_index: number
}

interface ClassFormModalProps {
  open: boolean
  onClose: () => void
  classToEdit: YOLOClass | null
  onSuccess: () => void
}

export function ClassFormModal({ open, onClose, classToEdit, onSuccess }: ClassFormModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [nome, setNome] = useState(classToEdit?.nome || '')
  const [descricao, setDescricao] = useState(classToEdit?.descricao || '')
  const [valorUnitario, setValorUnitario] = useState(classToEdit?.valor_unitario?.toString() || '0.00')
  const [unidade, setUnidade] = useState(classToEdit?.unidade || 'unidade')
  const [corHex, setCorHex] = useState(classToEdit?.cor_hex || '#00FF00')
  const [ativo, setAtivo] = useState(classToEdit ? classToEdit.ativo : true)

  useEffect(() => {
    if (open) {
      setNome(classToEdit?.nome || '')
      setDescricao(classToEdit?.descricao || '')
      setValorUnitario(classToEdit?.valor_unitario?.toString() || '0.00')
      setUnidade(classToEdit?.unidade || 'unidade')
      setCorHex(classToEdit?.cor_hex || '#00FF00')
      setAtivo(classToEdit ? classToEdit.ativo : true)
      setError('')
    }
  }, [open, classToEdit])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const payload: any = {
        nome,
        descricao,
        valor_unitario: parseFloat(valorUnitario),
        unidade,
        cor_hex: corHex,
        ativo
      }

      if (classToEdit) {
        // Update existing class
        await api.patch(`/api/classes/${classToEdit.id}`, payload)
      } else {
        // Create new class
        await api.post('/api/classes', payload)
      }

      onSuccess()
      onClose()
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Erro ao salvar classe')
    } finally {
      setLoading(false)
    }
  }

  const isEditMode = classToEdit !== null

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {isEditMode ? 'Editar Classe' : 'Nova Classe YOLO'}
          </DialogTitle>
          <DialogDescription>
            {isEditMode
              ? `Editando: ${classToEdit.nome} (Índice ${classToEdit.class_index})`
              : 'Configure uma nova classe para detecção automática'
            }
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Nome */}
          <div className="space-y-2">
            <Label htmlFor="nome">Nome da Classe *</Label>
            <Input
              id="nome"
              placeholder="Ex: EPI_Capacete"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              disabled={loading}
              required
            />
            <p className="text-xs text-muted-foreground">
              Use nomes descritivos sem espaços (snake_case)
            </p>
          </div>

          {/* Descrição */}
          <div className="space-y-2">
            <Label htmlFor="descricao">Descrição</Label>
            <Textarea
              id="descricao"
              placeholder="Descreva o que esta classe detecta..."
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              disabled={loading}
              rows={2}
            />
          </div>

          {/* Valor Unitário e Unidade */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="valor">Valor Unitário (R$)</Label>
              <Input
                id="valor"
                type="number"
                step="0.01"
                placeholder="0.00"
                value={valorUnitario}
                onChange={(e) => setValorUnitario(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="unidade">Unidade</Label>
              <Input
                id="unidade"
                placeholder="unidade"
                value={unidade}
                onChange={(e) => setUnidade(e.target.value)}
                disabled={loading}
                required
              />
              <p className="text-xs text-muted-foreground">
                Ex: unidade, kg, litro, caixa, par
              </p>
            </div>
          </div>

          {/* Cor */}
          <div className="space-y-2">
            <Label htmlFor="cor">Cor do Bounding Box</Label>
            <div className="flex items-center gap-4">
              <HexColorPicker
                color={corHex}
                onChange={setCorHex}
                styles={{
                  default: {
                    hex: true
                  }
                }}
              />
              <Input
                id="cor"
                type="text"
                value={corHex}
                onChange={(e) => setCorHex(e.target.value)}
                disabled={loading}
                maxLength={7}
                className="w-32"
              />
              <div
                className="w-16 h-16 rounded border"
                style={{ backgroundColor: corHex }}
              />
            </div>
          </div>

          {/* Ativo */}
          {isEditMode && (
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <Label htmlFor="ativo" className="font-semibold">Classe Ativa</Label>
                <p className="text-xs text-muted-foreground">
                  Classes inativas não são usadas na detecção
                </p>
              </div>
              <Switch
                id="ativo"
                checked={ativo}
                onCheckedChange={setAtivo}
                disabled={loading}
              />
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={loading}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={loading}>
              {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {isEditMode ? 'Salvar' : 'Criar'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
