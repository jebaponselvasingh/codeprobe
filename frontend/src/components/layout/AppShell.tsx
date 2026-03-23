
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useUiStore } from '../../stores/uiStore';
import { useReviewStore } from '../../stores/reviewStore';
import { useBatchStore } from '../../stores/batchStore';
import { UploadPage } from '../upload/UploadPage';
import { ProgressPage } from '../progress/ProgressPage';
import { ReportPage } from '../report/ReportPage';
import { BatchUploadPage } from '../batch/BatchUploadPage';
import { BatchProgressPage } from '../batch/BatchProgressPage';
import { ComparisonDashboard } from '../batch/ComparisonDashboard';
import { HistoryPage } from '../history/HistoryPage';
import { ProfilesPage } from '../profiles/ProfilesPage';

export function AppShell() {
  const { activePage, sidebarOpen } = useUiStore();
  const { phase } = useReviewStore();
  const { phase: batchPhase, comparison } = useBatchStore();

  const renderMain = () => {
    if (activePage === 'review') {
      if (phase === 'reviewing' || phase === 'uploading') return <ProgressPage />;
      if (phase === 'complete') return <ReportPage />;
      return <UploadPage />;
    }
    if (activePage === 'batch') {
      if (batchPhase === 'reviewing' || batchPhase === 'uploading') return <BatchProgressPage />;
      if (batchPhase === 'complete' && comparison) return <ComparisonDashboard />;
      return <BatchUploadPage />;
    }
    if (activePage === 'history') return <HistoryPage />;
    if (activePage === 'profiles') return <ProfilesPage />;
    return (
      <div className="flex items-center justify-center h-full text-sm" style={{ color: 'var(--text-muted)' }}>
        Coming in a future phase
      </div>
    );
  };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg-primary)' }}>
      <Sidebar />
      <div
        className="flex flex-col flex-1 min-w-0 transition-all duration-200"
        style={{ marginLeft: sidebarOpen ? 'var(--sidebar-width)' : '64px' }}
      >
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          {renderMain()}
        </main>
      </div>
    </div>
  );
}
