import { useEffect } from 'react';
import { AppShell } from './components/layout/AppShell';
import { Toast } from './components/shared/Toast';
import { useUiStore } from './stores/uiStore';

export default function App() {
  const { theme } = useUiStore();

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  return (
    <>
      <AppShell />
      <Toast />
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </>
  );
}
