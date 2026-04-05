'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useCreateTrainingProject } from '@/hooks/useTrainingProjects'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowLeft, Plus, X } from 'lucide-react'
import Link from 'next/link'

export default function NewTrainingProjectPage() {
  const router = useRouter()
  const createProject = useCreateTrainingProject()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [targetClass, setTargetClass] = useState('')
  const [targetClasses, setTargetClasses] = useState<string[]>([])
  const [errors, setErrors] = useState<{ name?: string; targetClasses?: string; general?: string }>({})

  const addTargetClass = () => {
    const trimmed = targetClass.trim().toLowerCase()

    // Validation
    if (!trimmed) {
      return
    }

    if (trimmed.length < 2) {
      setErrors({ ...errors, targetClasses: 'Nome da classe deve ter pelo menos 2 caracteres' })
      return
    }

    if (targetClasses.includes(trimmed)) {
      setErrors({ ...errors, targetClasses: 'Esta classe já foi adicionada' })
      return
    }

    setTargetClasses([...targetClasses, trimmed])
    setTargetClass('')
    setErrors({ ...errors, targetClasses: undefined })
  }

  const removeTargetClass = (cls: string) => {
    setTargetClasses(targetClasses.filter(c => c !== cls))
  }

  const validate = (): boolean => {
    const newErrors: { name?: string; targetClasses?: string } = {}

    // Name validation
    if (!name.trim()) {
      newErrors.name = 'Nome do projeto é obrigatório'
    } else if (name.trim().length < 3) {
      newErrors.name = 'Nome do projeto deve ter pelo menos 3 caracteres'
    }

    // Target classes validation
    if (targetClasses.length === 0) {
      newErrors.targetClasses = 'Pelo menos uma classe de objeto é obrigatória'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) {
      return
    }

    try {
      await createProject.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        target_classes: targetClasses,
      })

      // Redirect to training projects list on success
      router.push('/dashboard/training')
    } catch (error) {
      setErrors({
        ...errors,
        general: error instanceof Error ? error.message : 'Erro ao criar projeto',
      })
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/dashboard/training">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Novo Projeto de Treinamento</h1>
          <p className="text-muted-foreground">
            Crie um projeto para treinar modelo customizado do YOLOv8
          </p>
        </div>
      </div>

      {/* Form */}
      <Card>
        <CardHeader>
          <CardTitle>Informações do Projeto</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* General Error */}
            {errors.general && (
              <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md border border-destructive/20">
                {errors.general}
              </div>
            )}

            {/* Project Name */}
            <div className="space-y-2">
              <Label htmlFor="name">
                Nome do Projeto <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                placeholder="Ex: Detecção de EPIs - Capacete e Colete"
                value={name}
                onChange={(e) => {
                  setName(e.target.value)
                  if (errors.name) setErrors({ ...errors, name: undefined })
                }}
                disabled={createProject.isPending}
                className={errors.name ? 'border-destructive' : ''}
              />
              {errors.name && <p className="text-sm text-destructive">{errors.name}</p>}
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">Descrição</Label>
              <Textarea
                id="description"
                placeholder="Descreva o objetivo deste projeto e quais objetos ele deve detectar..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={createProject.isPending}
                rows={3}
                maxLength={500}
              />
              <p className="text-xs text-muted-foreground text-right">
                {description.length}/500 caracteres
              </p>
            </div>

            {/* Target Classes */}
            <div className="space-y-2">
              <Label>
                Classes de Objetos <span className="text-destructive">*</span>
              </Label>
              <div className="flex gap-2">
                <Input
                  placeholder="Ex: capacete, colete, luvas"
                  value={targetClass}
                  onChange={(e) => {
                    setTargetClass(e.target.value)
                    if (errors.targetClasses) setErrors({ ...errors, targetClasses: undefined })
                  }}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      addTargetClass()
                    }
                  }}
                  disabled={createProject.isPending}
                  className={errors.targetClasses ? 'border-destructive' : ''}
                />
                <Button
                  type="button"
                  onClick={addTargetClass}
                  disabled={createProject.isPending}
                  variant="outline"
                >
                  <Plus className="h-4 w-4" />
                  Adicionar
                </Button>
              </div>

              {errors.targetClasses && (
                <p className="text-sm text-destructive">{errors.targetClasses}</p>
              )}

              {/* Classes List */}
              {targetClasses.length > 0 && (
                <div className="mt-3">
                  <p className="text-sm text-muted-foreground mb-2">
                    Classes adicionadas ({targetClasses.length}):
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {targetClasses.map((cls) => (
                      <div
                        key={cls}
                        className="flex items-center gap-1 px-3 py-1.5 bg-secondary rounded-md text-sm font-medium"
                      >
                        <span className="capitalize">{cls}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-4 w-4 ml-1"
                          onClick={() => removeTargetClass(cls)}
                          disabled={createProject.isPending}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Examples */}
              {targetClasses.length === 0 && (
                <div className="mt-3 p-3 bg-muted/50 rounded-md">
                  <p className="text-xs text-muted-foreground font-medium mb-1">
                    Exemplos de EPIs comuns:
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {['capacete', 'colete', 'luvas', 'bota', 'oculos'].map((example) => (
                      <button
                        key={example}
                        type="button"
                        onClick={() => setTargetClass(example)}
                        className="text-xs px-2 py-1 bg-background border rounded hover:bg-secondary transition-colors"
                        disabled={createProject.isPending}
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Submit Buttons */}
            <div className="flex gap-3 pt-4 border-t">
              <Button
                type="submit"
                disabled={createProject.isPending}
                className="flex-1"
              >
                {createProject.isPending ? 'Criando projeto...' : 'Criar Projeto'}
              </Button>
              <Link href="/dashboard/training" className="flex-1">
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  disabled={createProject.isPending}
                >
                  Cancelar
                </Button>
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Help Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Dicas para um bom projeto</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            <strong className="text-foreground">Classes específicas:</strong> Defina classes
            claras e específicas (ex: &quot;capacete&quot; em vez de &quot;proteção&quot;).
          </p>
          <p>
            <strong className="text-foreground">Múltiplas classes:</strong> Adicione todos os tipos
            de EPIs que deseja detectar em um único projeto.
          </p>
          <p>
            <strong className="text-foreground">Nome descritivo:</strong> Use um nome que facilite
            identificar o propósito do projeto.
          </p>
          <p>
            <strong className="text-foreground">Próximos passos:</strong> Após criar o projeto, você
            fará upload de vídeos e anotará os frames manualmente.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
