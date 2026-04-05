import { useState } from 'react'

export function CameraEditModal({ camera, isConfigMode, onClose, onSave }) {
  const [form, setForm] = useState({
    name: camera?.name || '',
    location: camera?.location || '',
    description: camera?.description || '',
    host: camera?.host || '',
    port: camera?.port || 554,
    username: camera?.username || '',
    password: '',
    channel: camera?.channel || 1,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleSave = async () => {
    if (!form.name.trim()) { setError('Nome é obrigatório'); return }
    setSaving(true)
    setError(null)
    try {
      const token = localStorage.getItem('token') || sessionStorage.getItem('token')
      const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      }
      const body = { name: form.name, location: form.location, description: form.description }
      if (isConfigMode) {
        Object.assign(body, {
          host: form.host, port: Number(form.port),
          username: form.username, channel: Number(form.channel),
          ...(form.password ? { password: form.password } : {})
        })
      }
      const res = await fetch(`/api/cameras/${camera.id}`, {
        method: 'PUT', headers, body: JSON.stringify(body)
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
      onSave(data)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const inputStyle = {
    width: '100%', padding: '8px 10px', background: '#1f2937',
    border: '1px solid #374151', borderRadius: 6, color: 'white', fontSize: 14
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: '#111827', borderRadius: 12, padding: 24,
        width: 480, maxWidth: '90vw', border: '1px solid #374151' }}>
        <h2 style={{ color: 'white', margin: '0 0 20px', fontSize: 18 }}>
          Editar Câmera
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={{ color: '#9ca3af', fontSize: 12, display: 'block', marginBottom: 4 }}>
              Nome *
            </label>
            <input style={inputStyle} value={form.name}
              onChange={e => setForm(f => ({...f, name: e.target.value}))} />
          </div>
          <div>
            <label style={{ color: '#9ca3af', fontSize: 12, display: 'block', marginBottom: 4 }}>
              Localização
            </label>
            <input style={inputStyle} value={form.location}
              placeholder="ex: Baia 1 - Portão Leste"
              onChange={e => setForm(f => ({...f, location: e.target.value}))} />
          </div>
          <div>
            <label style={{ color: '#9ca3af', fontSize: 12, display: 'block', marginBottom: 4 }}>
              Descrição
            </label>
            <input style={inputStyle} value={form.description}
              onChange={e => setForm(f => ({...f, description: e.target.value}))} />
          </div>
          {isConfigMode && (
            <>
              <div style={{ borderTop: '1px solid #374151', paddingTop: 12,
                color: '#f59e0b', fontSize: 12, marginTop: 4 }}>
                ⚙️ Configurações avançadas (modo configuração ativo)
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8 }}>
                <div>
                  <label style={{ color: '#9ca3af', fontSize: 12, display: 'block', marginBottom: 4 }}>
                    Host/IP
                  </label>
                  <input style={inputStyle} value={form.host}
                    onChange={e => setForm(f => ({...f, host: e.target.value}))} />
                </div>
                <div>
                  <label style={{ color: '#9ca3af', fontSize: 12, display: 'block', marginBottom: 4 }}>
                    Porta
                  </label>
                  <input style={{...inputStyle, width: 80}} type="number" value={form.port}
                    onChange={e => setForm(f => ({...f, port: e.target.value}))} />
                </div>
              </div>
              <div>
                <label style={{ color: '#9ca3af', fontSize: 12, display: 'block', marginBottom: 4 }}>
                  Nova Senha (deixar vazio para não alterar)
                </label>
                <input style={inputStyle} type="password" value={form.password}
                  placeholder="••••••••"
                  onChange={e => setForm(f => ({...f, password: e.target.value}))} />
              </div>
            </>
          )}
          {error && (
            <div style={{ color: '#ef4444', fontSize: 13, padding: '8px 12px',
              background: 'rgba(239,68,68,0.1)', borderRadius: 6 }}>
              {error}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 20, justifyContent: 'flex-end' }}>
          <button onClick={onClose}
            style={{ padding: '8px 16px', background: 'transparent',
              border: '1px solid #374151', color: '#9ca3af',
              borderRadius: 6, cursor: 'pointer', fontSize: 14 }}>
            Cancelar
          </button>
          <button onClick={handleSave} disabled={saving}
            style={{ padding: '8px 16px', background: '#3b82f6', color: 'white',
              border: 'none', borderRadius: 6, cursor: saving ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.7 : 1, fontSize: 14 }}>
            {saving ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  )
}
