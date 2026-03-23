
import { RadialBarChart, RadialBar, ResponsiveContainer } from 'recharts';
import { scoreColor, gradeColor } from '../../utils/scoreColor';

interface Props {
  score: number;
  grade: string;
  durationSeconds?: number;
}

export function OverallScoreCard({ score, grade, durationSeconds }: Props) {
  const color = scoreColor(score);
  const data = [{ value: (score / 10) * 100, fill: color }];

  return (
    <div className="card flex flex-col items-center gap-4 min-w-[200px]">
      <div style={{ width: 160, height: 160, position: 'relative' }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="70%"
            outerRadius="100%"
            startAngle={90}
            endAngle={-270}
            data={data}
          >
            <RadialBar dataKey="value" background={{ fill: 'var(--bg-secondary)' }} isAnimationActive />
          </RadialBarChart>
        </ResponsiveContainer>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1 }}>
            {score.toFixed(1)}
          </span>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>/10</span>
        </div>
      </div>

      <div
        className="px-4 py-1 rounded-full font-bold text-xl"
        style={{ background: `${gradeColor(grade)}22`, color: gradeColor(grade) }}
      >
        Grade {grade}
      </div>

      {durationSeconds && (
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Reviewed in {Math.round(durationSeconds / 60)}m {durationSeconds % 60}s
        </p>
      )}
    </div>
  );
}
