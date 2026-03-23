import { Badge } from '../shared/Badge';
import type { ProgressData } from '../../stores/historyStore';

interface VersionComparisonProps {
  data: ProgressData;
}

function IssueList({ items, color, emptyText }: {
  items: string[];
  color: 'green' | 'red' | 'amber';
  emptyText: string;
}) {
  if (items.length === 0) {
    return <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{emptyText}</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item, i) => (
        <Badge key={i} color={color}>{item}</Badge>
      ))}
    </div>
  );
}

export function VersionComparison({ data }: VersionComparisonProps) {
  if (data.versions.length < 2) return null;

  const latest = data.versions[data.versions.length - 1];
  const previous = data.versions[data.versions.length - 2];

  const scoreDelta = latest.overall_score - previous.overall_score;
  const deltaColor = scoreDelta > 0 ? 'var(--accent-green)' : scoreDelta < 0 ? 'var(--accent-red)' : 'var(--text-muted)';
  const deltaPrefix = scoreDelta > 0 ? '+' : '';

  return (
    <div className="card flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
          VERSION COMPARISON — v{previous.version} → v{latest.version}
        </p>
        <span className="text-sm font-semibold" style={{ color: deltaColor }}>
          {deltaPrefix}{scoreDelta.toFixed(1)} pts
        </span>
      </div>

      {/* Trends */}
      <div>
        <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>TRENDS</p>
        <div className="flex flex-wrap gap-2">
          {data.trends.improving.map(cat => (
            <Badge key={cat} color="green">↑ {cat.replace(/_/g, ' ')}</Badge>
          ))}
          {data.trends.declining.map(cat => (
            <Badge key={cat} color="red">↓ {cat.replace(/_/g, ' ')}</Badge>
          ))}
          {data.trends.stable.map(cat => (
            <Badge key={cat} color="gray">— {cat.replace(/_/g, ' ')}</Badge>
          ))}
          {data.trends.improving.length === 0 &&
           data.trends.declining.length === 0 &&
           data.trends.stable.length === 0 && (
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No trend data</p>
          )}
        </div>
      </div>

      {/* Resolved issues */}
      <div>
        <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>RESOLVED</p>
        <IssueList items={data.resolved_issues} color="green" emptyText="No resolved issues" />
      </div>

      {/* New issues */}
      <div>
        <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>NEW ISSUES</p>
        <IssueList items={data.new_issues} color="red" emptyText="No new issues" />
      </div>

      {/* Persistent issues */}
      <div>
        <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>PERSISTENT</p>
        <IssueList items={data.persistent_issues} color="amber" emptyText="No persistent issues" />
      </div>
    </div>
  );
}
