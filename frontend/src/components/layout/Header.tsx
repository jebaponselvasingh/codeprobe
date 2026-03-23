
import { Moon, Sun, PanelLeftClose, PanelLeft } from 'lucide-react';
import { useUiStore } from '../../stores/uiStore';
import { useHealthCheck } from '../../hooks/useHealthCheck';

export function Header() {
  const { theme, toggleTheme, toggleSidebar, sidebarOpen } = useUiStore();
  const health = useHealthCheck();

  return (
    <header
      className="flex items-center justify-between px-6 flex-shrink-0"
      style={{
        height: 64,
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:opacity-80 transition-opacity"
          style={{ color: 'var(--text-secondary)' }}
        >
          {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeft size={18} />}
        </button>
        <span className="font-semibold text-base" style={{ color: 'var(--text-primary)' }}>
          CodeReview Agent
        </span>
      </div>

      <div className="flex items-center gap-4">
        {/* Ollama status */}
        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
          <div
            className="w-2 h-2 rounded-full"
            style={{ background: health?.ollama ? 'var(--accent-green)' : 'var(--accent-red)' }}
          />
          <span>{health?.ollama ? health.active_model : 'Ollama offline'}</span>
        </div>

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg hover:opacity-80 transition-opacity"
          style={{ color: 'var(--text-secondary)' }}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </header>
  );
}
