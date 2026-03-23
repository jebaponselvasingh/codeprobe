import { useState } from 'react';
import type { ComparisonData } from '../../stores/batchStore';
import { useBatchStore } from '../../stores/batchStore';

type SortKey = 'name' | 'overall_score' | 'grade' | 'critical_count' | string;
type SortDir = 'asc' | 'desc';

function scoreColor(score: number): { bg: string; color: string } {
  if (score >= 7) return { bg: 'rgba(52,211,153,0.12)', color: 'var(--accent-green)' };
  if (score >= 5) return { bg: 'rgba(251,191,36,0.12)', color: 'var(--accent-amber)' };
  return { bg: 'rgba(248,113,113,0.12)', color: 'var(--accent-red)' };
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div
      className="card flex flex-col gap-1"
      style={{ minWidth: 120 }}
    >
      <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</p>
      <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
        {typeof value === 'number' ? value.toFixed(1) : value}
      </p>
    </div>
  );
}

interface ComparisonDashboardProps {
  data?: ComparisonData;
}

export function ComparisonDashboard({ data: dataProp }: ComparisonDashboardProps) {
  const storeComparison = useBatchStore(s => s.comparison);
  const data = dataProp ?? storeComparison;

  const [sortKey, setSortKey] = useState<SortKey>('overall_score');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64 text-sm" style={{ color: 'var(--text-muted)' }}>
        No comparison data available.
      </div>
    );
  }

  const { students, class_stats, common_issues } = data;

  // Collect all category names
  const categoryNames = students.length > 0
    ? Object.keys(students[0].category_scores)
    : [];

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = [...students].sort((a, b) => {
    let av: number | string;
    let bv: number | string;

    if (sortKey === 'name') {
      av = a.name; bv = b.name;
    } else if (sortKey === 'overall_score') {
      av = a.overall_score; bv = b.overall_score;
    } else if (sortKey === 'grade') {
      av = a.grade; bv = b.grade;
    } else if (sortKey === 'critical_count') {
      av = a.critical_count; bv = b.critical_count;
    } else {
      av = a.category_scores[sortKey]?.score ?? 0;
      bv = b.category_scores[sortKey]?.score ?? 0;
    }

    if (av < bv) return sortDir === 'asc' ? -1 : 1;
    if (av > bv) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  // Class averages per category
  const categoryAvgs: Record<string, number> = {};
  categoryNames.forEach(cat => {
    const vals = students.map(s => s.category_scores[cat]?.score ?? 0);
    categoryAvgs[cat] = vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  });

  const SortHeader = ({ colKey, label }: { colKey: SortKey; label: string }) => (
    <th
      className="px-3 py-2 text-left text-xs font-medium cursor-pointer select-none whitespace-nowrap"
      style={{ color: sortKey === colKey ? 'var(--accent-blue)' : 'var(--text-secondary)' }}
      onClick={() => handleSort(colKey)}
    >
      {label} {sortKey === colKey ? (sortDir === 'asc' ? '↑' : '↓') : ''}
    </th>
  );

  const highFrequencyIssues = common_issues.filter(
    ci => ci.affected_students > students.length * 0.5
  );

  return (
    <div className="max-w-6xl mx-auto py-8 flex flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
          Class Comparison
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          {students.length} student{students.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Stats row */}
      <div className="flex gap-4 flex-wrap">
        <StatCard label="Mean Score" value={class_stats.mean} />
        <StatCard label="Median Score" value={class_stats.median} />
        <StatCard label="Std Deviation" value={class_stats.std_dev} />
      </div>

      {/* Comparison table */}
      <div
        className="card overflow-x-auto"
        style={{ padding: 0 }}
      >
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              <SortHeader colKey="name" label="Name" />
              <SortHeader colKey="overall_score" label="Overall" />
              <SortHeader colKey="grade" label="Grade" />
              {categoryNames.map(cat => (
                <SortHeader key={cat} colKey={cat} label={cat.replace(/_/g, ' ')} />
              ))}
              <SortHeader colKey="critical_count" label="Critical" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((student, i) => {
              const { bg, color } = scoreColor(student.overall_score);
              return (
                <tr
                  key={i}
                  style={{
                    borderBottom: '1px solid var(--border)',
                    background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                  }}
                >
                  <td className="px-3 py-2 font-medium" style={{ color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
                    {student.name}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className="px-2 py-0.5 rounded-full text-xs font-semibold"
                      style={{ background: bg, color }}
                    >
                      {student.overall_score.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="text-xs font-bold" style={{ color }}>
                      {student.grade}
                    </span>
                  </td>
                  {categoryNames.map(cat => {
                    const catScore = student.category_scores[cat]?.score ?? 0;
                    const { color: cc } = scoreColor(catScore);
                    return (
                      <td key={cat} className="px-3 py-2 text-xs" style={{ color: cc }}>
                        {catScore.toFixed(1)}
                      </td>
                    );
                  })}
                  <td className="px-3 py-2">
                    {student.critical_count > 0 ? (
                      <span
                        className="px-2 py-0.5 rounded-full text-xs font-semibold"
                        style={{ background: 'rgba(248,113,113,0.15)', color: 'var(--accent-red)' }}
                      >
                        {student.critical_count}
                      </span>
                    ) : (
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
          {/* Footer: class averages */}
          <tfoot>
            <tr style={{ borderTop: '2px solid var(--border)', background: 'var(--bg-secondary)' }}>
              <td className="px-3 py-2 text-xs font-bold" style={{ color: 'var(--text-secondary)' }}>
                Class Avg
              </td>
              <td className="px-3 py-2">
                <span className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>
                  {class_stats.mean.toFixed(1)}
                </span>
              </td>
              <td className="px-3 py-2" />
              {categoryNames.map(cat => (
                <td key={cat} className="px-3 py-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                  {categoryAvgs[cat].toFixed(1)}
                </td>
              ))}
              <td className="px-3 py-2" />
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Common issues */}
      {highFrequencyIssues.length > 0 && (
        <div className="card">
          <p className="text-xs font-medium mb-3" style={{ color: 'var(--text-secondary)' }}>
            COMMON ISSUES (affecting &gt;50% of students)
          </p>
          <div className="flex flex-col gap-2">
            {highFrequencyIssues.map((ci, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 rounded-lg"
                style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
              >
                <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{ci.issue}</p>
                <span
                  className="text-xs px-2 py-0.5 rounded-full font-medium ml-4 flex-shrink-0"
                  style={{ background: 'rgba(248,113,113,0.12)', color: 'var(--accent-red)' }}
                >
                  {ci.affected_students}/{students.length} students
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
