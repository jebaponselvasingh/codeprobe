import { Badge } from '../../shared/Badge';
import { FlaskConical } from 'lucide-react';

interface OriginalityFinding {
  severity?: string;
  area?: string;
  detail?: string;
  message?: string;
  [key: string]: unknown;
}

interface OriginalityData {
  originality_estimate: number;
  originality_score: number;
  boilerplate_percentage: number;
  custom_ratio: number;
  tutorial_signals: string[];
  original_elements: string[];
  assessment: string;
  findings: OriginalityFinding[];
}

interface Props {
  data: OriginalityData;
}

function scoreColor(score: number): string {
  if (score >= 7) return 'var(--accent-green)';
  if (score >= 4) return 'var(--accent-amber)';
  return 'var(--accent-red)';
}

function scoreBadgeColor(score: number): 'green' | 'amber' | 'red' {
  if (score >= 7) return 'green';
  if (score >= 4) return 'amber';
  return 'red';
}

export function OriginalityReport({ data }: Props) {
  const {
    originality_estimate,
    originality_score,
    boilerplate_percentage,
    custom_ratio,
    tutorial_signals,
    original_elements,
    assessment,
    findings,
  } = data;

  const customPercent = Math.round((custom_ratio ?? 0) * 100);

  return (
    <div className="card flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <FlaskConical size={18} style={{ color: 'var(--accent-blue)' }} />
        <h3 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
          Originality Analysis
        </h3>
        <Badge color={scoreBadgeColor(originality_score)} className="ml-auto">
          {originality_score?.toFixed(1)} / 10
        </Badge>
      </div>

      {/* Big stat */}
      <div
        className="rounded-xl p-5 text-center"
        style={{ background: 'var(--bg-secondary)', border: '1px solid var(--color-border)' }}
      >
        <div
          className="text-5xl font-bold"
          style={{ color: scoreColor(originality_score) }}
        >
          {Math.round(originality_estimate)}%
        </div>
        <div className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          Original
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-3">
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--color-border)' }}
        >
          <div className="text-2xl font-bold" style={{ color: 'var(--accent-green)' }}>
            {customPercent}%
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Custom Code</div>
        </div>
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--color-border)' }}
        >
          <div className="text-2xl font-bold" style={{ color: 'var(--accent-amber)' }}>
            {Math.round(boilerplate_percentage)}%
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Boilerplate</div>
        </div>
        <div
          className="rounded-lg p-3 text-center"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--color-border)' }}
        >
          <div
            className="text-2xl font-bold"
            style={{ color: scoreColor(originality_score) }}
          >
            {originality_score?.toFixed(1)}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Score / 10</div>
        </div>
      </div>

      {/* Assessment */}
      {assessment && (
        <div
          className="rounded-lg px-4 py-3 text-sm"
          style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--color-border)',
            color: 'var(--text-primary)',
          }}
        >
          <p className="text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
            ASSESSMENT
          </p>
          {assessment}
        </div>
      )}

      {/* Tutorial signals */}
      {tutorial_signals?.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            TUTORIAL SIGNALS
          </p>
          <div className="flex flex-wrap gap-1.5">
            {tutorial_signals.map((signal, i) => (
              <span
                key={i}
                className="text-xs px-2.5 py-1 rounded-full"
                style={{
                  background: 'rgba(245,158,11,0.15)',
                  color: '#f59e0b',
                  border: '1px solid rgba(245,158,11,0.3)',
                }}
              >
                {signal}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Original elements */}
      {original_elements?.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            ORIGINAL ELEMENTS
          </p>
          <div className="flex flex-wrap gap-1.5">
            {original_elements.map((element, i) => (
              <span
                key={i}
                className="text-xs px-2.5 py-1 rounded-full"
                style={{
                  background: 'rgba(34,197,94,0.15)',
                  color: '#22c55e',
                  border: '1px solid rgba(34,197,94,0.3)',
                }}
              >
                {element}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Findings */}
      {findings?.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
            FINDINGS
          </p>
          {findings.slice(0, 10).map((f, i) => (
            <div
              key={i}
              className="p-3 rounded-lg text-sm"
              style={{ background: 'var(--bg-secondary)', border: '1px solid var(--color-border)' }}
            >
              {f.area && (
                <div className="flex items-center gap-2 mb-1">
                  <Badge color="blue">{f.area}</Badge>
                </div>
              )}
              <p style={{ color: 'var(--text-secondary)' }}>
                {f.detail ?? f.message ?? ''}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
