import { useEffect } from 'react';
import { useToast } from '../hooks/useToast';

const Toast = ({ toast }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      // Toast will be removed by useToast hook
    }, 4000);
    return () => clearTimeout(timer);
  }, [toast.id]);

  const colors = {
    success: '#22c55e',
    error: '#ef4444',
    warning: '#f59e0b',
    info: '#3b82f6',
  };

  const icons = {
    success: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"/></svg>,
    error: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>,
    warning: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01"/></svg>,
    info: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>,
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '12px 16px',
        borderRadius: '10px',
        background: 'var(--card)',
        border: '1px solid var(--border)',
        boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
        minWidth: '280px',
        maxWidth: '400px',
        animation: 'slideInRight 0.3s ease both',
      }}
    >
      <div
        style={{
          width: '24px',
          height: '24px',
          borderRadius: '6px',
          background: `${colors[toast.type]}18`,
          color: colors[toast.type],
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        {icons[toast.type]}
      </div>
      <div
        style={{
          flex: 1,
          fontSize: '13px',
          fontWeight: '500',
          color: 'var(--text)',
        }}
      >
        {toast.message}
      </div>
    </div>
  );
};

export default function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <>
      <style>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        @keyframes slideOutRight {
          from {
            transform: translateX(0);
            opacity: 1;
          }
          to {
            transform: translateX(100%);
            opacity: 0;
          }
        }
      `}</style>
      <div
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          pointerEvents: 'none',
        }}
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            style={{ pointerEvents: 'auto' }}
            onClick={() => removeToast(toast.id)}
          >
            <Toast toast={toast} />
          </div>
        ))}
      </div>
    </>
  );
}
