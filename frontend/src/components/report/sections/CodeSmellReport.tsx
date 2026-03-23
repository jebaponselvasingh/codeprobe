import { Bug } from 'lucide-react';
import { Badge } from '../../shared/Badge';

interface SmellEntry {
  type: string;
  file: string;
  detail: string;
  line?: number;
}

interface SmellFinding {
  type: string;
  area: string;
  detail: string;
  file?: string;
  fix_hint?: string;
}

interface RefactoringSuggestion {
  title: string;
  before?: string;
  after?: string;
}

interface CodeSmells {
  smell_density?: number;
  smells?: SmellEntry[];
  findings?: SmellFinding[];
  code_quality_score?: number;
  refactoring_suggestions?: RefactoringSuggestion[];
}

interface Props {
  data: CodeSmells;
}

export function CodeSmellReport({ data }: Props) {
  const smells = data.smells ?? [];
  const findings = data.findings ?? [];
  const suggestions = data.refactoring_suggestions ?? [];

  // Group smells by type
  const byType = smells.reduce<Record<string, number>>((acc, s) => {
    acc[s.type] = (acc[s.type] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="card flex flex-col gap-5">
      <div className="flex items-center gap-2">
        <Bug size={18} style={{ color: 'var(--accent-amber)' }} />
        <h3 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
          Code Quality
        </h3>
        {data.code_quality_score !== undefined && (
          <span className="ml-auto text-sm font-bold" style={{ color: 'var(--accent-amber)' }}>
            {data.code_quality_score.toFixed(1)} / 10
          </span>
        )}
      </div>

      {/* Smell density bar */}
      {data.smell_density !== undefined && (
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span style={{ color: 'var(--text-secondary)' }}>Smell density (per 100 lines)</span>
            <span style={{ color: 'var(--accent-amber)' }}>{data.smell_density.toFixed(2)}</span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.min(100, data.smell_density * 10)}%`,
                background: 'var(--accent-amber)',
              }}
            />
          </div>
        </div>
      )}

      {/* Smell type breakdown */}
      {Object.keys(byType).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(byType).map(([type, count]) => (
            <div
              key={type}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs"
              style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
            >
              <span style={{ color: 'var(--text-primary)' }}>{type}</span>
              <Badge color="amber">{count}</Badge>
            </div>
          ))}
        </div>
      )}

      {/* LLM findings */}
      {findings.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
            ARCHITECTURAL ISSUES
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

      {/* Refactoring suggestions */}
      {suggestions.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            REFACTORING SUGGESTIONS
          </p>
          {suggestions.slice(0, 3).map((s, i) => (
            <div
              key={i}
              className="mb-2 p-3 rounded-lg text-sm"
              style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
            >
              <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                {s.title}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
