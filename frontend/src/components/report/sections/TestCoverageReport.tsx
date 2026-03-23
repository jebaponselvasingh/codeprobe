import { FlaskConical } from 'lucide-react';

interface Finding {
  type: string;
  area: string;
  detail: string;
  file?: string;
  fix_hint?: string;
}

interface TestCoverage {
  test_file_ratio: number;
  test_count: number;
  source_count: number;
  critical_gaps: string[];
  avg_assertions_per_test: number;
  missing_tests: string[];
  testing_score: number;
  findings: Finding[];
}

interface Props {
  data: TestCoverage;
}

function scoreBadgeStyle(score: number): { background: string; color: string } {
  if (score >= 7) return { background: 'rgba(34,197,94,0.15)', color: 'var(--accent-green)' };
  if (score >= 5) return { background: 'rgba(234,179,8,0.15)', color: 'var(--accent-amber)' };
  return { background: 'rgba(239,68,68,0.15)', color: 'var(--accent-red)' };
}

export function TestCoverageReport({ data }: Props) {
  const criticalGaps = data.critical_gaps ?? [];
  const missingTests = data.missing_tests ?? [];
  const findings = data.findings ?? [];
  const ratio = data.test_file_ratio ?? 0;
  const ratioPercent = Math.round(ratio * 100);
  const badgeStyle = scoreBadgeStyle(data.testing_score ?? 0);

  return (
    <div className="card flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <FlaskConical size={18} style={{ color: 'var(--accent-green)' }} />
        <h3 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
          Test Coverage
        </h3>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {ratioPercent}% test ratio
          </span>
          {data.testing_score !== undefined && (
            <span
              className="text-xs font-bold px-2 py-0.5 rounded-full"
              style={badgeStyle}
            >
              {data.testing_score.toFixed(1)} / 10
            </span>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
        >
          <div className="text-2xl font-bold" style={{ color: 'var(--accent-blue)' }}>
            {data.test_count ?? 0}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            Test Files
          </div>
        </div>
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
        >
          <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {data.source_count ?? 0}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            Source Files
          </div>
        </div>
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
        >
          <div className="text-2xl font-bold" style={{ color: 'var(--accent-purple)' }}>
            {(data.avg_assertions_per_test ?? 0).toFixed(1)}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            Avg Assertions
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-xs mb-1">
          <span style={{ color: 'var(--text-secondary)' }}>Test file ratio</span>
          <span style={{ color: 'var(--accent-green)' }}>{ratioPercent}%</span>
        </div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.min(100, ratioPercent)}%`,
              background: ratioPercent >= 70 ? 'var(--accent-green)' : ratioPercent >= 40 ? 'var(--accent-amber)' : 'var(--accent-red)',
            }}
          />
        </div>
      </div>

      {/* Critical gaps */}
      {criticalGaps.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            CRITICAL GAPS
          </p>
          <div className="flex flex-wrap gap-2">
            {criticalGaps.map((gap, i) => (
              <span
                key={i}
                className="text-xs px-2.5 py-1 rounded-full font-medium"
                style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--accent-red)', border: '1px solid rgba(239,68,68,0.25)' }}
              >
                {gap}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Missing tests */}
      {missingTests.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            MISSING TESTS
          </p>
          <div className="grid grid-cols-2 gap-1.5">
            {missingTests.slice(0, 8).map((t, i) => (
              <span
                key={i}
                className="text-xs px-2 py-1 rounded font-mono truncate"
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-secondary)',
                }}
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Findings */}
      {findings.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
            FINDINGS
          </p>
          {findings.slice(0, 6).map((f, i) => (
            <div
              key={i}
              className="p-3 rounded-lg text-sm"
              style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
            >
              <p className="font-medium mb-0.5" style={{ color: 'var(--text-primary)' }}>
                {f.area}
              </p>
              <p style={{ color: 'var(--text-secondary)' }}>{f.detail}</p>
              {f.fix_hint && (
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  Fix: {f.fix_hint}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
