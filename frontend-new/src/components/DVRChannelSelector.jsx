import { useState } from 'react'
import { useDVRDiscovery } from '../hooks/useDVRDiscovery'

export function DVRChannelSelector({ dvrId, onImport }) {
  const { channels, loading, error, discover } = useDVRDiscovery(dvrId)
  const [selected, setSelected] = useState([])
  const [importing, setImporting] = useState(false)

  const toggle = (num) => setSelected(s =>
    s.includes(num) ? s.filter(n => n !== num) : [...s, num]
  )

  const handleImport = async () => {
    if (!selected.length) return
    setImporting(true)
    try {
      const token = localStorage.getItem('token') || sessionStorage.getItem('token')
      const res = await fetch(`/api/cameras/dvrs/${dvrId}/import`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ channel_numbers: selected })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
      if (onImport) onImport(data)
    } catch (err) {
      alert(err.message)
    } finally {
      setImporting(false)
    }
  }

  if (!channels.length && !loading) return (
    <div style={{ textAlign: 'center', padding: 24 }}>
      <p style={{ color: '#6b7280', marginBottom: 16 }}>
        Clique para descobrir os canais disponíveis no DVR.
      </p>
      <button onClick={() => discover(dvrId)}
        style={{ padding: '8px 16px', background: '#3b82f6', color: 'white',
          border: 'none', borderRadius: 6, cursor: 'pointer' }}>
        🔍 Descobrir Canais
      </button>
      {error && <p style={{ color: '#ef4444', marginTop: 12 }}>{error}</p>}
    </div>
  )

  if (loading) return (
    <div style={{ color: '#9ca3af', textAlign: 'center', padding: 24 }}>
      Buscando canais do DVR...
    </div>
  )

  return (
    <div>
      <div style={{ marginBottom: 12, padding: '8px 12px', background: 'rgba(245,158,11,0.1)',
        border: '1px solid rgba(245,158,11,0.3)', borderRadius: 6, color: '#f59e0b', fontSize: 13 }}>
        ⚠️ Selecione apenas as câmeras que serão monitoradas.
        Cada stream ativo consome recursos do servidor.
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
        gap: 8, marginBottom: 16 }}>
        {channels.map(ch => (
          <div key={ch.number} onClick={() => toggle(ch.number)}
            style={{ padding: 12, border: `2px solid ${selected.includes(ch.number) ? '#3b82f6' : '#374151'}`,
              borderRadius: 8, cursor: 'pointer', background: selected.includes(ch.number) ? 'rgba(59,130,246,0.1)' : '#1f2937',
              transition: 'all 0.15s' }}>
            <div style={{ fontWeight: 600, color: 'white', marginBottom: 4 }}>
              Canal {ch.number}
            </div>
            <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 4 }}>
              {ch.name || `Canal ${ch.number}`}
            </div>
            <div style={{ fontSize: 11,
              color: ch.has_signal ? '#10b981' : '#6b7280' }}>
              {ch.has_signal ? '● Com sinal' : '○ Sem sinal'}
            </div>
            {selected.includes(ch.number) && (
              <div style={{ marginTop: 6, fontSize: 11, color: '#3b82f6' }}>✓ Selecionado</div>
            )}
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ color: '#9ca3af', fontSize: 13 }}>
          {selected.length} canal(is) selecionado(s)
        </span>
        <button onClick={handleImport}
          disabled={!selected.length || importing}
          style={{ padding: '8px 16px', background: selected.length ? '#10b981' : '#374151',
            color: 'white', border: 'none', borderRadius: 6,
            cursor: selected.length ? 'pointer' : 'not-allowed', fontSize: 14 }}>
          {importing ? 'Importando...' : `Importar Selecionados (${selected.length})`}
        </button>
      </div>
    </div>
  )
}
