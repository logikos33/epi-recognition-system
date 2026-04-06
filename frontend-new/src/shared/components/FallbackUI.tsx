interface Props {
  title?: string
  message?: string
  onRetry?: () => void
}

export function FallbackUI({
  title = 'Service Unavailable',
  message = 'This feature is temporarily unavailable.',
  onRetry,
}: Props) {
  return (
    <div
      style={{
        padding: '2rem',
        textAlign: 'center',
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        margin: '1rem',
      }}
    >
      <h3 style={{ color: '#6b7280' }}>⚠️ {title}</h3>
      <p style={{ color: '#9ca3af' }}>{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            padding: '0.5rem 1rem',
            background: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
          }}
        >
          Retry
        </button>
      )}
    </div>
  )
}
