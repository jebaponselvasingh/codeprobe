import { Badge } from '../shared/Badge';
import { useHistoryStore } from '../../stores/historyStore';
import { useUiStore } from '../../stores/uiStore';
import type { ReviewSummary } from '../../stores/historyStore';
import { Trash2 } from 'lucide-react';

interface HistoryCardProps {
  review: ReviewSummary;
}

function scoreColor(score: number): 'green' | 'amber' | 'red' {
  if (score >= 7) return 'green';
  if (score >= 5) return 'amber';
  return 'red';
}

export function HistoryCard({ review }: HistoryCardProps) {
  const { selectReview, deleteReview } = useHistoryStore();
  const { navigate } = useUiStore();

  const handleView = () => {
    selectReview(review.review_id);
    navigate('review');
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Delete this review?')) {
      deleteReview(review.review_id);
    }
  };

  const formattedDate = new Date(review.created_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  const color = scoreColor(review.overall_score);
  const scoreBg = color === 'green'
    ? 'rgba(52,211,153,0.15)'
    : color === 'amber'
    ? 'rgba(251,191,36,0.15)'
    : 'rgba(248,113,113,0.15)';
  const scoreTextColor = color === 'green'
    ? 'var(--accent-green)'
    : color === 'amber'
    ? 'var(--accent-amber)'
    : 'var(--accent-red)';

  return (
    <div
      className="card flex items-center gap-4 cursor-pointer hover:opacity-90 transition-opacity"
      style={{ border: '1px solid var(--border)' }}
      onClick={handleView}
    >
      {/* Score circle */}
      <div
        className="flex-shrink-0 w-14 h-14 rounded-full flex items-center justify-center font-bold text-lg"
        style={{ background: scoreBg, color: scoreTextColor }}
      >
        {review.overall_score.toFixed(1)}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        {review.student_name && (
          <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
            {review.student_name}
          </p>
        )}
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{formattedDate}</p>
        <div className="flex items-center gap-2 mt-1">
          <Badge color="gray">v{review.version}</Badge>
          <Badge color={color}>{review.grade}</Badge>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={handleView}
          className="px-3 py-1.5 rounded-lg text-xs font-medium transition-opacity hover:opacity-80"
          style={{ background: 'rgba(79,143,247,0.12)', color: 'var(--accent-blue)' }}
        >
          View Report
        </button>
        <button
          onClick={handleDelete}
          className="p-1.5 rounded-lg transition-opacity hover:opacity-80"
          style={{ color: 'var(--text-muted)' }}
          title="Delete"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}
