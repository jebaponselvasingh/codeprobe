import { useBatchStore } from '../../stores/batchStore';
import { BatchStudentRow } from './BatchStudentRow';

export function BatchProgressPage() {
  const { students, phase, fetchComparison } = useBatchStore();
  const completeCount = students.filter(s => s.status === 'complete').length;

  return (
    <div className="max-w-4xl mx-auto py-8 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {phase === 'uploading' ? 'Uploading...' : 'Batch Review in Progress'}
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            {completeCount}/{students.length} complete
          </p>
        </div>

        {/* Overall progress bar */}
        <div
          className="flex flex-col items-end gap-1"
          style={{ minWidth: 120 }}
        >
          <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
            {students.length > 0 ? Math.round((completeCount / students.length) * 100) : 0}%
          </span>
          <div
            className="rounded-full overflow-hidden"
            style={{ width: 120, height: 6, background: 'var(--bg-secondary)' }}
          >
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                background: 'var(--accent-blue)',
                width: students.length > 0 ? `${(completeCount / students.length) * 100}%` : '0%',
              }}
            />
          </div>
        </div>
      </div>

      {/* Student rows */}
      {students.map((s, i) => (
        <BatchStudentRow key={i} student={s} index={i} />
      ))}

      {/* View comparison button */}
      {phase === 'complete' && (
        <div className="flex justify-center mt-4">
          <button
            onClick={fetchComparison}
            className="flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm transition-all"
            style={{
              background: 'var(--accent-blue)',
              color: '#fff',
              cursor: 'pointer',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '0.85'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '1'; }}
          >
            View Comparison Report →
          </button>
        </div>
      )}
    </div>
  );
}
