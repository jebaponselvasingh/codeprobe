import { Accessibility } from 'lucide-react';

interface AccessibilityViolation {
  file: string;
  type: string;
  message: string;
  wcag: string;
}

interface AccessibilityData {
  violations: AccessibilityViolation[];
  violation_counts: Record<string, number>;
  total_violations: number;
  accessibility_score: number;
  wcag_coverage: { A: boolean; AA: boolean };
  llm_findings: any[];
}

interface Props {
  data: AccessibilityData;
}

function scoreBadgeStyle(score: number): { background: string; color: string } {
  if (score >= 7) return { background: 'rgba(34,197,94,0.15)', color: 'var(--accent-green)' };
  if (score >= 5) return { background: 'rgba(234,179,8,0.15)', color: 'var(--accent-amber)' };
  return { background: 'rgba(239,68,68,0.15)', color: 'var(--accent-red)' };
}

export function AccessibilityReport({ data }: Props) {
  const violations = data.violations ?? [];
  const violationCounts = data.violation_counts ?? {};
  const wcag = data.wcag_coverage ?? { A: false, AA: false };
  const total = data.total_violations ?? 0;
  const badgeStyle = scoreBadgeStyle(data.accessibility_score ?? 0);

  return (
    <div className="card flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Accessibility size={18} style={{ color: 'var(--accent-blue)' }} />
        <h3 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
          Accessibility
        </h3>
        <div className="ml-auto flex items-center gap-3">
          {/* WCAG coverage */}
          <div className="flex items-center gap-1.5">
            {(['A', 'AA'] as const).map(level => (
              <span
                key={level}
                className="text-xs px-2 py-0.5 rounded font-medium"
                style={{
                  background: wcag[level] ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.12)',
                  color: wcag[level] ? 'var(--accent-green)' : 'var(--accent-red)',
                  border: `1px solid ${wcag[level] ? 'rgba(34,197,94,0.25)' : 'rgba(239,68,68,0.2)'}`,
                }}
              >
                {wcag[level] ? '✓' : '✗'} WCAG {level}
              </span>
            ))}
          </div>
          {data.accessibility_score !== undefined && (
            <span
              className="text-xs font-bold px-2 py-0.5 rounded-full"
              style={badgeStyle}
            >
              {data.accessibility_score.toFixed(1)} / 10
            </span>
          )}
        </div>
      </div>

      {/* Compliant state */}
      {total === 0 ? (
        <div
          className="rounded-lg p-4 text-center text-sm font-medium"
          style={{
            background: 'rgba(34,197,94,0.1)',
            color: 'var(--accent-green)',
            border: '1px solid rgba(34,197,94,0.25)',
          }}
        >
          WCAG compliant — no violations detected
        </div>
      ) : (
        <>
          {/* Total violations */}
          <div
            className="rounded-lg p-4 text-center"
            style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
          >
            <div className="text-3xl font-bold" style={{ color: 'var(--accent-red)' }}>
              {total}
            </div>
            <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
              Total Violations
            </div>
          </div>

          {/* Violation type breakdown */}
          {Object.keys(violationCounts).length > 0 && (
            <div>
              <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
                VIOLATION BREAKDOWN
              </p>
              <div
                className="rounded-lg overflow-hidden"
                style={{ border: '1px solid var(--border)' }}
              >
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ background: 'var(--bg-secondary)' }}>
                      <th
                        className="text-left px-3 py-2 text-xs font-medium"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        Type
                      </th>
                      <th
                        className="text-right px-3 py-2 text-xs font-medium"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        Count
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(violationCounts).map(([type, count], i) => (
                      <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                        <td className="px-3 py-2 text-xs" style={{ color: 'var(--text-primary)' }}>
                          {type}
                        </td>
                        <td
                          className="px-3 py-2 text-xs text-right font-bold"
                          style={{ color: 'var(--accent-amber)' }}
                        >
                          {count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Top violations list */}
          {violations.length > 0 && (
            <div className="flex flex-col gap-2">
              <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                TOP VIOLATIONS
              </p>
              {violations.slice(0, 10).map((v, i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg text-sm"
                  style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="text-xs px-1.5 py-0.5 rounded font-medium flex-shrink-0"
                      style={{
                        background: 'rgba(234,179,8,0.12)',
                        color: 'var(--accent-amber)',
                        border: '1px solid rgba(234,179,8,0.2)',
                      }}
                    >
                      {v.wcag}
                    </span>
                    <span className="text-xs font-medium truncate" style={{ color: 'var(--text-secondary)' }}>
                      {v.type}
                    </span>
                  </div>
                  <p style={{ color: 'var(--text-primary)' }}>{v.message}</p>
                  <p className="text-xs mt-1 font-mono truncate" style={{ color: 'var(--accent-blue)' }}>
                    {v.file}
                  </p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
