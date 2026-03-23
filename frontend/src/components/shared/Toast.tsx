
import { useUiStore } from '../../stores/uiStore';
import { X } from 'lucide-react';

export function Toast() {
  const { toasts, dismissToast } = useUiStore();

  if (!toasts.length) return null;

  const colorMap = {
    success: 'var(--accent-green)',
    error: 'var(--accent-red)',
    info: 'var(--accent-blue)',
  };

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map(t => (
        <div
          key={t.id}
          className="flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-sm"
          style={{
            background: 'var(--bg-card)',
            border: `1px solid ${colorMap[t.type]}`,
            color: 'var(--text-primary)',
            minWidth: 260,
          }}
        >
          <div
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: colorMap[t.type] }}
          />
          <span className="flex-1">{t.message}</span>
          <button
            onClick={() => dismissToast(t.id)}
            className="opacity-60 hover:opacity-100"
            style={{ color: 'var(--text-secondary)' }}
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
