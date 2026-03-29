// frontend/src/components/monitoring/InfoOverlay.tsx
'use client'

import { useMemo } from 'react'
import type { SessionInfo } from '@/types/monitoring'
import { Badge } from '@/components/ui/badge'
import { Clock, Package, Scale, Activity } from 'lucide-react'

interface InfoOverlayProps {
  sessionInfo: SessionInfo | null
  className?: string
}

/**
 * Semi-transparent overlay showing session information
 */
export function InfoOverlay({ sessionInfo, className = '' }: InfoOverlayProps) {
  const statusColor = useMemo(() => {
    switch (sessionInfo?.status) {
      case 'active':
        return 'bg-green-500/20 text-green-700 border-green-500/30'
      case 'completed':
        return 'bg-blue-500/20 text-blue-700 border-blue-500/30'
      case 'paused':
        return 'bg-yellow-500/20 text-yellow-700 border-yellow-500/30'
      default:
        return 'bg-gray-500/20 text-gray-700 border-gray-500/30'
    }
  }, [sessionInfo?.status])

  const statusLabel = useMemo(() => {
    switch (sessionInfo?.status) {
      case 'active':
        return 'Ativo'
      case 'completed':
        return 'Concluído'
      case 'paused':
        return 'Pausado'
      default:
        return 'Desconhecido'
    }
  }, [sessionInfo?.status])

  if (!sessionInfo) {
    return (
      <div className={`absolute top-0 left-0 right-0 bg-black/70 backdrop-blur-sm p-4 ${className}`}>
        <p className="text-white/70 text-sm">Nenhuma sessão ativa</p>
      </div>
    )
  }

  return (
    <div className={`absolute top-0 left-0 right-0 bg-black/70 backdrop-blur-sm p-4 ${className}`}>
      <div className="flex items-center justify-between">
        {/* Left: License plate and time */}
        <div className="flex items-center gap-6">
          {/* License plate */}
          {sessionInfo.licensePlate && (
            <div className="flex items-center gap-2">
              <div className="bg-white text-black px-3 py-1 rounded font-bold text-lg tracking-wider">
                {sessionInfo.licensePlate}
              </div>
            </div>
          )}

          {/* Entry time */}
          {sessionInfo.entryTime && (
            <div className="flex items-center gap-2 text-white">
              <Clock className="w-4 h-4" />
              <span className="text-sm">
                Entrada: {(sessionInfo.entryTime instanceof Date ? sessionInfo.entryTime : new Date(sessionInfo.entryTime)).toLocaleTimeString('pt-BR')}
              </span>
            </div>
          )}

          {/* Elapsed time */}
          {sessionInfo.elapsedTime && (
            <div className="flex items-center gap-2 text-white">
              <Activity className="w-4 h-4" />
              <span className="text-sm font-mono">{sessionInfo.elapsedTime}</span>
            </div>
          )}
        </div>

        {/* Right: Products, weight, status */}
        <div className="flex items-center gap-4">
          {/* Product count */}
          {sessionInfo.productCount > 0 && (
            <div className="flex items-center gap-2 text-white">
              <Package className="w-4 h-4" />
              <span className="text-sm font-semibold">{sessionInfo.productCount}</span>
            </div>
          )}

          {/* Weight */}
          {sessionInfo.currentWeight > 0 && (
            <div className="flex items-center gap-2 text-white">
              <Scale className="w-4 h-4" />
              <span className="text-sm font-mono">{sessionInfo.currentWeight} kg</span>
            </div>
          )}

          {/* Status badge */}
          <Badge className={statusColor}>{statusLabel}</Badge>
        </div>
      </div>
    </div>
  )
}