import { Brain } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Badge } from '../../shared/Badge';

interface DangerFunction {
  name: string;
  file: string;
  complexity: number;
  line: number;
}

interface ComplexityData {
  avg_cyclomatic?: number;
  distribution?: { low?: number; moderate?: number; high?: number; danger?: number };
  danger_functions?: DangerFunction[];
  maintainability_index?: number;
  complexity_score?: number;
  refactoring_suggestions?: Array<{ function_name: string; approach: string }>;
}

interface Props {
  data: ComplexityData;
}

const distColor: Record<string, string> = {
  low: 'var(--accent-green)',
  moderate: 'var(--accent-blue)',
  high: 'var(--accent-amber)',
  danger: 'var(--accent-red)',
};

export function ComplexityReport({ data }: Props) {
  const dist = data.distribution ?? {};
  const chartData = Object.entries(dist).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value: value ?? 0,
    fill: distColor[name] ?? 'var(--text-muted)',
  }));
  const dangerFuncs = data.danger_functions ?? [];

  return (
    <div className="card flex flex-col gap-5">
      <div className="flex items-center gap-2">
        <Brain size={18} style={{ color: 'var(--accent-purple)' }} />
        <h3 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
          Complexity Analysis
        </h3>
        {data.complexity_score !== undefined && (
          <span className="ml-auto text-sm font-bold" style={{ color: 'var(--accent-purple)' }}>
            {data.complexity_score.toFixed(1)} / 10
          </span>
        )}
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 gap-3">
        <div
          className="rounded-lg p-3"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
        >
          <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
            Avg Cyclomatic
          </div>
          <div className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {data.avg_cyclomatic?.toFixed(1) ?? '—'}
          </div>
        </div>
        <div
          className="rounded-lg p-3"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
        >
          <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
            Maintainability
          </div>
          <div className="text-xl font-bold" style={{ color: 'var(--accent-purple)' }}>
            {data.maintainability_index?.toFixed(1) ?? '—'} / 10
          </div>
        </div>
      </div>

      {/* Distribution chart */}
      {chartData.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            COMPLEXITY DISTRIBUTION
          </p>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={chartData} barSize={32}>
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis hide />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  fontSize: 12,
                }}
                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Most complex functions */}
      {dangerFuncs.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
            MOST COMPLEX FUNCTIONS
          </p>
          <div className="flex flex-col gap-1.5">
            {dangerFuncs.slice(0, 8).map((f, i) => (
              <div
                key={i}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm"
                style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
              >
                <Badge color={f.complexity >= 15 ? 'red' : f.complexity >= 10 ? 'amber' : 'blue'}>
                  {f.complexity}
                </Badge>
                <span
                  className="font-mono text-xs flex-1 truncate"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {f.name}
                </span>
                <span
                  className="text-xs truncate"
                  style={{ color: 'var(--text-muted)', maxWidth: 160 }}
                >
                  {f.file}:{f.line}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
