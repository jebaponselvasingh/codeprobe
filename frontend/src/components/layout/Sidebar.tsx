
import { FileCode2, Users, History, Settings } from 'lucide-react';
import { useUiStore } from '../../stores/uiStore';

const NAV = [
  { page: 'review' as const,   icon: FileCode2, label: 'New Review' },
  { page: 'batch' as const,    icon: Users,     label: 'Batch Review' },
  { page: 'history' as const,  icon: History,   label: 'History' },
  { page: 'profiles' as const, icon: Settings,  label: 'Profiles' },
];

export function Sidebar() {
  const { activePage, navigate, sidebarOpen } = useUiStore();

  return (
    <aside
      className="fixed left-0 top-0 h-full flex flex-col z-40 transition-all duration-200"
      style={{
        width: sidebarOpen ? 'var(--sidebar-width)' : '64px',
        background: 'var(--bg-sidebar)',
        borderRight: '1px solid var(--border)',
      }}
    >
      {/* Logo */}
      <div
        className="flex items-center gap-3 px-4 py-5 border-b"
        style={{ borderColor: 'var(--border)', height: 64 }}
      >
        <span className="text-xl flex-shrink-0">🔍</span>
        {sidebarOpen && (
          <span className="font-semibold text-sm truncate" style={{ color: 'var(--text-primary)' }}>
            CodeReview
          </span>
        )}
      </div>

      {/* Nav items */}
      <nav className="flex-1 py-4">
        {NAV.map(({ page, icon: Icon, label }) => {
          const active = activePage === page;
          return (
            <button
              key={page}
              onClick={() => navigate(page)}
              className="w-full flex items-center gap-3 px-4 py-3 transition-colors text-sm"
              style={{
                background: active ? 'rgba(79,143,247,0.12)' : 'transparent',
                color: active ? 'var(--accent-blue)' : 'var(--text-secondary)',
                borderLeft: active ? '3px solid var(--accent-blue)' : '3px solid transparent',
              }}
              title={!sidebarOpen ? label : undefined}
            >
              <Icon size={18} className="flex-shrink-0" />
              {sidebarOpen && <span>{label}</span>}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
