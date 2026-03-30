import { useState } from 'react';
import Modal from './Modal';
import { useToast } from '../hooks/useToast';

const Icons = {
  plus: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>,
  check: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>,
};

export default function CameraForm({ isOpen, onClose, camera = null, onSave }) {
  const { success, error } = useToast();
  const [testing, setTesting] = useState(false);

  const isEdit = !!camera;

  const [formData, setFormData] = useState({
    name: camera?.name || '',
    manufacturer: camera?.manufacturer || 'intelbras',
    ip: camera?.ip || '',
    port: camera?.port || 554,
    username: camera?.username || '',
    password: camera?.password || '',
    channel: camera?.channel || 1,
    subtype: camera?.subtype || 1,
    type: camera?.type || 'ip',
    location: camera?.location || '',
    resolution: camera?.resolution || '1080p',
  });

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validations
    if (!formData.name.trim()) {
      error('Nome da câmera é obrigatório');
      return;
    }
    if (!formData.ip.trim()) {
      error('Endereço IP é obrigatório');
      return;
    }

    try {
      await onSave(formData);
      success(isEdit ? 'Câmera atualizada com sucesso!' : 'Câmera criada com sucesso!');
      onClose();
    } catch (err) {
      error(err.message || 'Erro ao salvar câmera');
    }
  };

  const handleTestConnection = async () => {
    if (!formData.ip.trim()) {
      error('Digite o endereço IP primeiro');
      return;
    }

    setTesting(true);
    try {
      const result = await fetch('http://localhost:5001/api/cameras/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          ip: formData.ip,
          port: formData.port,
          username: formData.username,
          password: formData.password,
        }),
      }).then(res => res.json());

      if (result.success || result.reachable) {
        success('Conexão com a câmera estabelecida com sucesso!');
      } else {
        error('Não foi possível conectar à câmera');
      }
    } catch (err) {
      error('Erro ao testar conexão: ' + err.message);
    } finally {
      setTesting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? 'Editar Câmera' : 'Nova Câmera'}
      size="lg"
    >
      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          {/* Name */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: 'var(--text)', marginBottom: '6px' }}>
              Nome *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="Ex: Entrada Principal"
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '14px',
                outline: 'none',
                transition: 'all 0.15s',
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent)';
                e.currentTarget.style.boxShadow = '0 0 0 3px rgba(37,99,235,0.1)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = 'var(--border)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            />
          </div>

          {/* Location */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: 'var(--text)', marginBottom: '6px' }}>
              Localização
            </label>
            <input
              type="text"
              value={formData.location}
              onChange={(e) => handleChange('location', e.target.value)}
              placeholder="Ex: Portaria"
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '14px',
                outline: 'none',
              }}
            />
          </div>

          {/* Manufacturer */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: 'var(--text)', marginBottom: '6px' }}>
              Fabricante *
            </label>
            <select
              value={formData.manufacturer}
              onChange={(e) => handleChange('manufacturer', e.target.value)}
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '14px',
                outline: 'none',
                background: 'var(--card)',
              }}
            >
              <option value="intelbras">Intelbras</option>
              <option value="hikvision">Hikvision</option>
              <option value="generic">Genérico</option>
            </select>
          </div>

          {/* Resolution */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: 'var(--text)', marginBottom: '6px' }}>
              Resolução
            </label>
            <select
              value={formData.resolution}
              onChange={(e) => handleChange('resolution', e.target.value)}
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '14px',
                outline: 'none',
                background: 'var(--card)',
              }}
            >
              <option value="720p">720p HD</option>
              <option value="1080p">1080p Full HD</option>
              <option value="4K">4K Ultra HD</option>
            </select>
          </div>

          {/* IP Address */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: 'var(--text)', marginBottom: '6px' }}>
              Endereço IP *
            </label>
            <input
              type="text"
              value={formData.ip}
              onChange={(e) => handleChange('ip', e.target.value)}
              placeholder="192.168.1.100"
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '14px',
                fontFamily: 'var(--mono)',
                outline: 'none',
              }}
            />
          </div>

          {/* Port */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: 'var(--text)', marginBottom: '6px' }}>
              Porta RTSP
            </label>
            <input
              type="number"
              value={formData.port}
              onChange={(e) => handleChange('port', parseInt(e.target.value))}
              placeholder="554"
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '14px',
                outline: 'none',
                fontFamily: 'var(--mono)',
              }}
            />
          </div>

          {/* Username */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: 'var(--text)', marginBottom: '6px' }}>
              Usuário
            </label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) => handleChange('username', e.target.value)}
              placeholder="admin"
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '14px',
                outline: 'none',
              }}
            />
          </div>

          {/* Password */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: 'var(--text)', marginBottom: '6px' }}>
              Senha
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => handleChange('password', e.target.value)}
              placeholder="••••••••"
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '14px',
                outline: 'none',
              }}
            />
          </div>

          {/* Channel */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: 'var(--text)', marginBottom: '6px' }}>
              Canal
            </label>
            <input
              type="number"
              value={formData.channel}
              onChange={(e) => handleChange('channel', parseInt(e.target.value))}
              min="1"
              max="16"
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '14px',
                outline: 'none',
              }}
            />
          </div>

          {/* Subtype */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '500', color: 'var(--text)', marginBottom: '6px' }}>
              Tipo de Stream
            </label>
            <select
              value={formData.subtype}
              onChange={(e) => handleChange('subtype', parseInt(e.target.value))}
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '14px',
                outline: 'none',
                background: 'var(--card)',
              }}
            >
              <option value="0">Stream Principal (Main)</option>
              <option value="1">Sub-stream (Low Latency)</option>
            </select>
          </div>
        </div>

        {/* Actions */}
        <div
          style={{
            display: 'flex',
            gap: '12px',
            marginTop: '24px',
            paddingTop: '20px',
            borderTop: '1px solid var(--border)',
          }}
        >
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={testing}
            style={{
              padding: '10px 20px',
              borderRadius: '8px',
              background: testing ? '#6b7280' : '#3b82f6',
              color: '#fff',
              border: 'none',
              fontSize: '14px',
              fontWeight: '500',
              cursor: testing ? 'not-allowed' : 'pointer',
              opacity: testing ? 0.6 : 1,
              transition: 'all 0.15s',
            }}
            onMouseEnter={(e) => !testing && (e.currentTarget.style.background = '#2563eb')}
            onMouseLeave={(e) => !testing && (e.currentTarget.style.background = '#3b82f6')}
          >
            {testing ? 'Testando...' : 'Testar Conexão'}
          </button>

          <div style={{ flex: 1 }} />

          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '10px 20px',
              borderRadius: '8px',
              background: 'var(--bg)',
              color: 'var(--text)',
              border: '1px solid var(--border)',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer',
            }}
          >
            Cancelar
          </button>

          <button
            type="submit"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 24px',
              borderRadius: '8px',
              background: 'var(--accent)',
              color: '#fff',
              border: 'none',
              fontSize: '14px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#1d4ed8'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'var(--accent)'}
          >
            {Icons.check}
            {isEdit ? 'Salvar' : 'Criar Câmera'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
