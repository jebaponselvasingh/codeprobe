import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Page = 'review' | 'batch' | 'history' | 'profiles';

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

interface UiStore {
  theme: 'dark' | 'light';
  sidebarOpen: boolean;
  activePage: Page;
  activeReportTab: string;
  toasts: Toast[];
  toggleTheme: () => void;
  toggleSidebar: () => void;
  navigate: (page: Page) => void;
  setActiveReportTab: (tab: string) => void;
  showToast: (message: string, type?: Toast['type']) => void;
  dismissToast: (id: string) => void;
}

export const useUiStore = create<UiStore>()(
  persist(
    (set, get) => ({
      theme: 'dark',
      sidebarOpen: true,
      activePage: 'review',
      activeReportTab: 'overview',
      toasts: [],
      toggleTheme: () => {
        const next = get().theme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        set({ theme: next });
      },
      toggleSidebar: () => set(s => ({ sidebarOpen: !s.sidebarOpen })),
      navigate: (page) => set({ activePage: page }),
      setActiveReportTab: (tab) => set({ activeReportTab: tab }),
      showToast: (message, type = 'info') => {
        const id = Math.random().toString(36).slice(2);
        set(s => ({ toasts: [...s.toasts, { id, message, type }] }));
        setTimeout(() => get().dismissToast(id), 4000);
      },
      dismissToast: (id) => set(s => ({ toasts: s.toasts.filter(t => t.id !== id) })),
    }),
    { name: 'ui-prefs', partialize: (s) => ({ theme: s.theme }) }
  )
);
