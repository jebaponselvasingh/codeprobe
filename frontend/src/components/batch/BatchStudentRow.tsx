import type { StudentEntry } from '../../stores/batchStore';

interface BatchStudentRowProps {
  student: StudentEntry;
  index: number;
}

function StatusIcon({ status }: { status: StudentEntry['status'] }) {
  if (status === 'pending') return <span title="Pending">⏳</span>;
  if (status === 'complete') return <span title="Complete" style={{ color: 'var(--accent-green)' }}>✓</span>;
  if (status === 'error') return <span title="Error" style={{ color: 'var(--accent-red)' }}>✗</span>;
  // reviewing — pulsing spinner
  return (
    <span
      title="Reviewing"
      style={{
        display: 'inline-block',
        animation: 'spin 1s linear infinite',
        color: 'var(--accent-blue)',
      }}
    >
      🔄
    </span>
  );
}

function GradeBadge({ grade, score }: { grade: string; score: number }) {
  const color =
    score >= 7 ? 'var(--accent-green)' :
    score >= 5 ? 'var(--accent-amber)' :
    'var(--accent-red)';
  const bg =
    score >= 7 ? 'rgba(52,211,153,0.15)' :
    score >= 5 ? 'rgba(251,191,36,0.15)' :
    'rgba(248,113,113,0.15)';

  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold"
      style={{ background: bg, color }}
    >
      {grade} · {score.toFixed(1)}
    </span>
  );
}

export function BatchStudentRow({ student, index }: BatchStudentRowProps) {
  const isReviewing = student.status === 'reviewing';
  const isComplete = student.status === 'complete';

  return (
    <div
      className="card flex flex-col gap-2"
      style={{
        borderLeft: `3px solid ${
          isComplete ? 'var(--accent-green)' :
          student.status === 'error' ? 'var(--accent-red)' :
          isReviewing ? 'var(--accent-blue)' :
          'var(--border)'
        }`,
      }}
    >
      <div className="flex items-center gap-3">
        {/* Index */}
        <span
          className="w-6 h-6 flex-shrink-0 flex items-center justify-center rounded-full text-xs font-bold"
          style={{ background: 'var(--bg-secondary)', color: 'var(--text-muted)' }}
        >
          {index + 1}
        </span>

        {/* Status icon */}
        <span className="text-base flex-shrink-0">
          <StatusIcon status={student.status} />
        </span>

        {/* Name + file */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
            {student.name}
          </p>
          <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
            {student.file.name}
          </p>
        </div>

        {/* Current agent (when reviewing) */}
        {isReviewing && student.currentAgent && (
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{
              background: 'rgba(79,143,247,0.12)',
              color: 'var(--accent-blue)',
              flexShrink: 0,
            }}
          >
            {student.currentAgent}
          </span>
        )}

        {/* Score + grade (when complete) */}
        {isComplete && student.score !== null && student.grade !== null && (
          <GradeBadge grade={student.grade} score={student.score} />
        )}
      </div>

      {/* Progress bar */}
      <div
        className="w-full rounded-full overflow-hidden"
        style={{ height: 4, background: 'var(--bg-secondary)' }}
      >
        {isReviewing && (
          <div
            className="h-full rounded-full"
            style={{
              background: 'var(--accent-blue)',
              width: '40%',
              animation: 'indeterminate 1.5s ease-in-out infinite',
            }}
          />
        )}
        {isComplete && (
          <div
            className="h-full rounded-full"
            style={{ background: 'var(--accent-green)', width: '100%' }}
          />
        )}
        {student.status === 'error' && (
          <div
            className="h-full rounded-full"
            style={{ background: 'var(--accent-red)', width: '100%' }}
          />
        )}
      </div>

      <style>{`
        @keyframes indeterminate {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(350%); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
