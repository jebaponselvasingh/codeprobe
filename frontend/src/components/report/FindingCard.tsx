import { useState } from 'react';
import type { Finding } from '../../types/review';
import { Badge } from '../shared/Badge';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useReviewStore } from '../../stores/reviewStore';
import { FindingDiffView } from './FindingDiffView';

interface Props {
  finding: Finding;
}

const typeConfig = {
  negative:   { icon: '🔴', color: 'red' as const },
  suggestion: { icon: '💡', color: 'amber' as const },
  positive:   { icon: '✅', color: 'green' as const },
};

export function FindingCard({ finding }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const { icon, color } = typeConfig[finding.type];
  const { openCodeViewer } = useReviewStore();
  const sessionId = useReviewStore(s => s.sessionId);

  const handleViewCode = () => {
    if (!finding.file) return;
    openCodeViewer(finding.file, [
      {
        line: finding.line ?? 1,
        severity: finding.type,
        message: finding.detail,
      },
    ]);
  };

  return (
    <div
      className="rounded-lg p-3 text-sm"
      style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
    >
      <div className="flex items-start gap-3">
        <span className="text-base flex-shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <Badge color={color}>{finding.area}</Badge>
            {finding.file && (
              <button
                onClick={handleViewCode}
                className="text-xs font-mono hover:underline"
                style={{ color: 'var(--accent-blue)', background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
              >
                {finding.file}{finding.line ? `:${finding.line}` : ''}
              </button>
            )}
          </div>
          <p style={{ color: 'var(--text-primary)' }}>{finding.detail}</p>

          <div className="flex items-center gap-3 mt-2">
            {finding.fix_hint && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-xs"
                style={{ color: 'var(--accent-blue)' }}
              >
                {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                {expanded ? 'Hide fix' : 'Show fix'}
              </button>
            )}
            {finding.file && (
              <button
                onClick={handleViewCode}
                className="text-xs"
                style={{ color: 'var(--accent-blue)', background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
              >
                View Code →
              </button>
            )}
            {finding.file && sessionId && (
              <button
                onClick={() => setShowDiff(true)}
                className="text-xs"
                style={{ color: 'var(--accent-purple, #a78bfa)', background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
              >
                Show Fix ▾
              </button>
            )}
          </div>

          {expanded && finding.fix_hint && (
            <div
              className="mt-2 p-2 rounded text-xs font-mono"
              style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', borderLeft: '3px solid var(--accent-blue)' }}
            >
              {finding.fix_hint}
            </div>
          )}
        </div>
      </div>

      {showDiff && sessionId && finding.file && (
        <FindingDiffView
          sessionId={sessionId}
          findingId={finding.id}
          file={finding.file}
          line={finding.line}
          codeSnippet={finding.fix_hint ?? ''}
          description={finding.detail}
          onClose={() => setShowDiff(false)}
        />
      )}
    </div>
  );
}
