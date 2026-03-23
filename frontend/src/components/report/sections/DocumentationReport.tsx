import { BookOpen } from 'lucide-react';

interface DocFinding {
  type: string;
  area: string;
  detail: string;
  file?: string;
  fix_hint?: string;
}

interface DocumentationReview {
  readme_found: boolean;
  readme_score: number;
  python_doc_ratio: number;
  js_doc_ratio: number;
  comment_density: number;
  documentation_score: number;
  findings: DocFinding[];
  llm_assessment: string;
}

interface Props {
  data: DocumentationReview;
}

function scoreBadgeStyle(score: number): { background: string; color: string } {
  if (score >= 7) return { background: 'rgba(34,197,94,0.15)', color: 'var(--accent-green)' };
  if (score >= 5) return { background: 'rgba(234,179,8,0.15)', color: 'var(--accent-amber)' };
  return { background: 'rgba(239,68,68,0.15)', color: 'var(--accent-red)' };
}

function ratioBarColor(pct: number): string {
  if (pct >= 70) return 'var(--accent-green)';
  if (pct >= 40) return 'var(--accent-amber)';
  return 'var(--accent-red)';
}

interface MetricCardProps {
  label: string;
  value: string;
  pct?: number;
}

function MetricCard({ label, value, pct }: MetricCardProps) {
  return (
    <div
      className="rounded-lg p-3 flex flex-col gap-1"
      style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
    >
      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
        {label}
      </div>
      <div className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
        {value}
      </div>
      {pct !== undefined && (
        <div className="h-1.5 rounded-full overflow-hidden mt-1" style={{ background: 'var(--bg-card)' }}>
          <div
            className="h-full rounded-full"
            style={{ width: `${Math.min(100, pct)}%`, background: ratioBarColor(pct) }}
          />
        </div>
      )}
    </div>
  );
}

export function DocumentationReport({ data }: Props) {
  const findings = data.findings ?? [];
  const badgeStyle = scoreBadgeStyle(data.documentation_score ?? 0);

  const pythonPct = Math.round((data.python_doc_ratio ?? 0) * 100);
  const jsPct = Math.round((data.js_doc_ratio ?? 0) * 100);
  const commentPct = Math.round((data.comment_density ?? 0) * 100);

  return (
    <div className="card flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <BookOpen size={18} style={{ color: 'var(--accent-amber)' }} />
        <h3 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
          Documentation
        </h3>
        <div className="ml-auto flex items-center gap-2">
          {/* README status */}
          <span
            className="text-xs px-2 py-0.5 rounded font-medium"
            style={{
              background: data.readme_found ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.12)',
              color: data.readme_found ? 'var(--accent-green)' : 'var(--accent-red)',
              border: `1px solid ${data.readme_found ? 'rgba(34,197,94,0.25)' : 'rgba(239,68,68,0.2)'}`,
            }}
          >
            {data.readme_found ? '✓ README' : '✗ No README'}
          </span>
          {data.documentation_score !== undefined && (
            <span
              className="text-xs font-bold px-2 py-0.5 rounded-full"
              style={badgeStyle}
            >
              {data.documentation_score.toFixed(1)} / 10
            </span>
          )}
        </div>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          label="README Score"
          value={`${(data.readme_score ?? 0).toFixed(1)} / 10`}
        />
        <MetricCard
          label="Python Docstrings"
          value={`${pythonPct}%`}
          pct={pythonPct}
        />
        <MetricCard
          label="JSDoc Coverage"
          value={`${jsPct}%`}
          pct={jsPct}
        />
        <MetricCard
          label="Comment Density"
          value={`${commentPct}%`}
          pct={commentPct}
        />
      </div>

      {/* LLM Assessment */}
      {data.llm_assessment && data.llm_assessment.trim() !== '' && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            AI ASSESSMENT
          </p>
          <p
            className="text-sm leading-relaxed px-4 py-3 rounded-lg"
            style={{
              background: 'var(--bg-secondary)',
              borderLeft: '3px solid var(--accent-amber)',
              color: 'var(--text-secondary)',
            }}
          >
            {data.llm_assessment}
          </p>
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
