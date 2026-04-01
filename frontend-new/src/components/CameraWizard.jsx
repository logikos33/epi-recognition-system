import { useState } from 'react'
import { ConnectionTestBadge } from './ConnectionTestBadge'
import { DVRChannelSelector } from './DVRChannelSelector'

const MANUFACTURERS = ['intelbras', 'hikvision', 'dahua', 'axis', 'generic']

const CONNECTION_TYPES = [
  { id: 'individual', icon: '📷', label: 'Câmera IP Individual',
    desc: 'Intelbras, Hikvision, Dahua, etc.' },
  { id: 'dvr', icon: '🖥️', label: 'DVR / NVR',
    desc: 'Múltiplos canais em um dispositivo' },
  { id: 'manual', icon: '🔗', label: 'URL RTSP Manual',
    desc: 'Inserir URL completa' },
  { id: 'onvif', icon: '🔍', label: 'Descoberta ONVIF',
    desc: 'Scan automático na rede local' },
]

export function CameraWizard({ onClose, onSaved }) {
  const [step, setStep] = useState(1)
  const [connType, setConnType] = useState(null)
  const [testOk, setTestOk] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [onvifDevices, setOnvifDevices] = useState([])
  const [scanning, setScanning] = useState(false)
  const [dvrId, setDvrId] = useState(null)
  const [channelsImported, setChannelsImported] = useState(false)

  const [cred, setCred] = useState({
    manufacturer: 'intelbras', host: '', port: 554,
    username: 'admin', password: '', channel: 1, subtype: 0,
    rtsp_url: '',
    dvr_host: '', dvr_port: 80, dvr_rtsp_port: 554,
    dvr_username: 'admin', dvr_password: '', dvr_manufacturer: 'intelbras',
  })

  const [info, setInfo] = useState({ name: '', location: '', description: '' })

  const getHeaders = () => {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token')
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    }
  }

  const scanOnvif = async () => {
    setScanning(true)
    try {
      const res = await fetch('/api/cameras/discover/onvif', {
        method: 'POST', headers: getHeaders(),
        body: JSON.stringify({ timeout_seconds: 5 })
      })
      const data = await res.json()
      setOnvifDevices(data.devices || [])
    } catch (err) {
      setError(`Erro ao escanear: ${err.message}`)
    } finally {
      setScanning(false)
    }
  }

  const registerDVR = async () => {
    try {
      const res = await fetch('/api/cameras/dvrs', {
        method: 'POST', headers: getHeaders(),
        body: JSON.stringify({
          name: `DVR ${cred.dvr_host}`,
          host: cred.dvr_host, port: Number(cred.dvr_port),
          rtsp_port: Number(cred.dvr_rtsp_port),
          username: cred.dvr_username, password: cred.dvr_password,
          manufacturer: cred.dvr_manufacturer,
        })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
      setDvrId(data.id)
      setTestOk(true)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleSave = async () => {
    if (!info.name.trim()) { setError('Nome é obrigatório'); return }
    setSaving(true)
    setError(null)
    try {
      const body = {
        name: info.name, location: info.location, description: info.description,
        manufacturer: cred.manufacturer, host: cred.host,
        port: Number(cred.port), username: cred.username,
        password: cred.password, channel: Number(cred.channel),
        subtype: Number(cred.subtype),
      }
      if (connType === 'manual') {
        body.rtsp_url = cred.rtsp_url
        body.manufacturer = 'generic'
      }
      const res = await fetch('/api/cameras', {
        method: 'POST', headers: getHeaders(), body: JSON.stringify(body)
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
      if (onSaved) onSaved(data)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const overlayStyle = {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000
  }
  const modalStyle = {
    background: '#111827', borderRadius: 12, padding: 28,
    width: 560, maxWidth: '95vw', maxHeight: '90vh',
    overflow: 'auto', border: '1px solid #374151'
  }
  const inputStyle = {
    width: '100%', padding: '8px 10px', background: '#1f2937',
    border: '1px solid #374151', borderRadius: 6,
    color: 'white', fontSize: 14, boxSizing: 'border-box'
  }
  const labelStyle = { color: '#9ca3af', fontSize: 12, display: 'block', marginBottom: 4 }

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', marginBottom: 24 }}>
          <div>
            <h2 style={{ color: 'white', margin: 0, fontSize: 18 }}>
              Adicionar Câmera
            </h2>
            <p style={{ color: '#6b7280', margin: '4px 0 0', fontSize: 13 }}>
              Passo {step} de 3
            </p>
          </div>
          <button onClick={onClose}
            style={{ background: 'transparent', border: 'none',
              color: '#6b7280', fontSize: 20, cursor: 'pointer' }}>
            ✕
          </button>
        </div>

        {/* Progress bar */}
        <div style={{ height: 4, background: '#1f2937', borderRadius: 2, marginBottom: 24 }}>
          <div style={{ height: '100%', borderRadius: 2, background: '#3b82f6',
            width: `${(step / 3) * 100}%`, transition: 'width 0.3s' }} />
        </div>

        {/* PASSO 1: Tipo de conexão */}
        {step === 1 && (
          <div>
            <h3 style={{ color: 'white', marginBottom: 16, fontSize: 15 }}>
              Tipo de conexão
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {CONNECTION_TYPES.map(t => (
                <div key={t.id} onClick={() => setConnType(t.id)}
                  style={{ padding: 16, border: `2px solid ${connType === t.id ? '#3b82f6' : '#374151'}`,
                    borderRadius: 8, cursor: 'pointer',
                    background: connType === t.id ? 'rgba(59,130,246,0.1)' : '#1f2937' }}>
                  <div style={{ fontSize: 24, marginBottom: 6 }}>{t.icon}</div>
                  <div style={{ color: 'white', fontWeight: 600, fontSize: 13 }}>{t.label}</div>
                  <div style={{ color: '#6b7280', fontSize: 11, marginTop: 2 }}>{t.desc}</div>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 20 }}>
              <button onClick={() => { setStep(2); setError(null) }}
                disabled={!connType}
                style={{ padding: '8px 20px', background: connType ? '#3b82f6' : '#374151',
                  color: 'white', border: 'none', borderRadius: 6,
                  cursor: connType ? 'pointer' : 'not-allowed', fontSize: 14 }}>
                Próximo →
              </button>
            </div>
          </div>
        )}

        {/* PASSO 2: Credenciais */}
        {step === 2 && (
          <div>
            <h3 style={{ color: 'white', marginBottom: 16, fontSize: 15 }}>
              {connType === 'dvr' ? 'Dados do DVR' :
               connType === 'manual' ? 'URL RTSP' :
               connType === 'onvif' ? 'Descoberta ONVIF' : 'Credenciais da câmera'}
            </h3>

            {/* Câmera individual */}
            {connType === 'individual' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <label style={labelStyle}>Fabricante</label>
                  <select style={inputStyle} value={cred.manufacturer}
                    onChange={e => setCred(c => ({...c, manufacturer: e.target.value}))}>
                    {MANUFACTURERS.map(m => (
                      <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8 }}>
                  <div>
                    <label style={labelStyle}>Host / IP *</label>
                    <input style={inputStyle} value={cred.host} placeholder="192.168.1.100"
                      onChange={e => setCred(c => ({...c, host: e.target.value}))} />
                  </div>
                  <div>
                    <label style={labelStyle}>Porta RTSP</label>
                    <input style={{...inputStyle, width: 80}} type="number" value={cred.port}
                      onChange={e => setCred(c => ({...c, port: e.target.value}))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <label style={labelStyle}>Usuário</label>
                    <input style={inputStyle} value={cred.username}
                      onChange={e => setCred(c => ({...c, username: e.target.value}))} />
                  </div>
                  <div>
                    <label style={labelStyle}>Senha</label>
                    <input style={inputStyle} type="password" value={cred.password}
                      onChange={e => setCred(c => ({...c, password: e.target.value}))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <label style={labelStyle}>Canal</label>
                    <input style={inputStyle} type="number" min="1" value={cred.channel}
                      onChange={e => setCred(c => ({...c, channel: e.target.value}))} />
                  </div>
                  <div>
                    <label style={labelStyle}>Stream</label>
                    <select style={inputStyle} value={cred.subtype}
                      onChange={e => setCred(c => ({...c, subtype: e.target.value}))}>
                      <option value={0}>Main (Alta qualidade)</option>
                      <option value={1}>Sub (Preview)</option>
                    </select>
                  </div>
                </div>
                <ConnectionTestBadge config={cred} onSuccess={() => setTestOk(true)} />
              </div>
            )}

            {/* DVR */}
            {connType === 'dvr' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <label style={labelStyle}>Fabricante DVR</label>
                  <select style={inputStyle} value={cred.dvr_manufacturer}
                    onChange={e => setCred(c => ({...c, dvr_manufacturer: e.target.value}))}>
                    {MANUFACTURERS.filter(m => m !== 'generic').map(m => (
                      <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 8 }}>
                  <div>
                    <label style={labelStyle}>IP do DVR *</label>
                    <input style={inputStyle} value={cred.dvr_host} placeholder="192.168.1.64"
                      onChange={e => setCred(c => ({...c, dvr_host: e.target.value}))} />
                  </div>
                  <div>
                    <label style={labelStyle}>Porta HTTP</label>
                    <input style={{...inputStyle, width: 70}} type="number" value={cred.dvr_port}
                      onChange={e => setCred(c => ({...c, dvr_port: e.target.value}))} />
                  </div>
                  <div>
                    <label style={labelStyle}>Porta RTSP</label>
                    <input style={{...inputStyle, width: 70}} type="number" value={cred.dvr_rtsp_port}
                      onChange={e => setCred(c => ({...c, dvr_rtsp_port: e.target.value}))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <label style={labelStyle}>Usuário</label>
                    <input style={inputStyle} value={cred.dvr_username}
                      onChange={e => setCred(c => ({...c, dvr_username: e.target.value}))} />
                  </div>
                  <div>
                    <label style={labelStyle}>Senha</label>
                    <input style={inputStyle} type="password" value={cred.dvr_password}
                      onChange={e => setCred(c => ({...c, dvr_password: e.target.value}))} />
                  </div>
                </div>
                <button onClick={registerDVR} disabled={!cred.dvr_host}
                  style={{ padding: '8px 14px', background: '#3b82f6', color: 'white',
                    border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
                  🔌 Conectar ao DVR e descobrir canais
                </button>
                {dvrId && (
                  <DVRChannelSelector dvrId={dvrId}
                    onImport={() => { setChannelsImported(true); setTestOk(true) }} />
                )}
              </div>
            )}

            {/* URL Manual */}
            {connType === 'manual' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                  <label style={labelStyle}>URL RTSP completa *</label>
                  <input style={inputStyle} value={cred.rtsp_url}
                    placeholder="rtsp://user:pass@192.168.1.100:554/stream1"
                    onChange={e => setCred(c => ({...c, rtsp_url: e.target.value}))} />
                </div>
                <ConnectionTestBadge
                  config={{ rtsp_url: cred.rtsp_url, manufacturer: 'generic' }}
                  onSuccess={() => setTestOk(true)} />
              </div>
            )}

            {/* ONVIF */}
            {connType === 'onvif' && (
              <div>
                <button onClick={scanOnvif} disabled={scanning}
                  style={{ padding: '8px 16px', background: '#7c3aed', color: 'white',
                    border: 'none', borderRadius: 6, cursor: 'pointer', marginBottom: 16 }}>
                  {scanning ? '🔍 Escaneando...' : '🔍 Escanear Rede Local'}
                </button>
                {onvifDevices.map((d, i) => (
                  <div key={i} onClick={() => {
                    setCred(c => ({...c, host: d.ip, manufacturer: d.manufacturer || 'generic'}))
                    setTestOk(true)
                  }} style={{ padding: 12, border: '1px solid #374151',
                    borderRadius: 8, marginBottom: 8, cursor: 'pointer',
                    background: cred.host === d.ip ? 'rgba(59,130,246,0.1)' : '#1f2937' }}>
                    <div style={{ color: 'white', fontWeight: 600 }}>{d.ip}</div>
                    <div style={{ color: '#9ca3af', fontSize: 12 }}>
                      {d.manufacturer} — {d.model}
                    </div>
                  </div>
                ))}
                {!onvifDevices.length && !scanning && (
                  <p style={{ color: '#6b7280', fontSize: 13 }}>
                    Nenhum dispositivo encontrado ainda.
                  </p>
                )}
              </div>
            )}

            {error && (
              <div style={{ color: '#ef4444', fontSize: 13, marginTop: 8,
                padding: '8px 12px', background: 'rgba(239,68,68,0.1)', borderRadius: 6 }}>
                {error}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 20 }}>
              <button onClick={() => { setStep(1); setError(null) }}
                style={{ padding: '8px 16px', background: 'transparent',
                  border: '1px solid #374151', color: '#9ca3af',
                  borderRadius: 6, cursor: 'pointer', fontSize: 14 }}>
                ← Voltar
              </button>
              <button onClick={() => { setStep(3); setError(null) }}
                disabled={!testOk}
                style={{ padding: '8px 20px',
                  background: testOk ? '#3b82f6' : '#374151',
                  color: 'white', border: 'none', borderRadius: 6,
                  cursor: testOk ? 'pointer' : 'not-allowed', fontSize: 14 }}>
                Próximo →
              </button>
            </div>
          </div>
        )}

        {/* PASSO 3: Identificação */}
        {step === 3 && (
          <div>
            <h3 style={{ color: 'white', marginBottom: 16, fontSize: 15 }}>
              Identificar câmera
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={labelStyle}>Nome *</label>
                <input style={inputStyle} value={info.name}
                  placeholder="ex: Câmera Baia 1"
                  onChange={e => setInfo(i => ({...i, name: e.target.value}))} />
              </div>
              <div>
                <label style={labelStyle}>Localização</label>
                <input style={inputStyle} value={info.location}
                  placeholder="ex: Baia 1 - Portão Leste"
                  onChange={e => setInfo(i => ({...i, location: e.target.value}))} />
              </div>
              <div>
                <label style={labelStyle}>Descrição</label>
                <input style={inputStyle} value={info.description}
                  onChange={e => setInfo(i => ({...i, description: e.target.value}))} />
              </div>
              <div style={{ padding: 12, background: '#1f2937',
                borderRadius: 8, fontSize: 12, color: '#9ca3af' }}>
                <div style={{ color: '#6b7280', marginBottom: 6, fontWeight: 600 }}>
                  Resumo:
                </div>
                <div>Tipo: {connType}</div>
                <div>Fabricante: {cred.manufacturer}</div>
                {cred.host && <div>Host: {cred.host}:{cred.port}</div>}
                {cred.channel && <div>Canal: {cred.channel}</div>}
              </div>
            </div>
            {error && (
              <div style={{ color: '#ef4444', fontSize: 13, marginTop: 12,
                padding: '8px 12px', background: 'rgba(239,68,68,0.1)', borderRadius: 6 }}>
                {error}
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 20 }}>
              <button onClick={() => { setStep(2); setError(null) }}
                style={{ padding: '8px 16px', background: 'transparent',
                  border: '1px solid #374151', color: '#9ca3af',
                  borderRadius: 6, cursor: 'pointer', fontSize: 14 }}>
                ← Voltar
              </button>
              <button onClick={handleSave} disabled={saving || !info.name.trim()}
                style={{ padding: '8px 20px',
                  background: info.name.trim() ? '#10b981' : '#374151',
                  color: 'white', border: 'none', borderRadius: 6,
                  cursor: info.name.trim() ? 'pointer' : 'not-allowed', fontSize: 14 }}>
                {saving ? 'Salvando...' : '💾 Salvar Câmera'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
