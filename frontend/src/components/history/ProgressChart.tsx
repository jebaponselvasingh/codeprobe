import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { ProgressData } from '../../stores/historyStore';

interface ProgressChartProps {
  data: ProgressData;
}

const COLORS = ['#4f8ff7', '#22d3ee', '#a78bfa', '#fb923c', '#34d399', '#f472b6'];

export function ProgressChart({ data }: ProgressChartProps) {
  // Determine top 5 categories by change range across versions
  const allCategories = data.versions.length > 0
    ? Object.keys(data.versions[0].scores_by_category)
    : [];

  const topCategories = allCategories
    .map(cat => {
      const vals = data.versions.map(v => v.scores_by_category[cat] ?? 0);
      const range = Math.max(...vals) - Math.min(...vals);
      return { cat, range };
    })
    .sort((a, b) => b.range - a.range)
    .slice(0, 5)
    .map(x => x.cat);

  const [hiddenLines, setHiddenLines] = useState<Set<string>>(new Set());

  const toggleLine = (key: string) => {
    setHiddenLines(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const chartData = data.versions.map(v => ({
    version: `v${v.version}`,
    overall: v.overall_score,
    ...Object.fromEntries(topCategories.map(cat => [cat, v.scores_by_category[cat] ?? 0])),
  }));

  if (chartData.length === 0) return null;

  return (
    <div className="card">
      <p className="text-xs font-medium mb-4" style={{ color: 'var(--text-secondary)' }}>
        SCORE PROGRESSION
      </p>

      {/* Toggle buttons */}
      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => toggleLine('overall')}
          className="text-xs px-2 py-0.5 rounded-full transition-opacity"
          style={{
            background: 'rgba(79,143,247,0.15)',
            color: '#4f8ff7',
            opacity: hiddenLines.has('overall') ? 0.4 : 1,
            border: '1px solid rgba(79,143,247,0.3)',
          }}
        >
          Overall
        </button>
        {topCategories.map((cat, i) => (
          <button
            key={cat}
            onClick={() => toggleLine(cat)}
            className="text-xs px-2 py-0.5 rounded-full transition-opacity"
            style={{
              background: `${COLORS[(i + 1) % COLORS.length]}22`,
              color: COLORS[(i + 1) % COLORS.length],
              opacity: hiddenLines.has(cat) ? 0.4 : 1,
              border: `1px solid ${COLORS[(i + 1) % COLORS.length]}44`,
            }}
          >
            {cat.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="version"
            tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--border)' }}
          />
          <YAxis
            domain={[0, 10]}
            tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--border)' }}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              color: 'var(--text-primary)',
              fontSize: 12,
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }}
          />
          {!hiddenLines.has('overall') && (
            <Line
              type="monotone"
              dataKey="overall"
              stroke={COLORS[0]}
              strokeWidth={2.5}
              dot={{ fill: COLORS[0], r: 4 }}
              name="Overall"
            />
          )}
          {topCategories.map((cat, i) =>
            !hiddenLines.has(cat) ? (
              <Line
                key={cat}
                type="monotone"
                dataKey={cat}
                stroke={COLORS[(i + 1) % COLORS.length]}
                strokeWidth={1.5}
                dot={{ fill: COLORS[(i + 1) % COLORS.length], r: 3 }}
                name={cat.replace(/_/g, ' ')}
                strokeDasharray="4 2"
              />
            ) : null
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
