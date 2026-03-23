import { useState } from 'react';
import type { Finding } from '../../types/review';
import { FindingCard } from './FindingCard';
import { Badge } from '../shared/Badge';

interface Props {
  findings: { critical: Finding[]; suggestions: Finding[]; strengths: Finding[] };
}

type Tab = 'critical' | 'suggestions' | 'strengths';

export function FindingsPanel({ findings }: Props) {
  const [tab, setTab] = useState<Tab>('critical');

  const tabs: { id: Tab; label: string; icon: string; color: 'red' | 'amber' | 'green'; items: Finding[] }[] = [
    { id: 'critical',    label: 'Critical',    icon: '🔴', color: 'red',   items: findings.critical },
    { id: 'suggestions', label: 'Suggestions', icon: '💡', color: 'amber', items: findings.suggestions },
    { id: 'strengths',   label: 'Strengths',   icon: '✅', color: 'green', items: findings.strengths },
  ];

  return (
    <div className="card">
      <div className="flex gap-2 mb-4">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all"
            style={{
              background: tab === t.id ? `rgba(79,143,247,0.12)` : 'var(--bg-secondary)',
              color: tab === t.id ? 'var(--accent-blue)' : 'var(--text-secondary)',
              border: tab === t.id ? '1px solid var(--accent-blue)' : '1px solid var(--border)',
            }}
          >
            {t.icon}
            <span>{t.label}</span>
            <Badge color={t.color}>{t.items.length}</Badge>
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-2">
        {tabs.find(t => t.id === tab)!.items.length === 0 ? (
          <p className="text-sm text-center py-6" style={{ color: 'var(--text-muted)' }}>
            No {tab} found
          </p>
        ) : (
          tabs.find(t => t.id === tab)!.items.map((f, i) => <FindingCard key={i} finding={f} />)
        )}
      </div>
    </div>
  );
}
