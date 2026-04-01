import { useState } from 'react'
import { useCameraConnection } from '../hooks/useCameraConnection'

export function ConnectionTestBadge({ config, onSuccess }) {
  const { test, testing, result, snapshotBase64, error, reset } = useCameraConnection()
  const [layer, setLayer] = useState(0)

  const handleTest = async () => {
    reset()
    setLayer(1)
    try {
      const res = await test(config)
      setLayer(5)
      if (onSuccess) onSuccess(res)
    } catch {
      setLayer(0)
    }
  }

  if (testing) return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#f59e0b' }}>
      <div style={{ width: 16, height: 16, border: '2px solid #f59e0b',
        borderTopColor: 'transparent', borderRadius: '50%',
        animation: 'spin 1s linear infinite' }} />
      Verificando camada {layer} de 5...
    </div>
  )

  if (error) return (
    <div style={{ color: '#ef4444', fontSize: 13 }}>
      ❌ {error}
      <button onClick={handleTest}
        style={{ marginLeft: 8, padding: '2px 8px', fontSize: 12,
          background: 'transparent', border: '1px solid #ef4444',
          color: '#ef4444', borderRadius: 4, cursor: 'pointer' }}>
        Tentar novamente
      </button>
    </div>
  )

  if (result?.success) return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ color: '#10b981' }}>
        ✅ Conectado ({result.latency_ms?.toFixed(0)}ms)
      </span>
      {snapshotBase64 && (
        <img
          src={`data:image/jpeg;base64,${snapshotBase64}`}
          alt="Preview da câmera"
          style={{ width: 120, height: 68, objectFit: 'cover',
            borderRadius: 4, border: '1px solid #374151' }}
        />
      )}
    </div>
  )

  return (
    <button onClick={handleTest}
      disabled={!config?.host}
      style={{ padding: '6px 14px', background: '#3b82f6', color: 'white',
        border: 'none', borderRadius: 6, cursor: config?.host ? 'pointer' : 'not-allowed',
        opacity: config?.host ? 1 : 0.5, fontSize: 13 }}>
      🔌 Testar Conexão
    </button>
  )
}
