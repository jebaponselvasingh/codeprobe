
import type { CategoryScore } from '../../types/review';
import { scoreColor, categoryLabel } from '../../utils/scoreColor';

interface Props {
  categories: Record<string, CategoryScore>;
}

export function CategoryScoresGrid({ categories }: Props) {
  const entries = Object.entries(categories).sort((a, b) => b[1].score - a[1].score);

  return (
    <div className="card flex-1">
      <p className="text-xs font-medium mb-4" style={{ color: 'var(--text-secondary)' }}>CATEGORY SCORES</p>
      <div className="flex flex-col gap-3">
        {entries.map(([key, cat]) => (
          <div key={key}>
            <div className="flex justify-between text-xs mb-1">
              <span style={{ color: 'var(--text-primary)' }}>{categoryLabel(key)}</span>
              <span style={{ color: scoreColor(cat.score), fontWeight: 600 }}>
                {cat.score.toFixed(1)}
              </span>
            </div>
            <div
              className="h-2 rounded-full overflow-hidden"
              style={{ background: 'var(--bg-secondary)' }}
            >
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: `${(cat.score / 10) * 100}%`, background: scoreColor(cat.score) }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
