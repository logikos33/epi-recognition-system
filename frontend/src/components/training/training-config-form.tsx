'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Clock, Cpu, RotateCcw, Play, Save } from 'lucide-react'
import type { TrainingConfig } from '@/types/training'

interface AugmentationConfig {
  flip: boolean
  rotate: number
  blur: boolean
  mosaic: boolean
  mixup: boolean
}

interface TrainingConfigFormProps {
  projectId: string
  onTrainStart: (config: TrainingConfig & { augmentation: AugmentationConfig; device: string; model: string }) => void
  loading?: boolean
  datasetStats?: {
    totalFrames: number
    annotatedFrames: number
    totalAnnotations: number
  }
}

export function TrainingConfigForm({
  projectId,
  onTrainStart,
  loading = false,
  datasetStats
}: TrainingConfigFormProps) {
  const [config, setConfig] = useState<TrainingConfig>({
    epochs: 100,
    batch_size: 16,
    image_size: 640,
    learning_rate: 0.001,
    optimizer: 'adam',
    train_val_split: 0.8
  })

  const [augmentation, setAugmentation] = useState<AugmentationConfig>({
    flip: true,
    rotate: 0,
    blur: false,
    mosaic: true,
    mixup: false
  })

  const [device, setDevice] = useState<'cpu' | 'gpu'>('cpu')
  const [model, setModel] = useState<'yolov8n' | 'yolov8s' | 'yolov8m'>('yolov8n')

  // Calculate estimated training time (rough estimate in minutes)
  const estimateTrainingTime = () => {
    const baseTimePerEpoch = {
      yolov8n: 0.5,
      yolov8s: 1,
      yolov8m: 2
    }

    const deviceMultiplier = device === 'gpu' ? 0.3 : 1
    const batchMultiplier = config.batch_size / 16
    const samplesPerEpoch = (datasetStats?.annotatedFrames || 100) * config.train_val_split

    const timePerEpoch = (baseTimePerEpoch[model] * deviceMultiplier * (samplesPerEpoch / 100))
    const totalTime = timePerEpoch * config.epochs

    return Math.round(totalTime)
  }

  const estimatedMinutes = estimateTrainingTime()
  const estimatedHours = Math.floor(estimatedMinutes / 60)
  const estimatedMins = estimatedMinutes % 60

  const resetToDefaults = () => {
    setConfig({
      epochs: 100,
      batch_size: 16,
      image_size: 640,
      learning_rate: 0.001,
      optimizer: 'adam',
      train_val_split: 0.8
    })
    setAugmentation({
      flip: true,
      rotate: 0,
      blur: false,
      mosaic: true,
      mixup: false
    })
    setDevice('cpu')
    setModel('yolov8n')
  }

  const handleStartTraining = () => {
    onTrainStart({
      ...config,
      augmentation,
      device,
      model
    })
  }

  return (
    <div className="space-y-6">
      {/* Dataset Info Card */}
      {datasetStats && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Informações do Dataset</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Frames Totais</p>
                <p className="text-2xl font-bold">{datasetStats.totalFrames}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Frames Anotados</p>
                <p className="text-2xl font-bold text-green-600">{datasetStats.annotatedFrames}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Anotações</p>
                <p className="text-2xl font-bold">{datasetStats.totalAnnotations}</p>
              </div>
            </div>
            <div className="mt-3 pt-3 border-t">
              <p className="text-xs text-muted-foreground">
                Split: <span className="font-medium">{Math.round(config.train_val_split * 100)}% treino</span> /{' '}
                <span className="font-medium">{Math.round((1 - config.train_val_split) * 100)}% validação</span>
              </p>
              <p className="text-xs text-muted-foreground">
                Amostras de treino: ~{Math.round(datasetStats.annotatedFrames * config.train_val_split)} | Amostras de validação: ~{Math.round(datasetStats.annotatedFrames * (1 - config.train_val_split))}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Hyperparameters Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Hiperparâmetros de Treinamento</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Model Selection */}
          <div className="space-y-2">
            <Label htmlFor="model">
              Modelo YOLOv8
              <span className="ml-2 text-xs text-muted-foreground">(tamanho do modelo afeta velocidade e precisão)</span>
            </Label>
            <Select
              id="model"
              value={model}
              onChange={(e) => setModel(e.target.value as any)}
              disabled={loading}
            >
              <option value="yolov8n">YOLOv8n (Nano) - Mais rápido, menos preciso</option>
              <option value="yolov8s">YOLOv8s (Small) - Equilibrado</option>
              <option value="yolov8m">YOLOv8m (Medium) - Mais preciso, mais lento</option>
            </Select>
          </div>

          {/* Epochs and Batch Size */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="epochs">
                Épocas
                <span className="ml-2 text-xs text-muted-foreground">(iterações completas sobre o dataset)</span>
              </Label>
              <Input
                id="epochs"
                type="number"
                value={config.epochs}
                onChange={(e) => setConfig({ ...config, epochs: parseInt(e.target.value) || 10 })}
                min={10}
                max={300}
                disabled={loading}
              />
              <p className="text-xs text-muted-foreground">
                Recomendado: 50-150 épocas para detecção de EPIs
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="batch">
                Batch Size
                <span className="ml-2 text-xs text-muted-foreground">(amostras por iteração)</span>
              </Label>
              <Select
                id="batch"
                value={config.batch_size.toString()}
                onChange={(e) => setConfig({ ...config, batch_size: parseInt(e.target.value) })}
                disabled={loading}
              >
                <option value="8">8 (para GPU com 4GB VRAM)</option>
                <option value="16">16 (para GPU com 8GB VRAM)</option>
                <option value="32">32 (para GPU com 16GB VRAM)</option>
                <option value="64">64 (para GPU com 32GB+ VRAM)</option>
              </Select>
              <p className="text-xs text-muted-foreground">
                Maior batch = treinamento mais estável, mas exige mais memória
              </p>
            </div>
          </div>

          {/* Image Size and Learning Rate */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="imgsz">
                Tamanho da Imagem
                <span className="ml-2 text-xs text-muted-foreground">(resolução de entrada)</span>
              </Label>
              <Select
                id="imgsz"
                value={config.image_size.toString()}
                onChange={(e) => setConfig({ ...config, image_size: parseInt(e.target.value) })}
                disabled={loading}
              >
                <option value="320">320x320 (mais rápido, menos preciso)</option>
                <option value="640">640x640 (recomendado para EPIs)</option>
                <option value="1280">1280x1280 (objetos pequenos)</option>
              </Select>
              <p className="text-xs text-muted-foreground">
                640px é ideal para detecção de EPIs em caminhões
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="lr">
                Learning Rate
                <span className="ml-2 text-xs text-muted-foreground">(taxa de aprendizado)</span>
              </Label>
              <div className="flex gap-2">
                <Input
                  id="lr"
                  type="number"
                  step="0.0001"
                  value={config.learning_rate}
                  onChange={(e) => setConfig({ ...config, learning_rate: parseFloat(e.target.value) || 0.0001 })}
                  min={0.0001}
                  max={0.1}
                  disabled={loading}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setConfig({ ...config, learning_rate: 0.001 })}
                  disabled={loading}
                >
                  Reset
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Padrão: 0.001 (Adam), 0.01 (SGD)
              </p>
            </div>
          </div>

          {/* Optimizer */}
          <div className="space-y-2">
            <Label htmlFor="optimizer">
              Otimizador
              <span className="ml-2 text-xs text-muted-foreground">(algoritmo de atualização de pesos)</span>
            </Label>
            <Select
              id="optimizer"
              value={config.optimizer}
              onChange={(e) => setConfig({ ...config, optimizer: e.target.value as any })}
              disabled={loading}
            >
              <option value="adam">Adam (recomendado - converge rápido)</option>
              <option value="adamw">AdamW (com decay de peso corrigido)</option>
              <option value="sgd">SGD (mais lento, mas pode generalizar melhor)</option>
            </Select>
          </div>

          {/* Train/Val Split */}
          <div className="space-y-2">
            <Label htmlFor="split">
              Split Treino/Validação
              <span className="ml-2 text-xs text-muted-foreground">(proporção para validação)</span>
            </Label>
            <div className="flex items-center gap-4">
              <Input
                id="split"
                type="number"
                step="0.05"
                value={config.train_val_split}
                onChange={(e) => setConfig({ ...config, train_val_split: parseFloat(e.target.value) || 0.1 })}
                min={0.1}
                max={0.9}
                disabled={loading}
                className="flex-1"
              />
              <div className="text-sm font-medium min-w-[150px]">
                {Math.round(config.train_val_split * 100)}% treino / {Math.round((1 - config.train_val_split) * 100)}% val
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Padrão: 80% treino, 20% validação. Use mais validação (0.7-0.75) com datasets pequenos
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Augmentation Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Augmentação de Dados</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            A augmentação cria variações artificiais das imagens para melhorar a generalização do modelo
          </p>

          {/* Flip */}
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <Label htmlFor="flip" className="cursor-pointer">
                Flip Horizontal
                <span className="ml-2 text-xs text-muted-foreground">(espelhar imagem)</span>
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Simula objetos vistos de ângulos opostos
              </p>
            </div>
            <input
              id="flip"
              type="checkbox"
              checked={augmentation.flip}
              onChange={(e) => setAugmentation({ ...augmentation, flip: e.target.checked })}
              disabled={loading}
              className="h-4 w-4"
            />
          </div>

          {/* Rotate */}
          <div className="space-y-2">
            <Label htmlFor="rotate">
              Rotação Máxima
              <span className="ml-2 text-xs text-muted-foreground">(graus)</span>
            </Label>
            <Input
              id="rotate"
              type="number"
              value={augmentation.rotate}
              onChange={(e) => setAugmentation({ ...augmentation, rotate: parseInt(e.target.value) || 0 })}
              min={0}
              max={180}
              step={15}
              disabled={loading}
            />
            <p className="text-xs text-muted-foreground">
              0° = desativado, 90° = rotação até 90 graus, 180° = rotação completa
            </p>
          </div>

          {/* Blur */}
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <Label htmlFor="blur" className="cursor-pointer">
                Blur
                <span className="ml-2 text-xs text-muted-foreground">(desfoque)</span>
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Simula imagens fora de foco ou condições de baixa luminosidade
              </p>
            </div>
            <input
              id="blur"
              type="checkbox"
              checked={augmentation.blur}
              onChange={(e) => setAugmentation({ ...augmentation, blur: e.target.checked })}
              disabled={loading}
              className="h-4 w-4"
            />
          </div>

          {/* Mosaic */}
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <Label htmlFor="mosaic" className="cursor-pointer">
                Mosaic
                <span className="ml-2 text-xs text-muted-foreground">(combina 4 imagens)</span>
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Altamente recomendado para detecção de múltiplos objetos
              </p>
            </div>
            <input
              id="mosaic"
              type="checkbox"
              checked={augmentation.mosaic}
              onChange={(e) => setAugmentation({ ...augmentation, mosaic: e.target.checked })}
              disabled={loading}
              className="h-4 w-4"
            />
          </div>

          {/* Mixup */}
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <Label htmlFor="mixup" className="cursor-pointer">
                Mixup
                <span className="ml-2 text-xs text-muted-foreground">(mistura duas imagens)</span>
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Mistura patches de duas imagens com suas labels
              </p>
            </div>
            <input
              id="mixup"
              type="checkbox"
              checked={augmentation.mixup}
              onChange={(e) => setAugmentation({ ...augmentation, mixup: e.target.checked })}
              disabled={loading}
              className="h-4 w-4"
            />
          </div>
        </CardContent>
      </Card>

      {/* Device and Estimated Time Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Dispositivo e Estimativa</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Device Selection */}
          <div className="space-y-2">
            <Label htmlFor="device">
              Dispositivo de Treinamento
              <span className="ml-2 text-xs text-muted-foreground">(CPU é lento, GPU é recomendado)</span>
            </Label>
            <Select
              id="device"
              value={device}
              onChange={(e) => setDevice(e.target.value as any)}
              disabled={loading}
            >
              <option value="cpu">CPU (lento, use só para testes)</option>
              <option value="gpu">GPU (recomendado - NVIDIA CUDA)</option>
            </Select>
          </div>

          {/* Estimated Time */}
          <div className="p-4 bg-muted rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="h-5 w-5 text-muted-foreground" />
              <p className="font-medium">Tempo Estimado de Treinamento</p>
            </div>
            {estimatedHours > 0 ? (
              <p className="text-2xl font-bold">
                ~{estimatedHours}h {estimatedMins}m
              </p>
            ) : (
              <p className="text-2xl font-bold">~{estimatedMins} minutos</p>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Baseado em {config.epochs} épocas, modelo {model}, batch {config.batch_size}, dispositivo {device.toUpperCase()}
            </p>
            <p className="text-xs text-muted-foreground">
              {datasetStats?.annotatedFrames || 0} frames anotados, {Math.round(config.train_val_split * 100)}% para treino
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <Button
          onClick={handleStartTraining}
          disabled={loading || (datasetStats?.annotatedFrames || 0) === 0}
          className="flex-1"
        >
          <Play className="h-4 w-4 mr-2" />
          {loading ? 'Iniciando treinamento...' : 'Iniciar Treinamento'}
        </Button>
        <Button
          onClick={resetToDefaults}
          variant="outline"
          disabled={loading}
        >
          <RotateCcw className="h-4 w-4 mr-2" />
          Resetar para Padrões
        </Button>
      </div>

      {/* Validation Warning */}
      {(datasetStats?.annotatedFrames || 0) === 0 && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-4">
            <p className="text-sm text-yellow-800">
              <strong>Aviso:</strong> Você precisa anotar pelo menos alguns frames antes de iniciar o treinamento.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
