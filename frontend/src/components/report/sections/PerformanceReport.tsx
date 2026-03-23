import { Zap } from 'lucide-react';

interface PerformanceIssue {
  file: string;
  type: string;
  message: string;
}

interface Finding {
  type: string;
  area: string;
  detail: string;
  file?: string;
  fix_hint?: string;
}

interface PerformanceProfile {
  frontend_issues: PerformanceIssue[];
  backend_issues: PerformanceIssue[];
  performance_score: number;
  findings: Finding[];
}

interface Props {
  data: PerformanceProfile;
}

function scoreBadgeStyle(score: number): { background: string; color: string } {
  if (score >= 7) return { background: 'rgba(34,197,94,0.15)', color: 'var(--accent-green)' };
  if (score >= 5) return { background: 'rgba(234,179,8,0.15)', color: 'var(--accent-amber)' };
  return { background: 'rgba(239,68,68,0.15)', color: 'var(--accent-red)' };
}

export function PerformanceReport({ data }: Props) {
  const frontendIssues = data.frontend_issues ?? [];
  const backendIssues = data.backend_issues ?? [];
  const findings = data.findings ?? [];
  const allIssues = [
    ...frontendIssues.map(i => ({ ...i, origin: 'Frontend' as const })),
    ...backendIssues.map(i => ({ ...i, origin: 'Backend' as const })),
  ];
  const noIssues = frontendIssues.length === 0 && backendIssues.length === 0;
  const badgeStyle = scoreBadgeStyle(data.performance_score ?? 0);

  return (
    <div className="card flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Zap size={18} style={{ color: 'var(--accent-blue)' }} />
        <h3 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
          Performance Profile
        </h3>
        {data.performance_score !== undefined && (
          <span
            className="ml-auto text-xs font-bold px-2 py-0.5 rounded-full"
            style={badgeStyle}
          >
            {data.performance_score.toFixed(1)} / 10
          </span>
        )}
      </div>

      {/* Count cards */}
      <div className="grid grid-cols-2 gap-3">
        <div
          className="rounded-lg p-4 text-center"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
        >
          <div
            className="text-2xl font-bold"
            style={{ color: frontendIssues.length > 0 ? 'var(--accent-amber)' : 'var(--accent-green)' }}
          >
            {frontendIssues.length}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            Frontend Issues
          </div>
        </div>
        <div
          className="rounded-lg p-4 text-center"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
        >
          <div
            className="text-2xl font-bold"
            style={{ color: backendIssues.length > 0 ? 'var(--accent-amber)' : 'var(--accent-green)' }}
          >
            {backendIssues.length}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            Backend Issues
          </div>
        </div>
      </div>

      {/* No issues state */}
      {noIssues ? (
        <div
          className="rounded-lg p-4 text-center text-sm font-medium"
          style={{ background: 'rgba(34,197,94,0.1)', color: 'var(--accent-green)', border: '1px solid rgba(34,197,94,0.25)' }}
        >
          No performance issues detected
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
            TOP ISSUES
          </p>
          {allIssues.slice(0, 10).map((issue, i) => (
            <div
              key={i}
              className="p-3 rounded-lg text-sm"
              style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
            >
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="text-xs px-1.5 py-0.5 rounded font-medium flex-shrink-0"
                  style={{
                    background: issue.origin === 'Frontend' ? 'rgba(99,102,241,0.15)' : 'rgba(20,184,166,0.15)',
                    color: issue.origin === 'Frontend' ? 'var(--accent-purple)' : 'var(--accent-teal, var(--accent-green))',
                  }}
                >
                  {issue.origin}
                </span>
                <span className="text-xs font-medium truncate" style={{ color: 'var(--text-secondary)' }}>
                  {issue.type}
                </span>
              </div>
              <p style={{ color: 'var(--text-primary)' }}>{issue.message}</p>
              <p className="text-xs mt-1 font-mono truncate" style={{ color: 'var(--accent-blue)' }}>
                {issue.file}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* LLM findings */}
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
