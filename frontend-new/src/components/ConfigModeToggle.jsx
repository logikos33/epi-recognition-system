import { useConfigMode } from '../hooks/useConfigMode'

export function ConfigModeToggle({ onModeChange }) {
  const { isActive, secondsRemaining, token, enter, exit } = useConfigMode()

  const formatTime = (s) => `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`

  const handleEnter = async () => {
    try {
      const t = await enter()
      if (onModeChange) onModeChange(true, t)
    } catch (err) {
      alert(`Erro ao ativar modo configuração: ${err.message}`)
    }
  }

  const handleExit = async () => {
    await exit()
    if (onModeChange) onModeChange(false, null)
  }

  return (
    <>
      {isActive && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 9000,
          background: '#d97706', color: 'white', padding: '10px 20px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          fontSize: 14, fontWeight: 500 }}>
          <span>⚙️ Modo de Configuração Ativo — {formatTime(secondsRemaining)} restantes</span>
          <button onClick={handleExit}
            style={{ background: 'rgba(255,255,255,0.2)', border: '1px solid white',
              color: 'white', padding: '4px 12px', borderRadius: 4,
              cursor: 'pointer', fontSize: 13 }}>
            ✕ Sair do Modo Configuração
          </button>
        </div>
      )}
      {!isActive && (
        <button onClick={handleEnter}
          style={{ padding: '6px 14px', background: 'transparent',
            border: '1px solid #6b7280', color: '#9ca3af',
            borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
          ⚙️ Modo Configuração
        </button>
      )}
    </>
  )
}
