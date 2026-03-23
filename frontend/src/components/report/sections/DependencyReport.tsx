import { Package } from 'lucide-react';

interface DepFinding {
  type: string;
  area: string;
  detail: string;
  file?: string;
  fix_hint?: string;
}

interface DependencyAudit {
  total_deps: number;
  deprecated: Array<{ name: string; reason: string }>;
  unpinned: string[];
  pre_release: string[];
  dependency_score: number;
  findings: DepFinding[];
  llm_concerns: string;
}

interface Props {
  data: DependencyAudit;
}

function scoreBadgeStyle(score: number): { background: string; color: string } {
  if (score >= 7) return { background: 'rgba(34,197,94,0.15)', color: 'var(--accent-green)' };
  if (score >= 5) return { background: 'rgba(234,179,8,0.15)', color: 'var(--accent-amber)' };
  return { background: 'rgba(239,68,68,0.15)', color: 'var(--accent-red)' };
}

export function DependencyReport({ data }: Props) {
  const deprecated = data.deprecated ?? [];
  const unpinned = data.unpinned ?? [];
  const preRelease = data.pre_release ?? [];
  const findings = data.findings ?? [];
  const badgeStyle = scoreBadgeStyle(data.dependency_score ?? 0);

  return (
    <div className="card flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Package size={18} style={{ color: 'var(--accent-purple)' }} />
        <h3 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
          Dependency Audit
        </h3>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {data.total_deps ?? 0} total deps
          </span>
          {data.dependency_score !== undefined && (
            <span
              className="text-xs font-bold px-2 py-0.5 rounded-full"
              style={badgeStyle}
            >
              {data.dependency_score.toFixed(1)} / 10
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
          <div
            className="text-2xl font-bold"
            style={{ color: deprecated.length > 0 ? 'var(--accent-red)' : 'var(--text-muted)' }}
          >
            {deprecated.length}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            Deprecated
          </div>
        </div>
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
        >
          <div
            className="text-2xl font-bold"
            style={{ color: unpinned.length > 0 ? 'var(--accent-amber)' : 'var(--text-muted)' }}
          >
            {unpinned.length}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            Unpinned
          </div>
        </div>
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
        >
          <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {preRelease.length}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            Pre-release
          </div>
        </div>
      </div>

      {/* Deprecated packages table */}
      {deprecated.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            DEPRECATED PACKAGES
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
                    Package
                  </th>
                  <th
                    className="text-left px-3 py-2 text-xs font-medium"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    Reason
                  </th>
                </tr>
              </thead>
              <tbody>
                {deprecated.map((dep, i) => (
                  <tr
                    key={i}
                    style={{ borderTop: '1px solid var(--border)' }}
                  >
                    <td className="px-3 py-2 font-mono text-xs" style={{ color: 'var(--accent-red)' }}>
                      {dep.name}
                    </td>
                    <td className="px-3 py-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                      {dep.reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Unpinned list */}
      {unpinned.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            UNPINNED DEPENDENCIES
          </p>
          <div className="flex flex-wrap gap-2">
            {unpinned.map((pkg, i) => (
              <span
                key={i}
                className="text-xs px-2.5 py-1 rounded-full font-mono"
                style={{
                  background: 'rgba(234,179,8,0.12)',
                  color: 'var(--accent-amber)',
                  border: '1px solid rgba(234,179,8,0.25)',
                }}
              >
                {pkg}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* LLM concerns */}
      {data.llm_concerns && data.llm_concerns.trim() !== '' && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            AI ASSESSMENT
          </p>
          <blockquote
            className="text-sm px-4 py-3 rounded-lg"
            style={{
              background: 'var(--bg-secondary)',
              borderLeft: '3px solid var(--accent-purple)',
              color: 'var(--text-secondary)',
            }}
          >
            {data.llm_concerns}
          </blockquote>
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
