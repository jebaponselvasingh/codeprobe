import { useState } from 'react';
import { useHistoryStore } from '../../stores/historyStore';
import { HistoryCard } from './HistoryCard';
import { ProgressChart } from './ProgressChart';
import { VersionComparison } from './VersionComparison';
import { Search, TrendingUp } from 'lucide-react';

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  padding: '8px 12px',
  color: 'var(--text-primary)',
  fontSize: 14,
  outline: 'none',
};

export function HistoryPage() {
  const {
    reviews,
    selectedProjectId,
    progressData,
    isLoading,
    error,
    page,
    total,
    limit,
    studentNameFilter,
    fetchHistory,
    fetchProgress,
    setStudentNameFilter,
  } = useHistoryStore();

  const [projectInput, setProjectInput] = useState(selectedProjectId ?? '');

  const handleSearch = async () => {
    if (!projectInput.trim()) return;
    await fetchHistory(projectInput.trim(), 1);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  const handleFetchProgress = async () => {
    if (selectedProjectId) await fetchProgress(selectedProjectId);
  };

  return (
    <div className="max-w-5xl mx-auto py-8 flex flex-col gap-6">
      {/* Header */}
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
        Review History
      </h1>

      {/* Search bar */}
      <div className="card flex flex-col gap-3">
        <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>SEARCH</p>
        <div className="flex gap-3 flex-wrap">
          <input
            type="text"
            placeholder="Project ID (e.g. todo-app)"
            value={projectInput}
            onChange={e => setProjectInput(e.target.value)}
            onKeyDown={handleKeyDown}
            style={{ ...inputStyle, flex: 1, minWidth: 180 }}
          />
          <input
            type="text"
            placeholder="Filter by student name"
            value={studentNameFilter}
            onChange={e => setStudentNameFilter(e.target.value)}
            onKeyDown={handleKeyDown}
            style={{ ...inputStyle, flex: 1, minWidth: 180 }}
          />
          <button
            onClick={handleSearch}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-opacity hover:opacity-80"
            style={{ background: 'var(--accent-blue)', color: '#fff', cursor: 'pointer' }}
          >
            <Search size={14} />
            Search
          </button>
          {selectedProjectId && (
            <button
              onClick={handleFetchProgress}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-opacity hover:opacity-80"
              style={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
              }}
            >
              <TrendingUp size={14} />
              Progress
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div
          className="px-4 py-3 rounded-lg text-sm"
          style={{ background: 'rgba(248,113,113,0.1)', color: 'var(--accent-red)', border: '1px solid rgba(248,113,113,0.2)' }}
        >
          {error}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12 text-sm" style={{ color: 'var(--text-muted)' }}>
          Loading history...
        </div>
      )}

      {/* History list */}
      {!isLoading && reviews.length > 0 && (
        <div className="flex flex-col gap-3">
          {reviews.map(r => (
            <HistoryCard key={r.review_id} review={r} />
          ))}
        </div>
      )}

      {!isLoading && reviews.length === 0 && selectedProjectId && (
        <div className="flex items-center justify-center py-12 text-sm" style={{ color: 'var(--text-muted)' }}>
          No reviews found for &quot;{selectedProjectId}&quot;.
        </div>
      )}

      {!isLoading && !selectedProjectId && reviews.length === 0 && (
        <div className="flex items-center justify-center py-16 text-sm" style={{ color: 'var(--text-muted)' }}>
          Enter a Project ID to search review history.
        </div>
      )}

      {/* Pagination */}
      {total > limit && (
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => selectedProjectId && fetchHistory(selectedProjectId, page - 1)}
            disabled={page === 1}
            className="px-4 py-2 rounded-lg text-sm transition-opacity"
            style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              color: page === 1 ? 'var(--text-muted)' : 'var(--text-secondary)',
              cursor: page === 1 ? 'not-allowed' : 'pointer',
              opacity: page === 1 ? 0.5 : 1,
            }}
          >
            Previous
          </button>
          <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            Page {page} of {Math.ceil(total / limit)}
          </span>
          <button
            onClick={() => selectedProjectId && fetchHistory(selectedProjectId, page + 1)}
            disabled={page * limit >= total}
            className="px-4 py-2 rounded-lg text-sm transition-opacity"
            style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              color: page * limit >= total ? 'var(--text-muted)' : 'var(--text-secondary)',
              cursor: page * limit >= total ? 'not-allowed' : 'pointer',
              opacity: page * limit >= total ? 0.5 : 1,
            }}
          >
            Next
          </button>
        </div>
      )}

      {/* Progress chart */}
      {progressData && <ProgressChart data={progressData} />}

      {/* Version comparison */}
      {progressData && progressData.versions.length >= 2 && (
        <VersionComparison data={progressData} />
      )}
    </div>
  );
}
