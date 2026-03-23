
import { AgentTimeline } from './AgentTimeline';
import { LiveLog } from './LiveLog';
import { useReviewStore } from '../../stores/reviewStore';
import { XCircle } from 'lucide-react';

export function ProgressPage() {
  const { cancelReview, phase } = useReviewStore();

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
        {phase === 'uploading' ? 'Uploading...' : 'Analyzing Your Code'}
      </h1>

      <div className="card">
        <AgentTimeline />
      </div>

      <div className="card">
        <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>LIVE LOG</p>
        <LiveLog />
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Estimated time: 3–8 minutes
        </p>
        <button
          onClick={cancelReview}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all hover:opacity-80"
          style={{
            background: 'rgba(248,113,113,0.1)',
            border: '1px solid var(--accent-red)',
            color: 'var(--accent-red)',
          }}
        >
          <XCircle size={16} />
          Cancel Review
        </button>
      </div>
    </div>
  );
}
