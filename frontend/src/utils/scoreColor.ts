export function scoreColor(score: number): string {
  if (score >= 7) return 'var(--score-high)';
  if (score >= 4) return 'var(--score-mid)';
  return 'var(--score-low)';
}

export function gradeColor(grade: string): string {
  if (grade === 'A') return 'var(--accent-green)';
  if (grade === 'B') return '#60a5fa';
  if (grade === 'C') return 'var(--accent-amber)';
  if (grade === 'D') return '#f97316';
  return 'var(--accent-red)';
}

export function categoryLabel(key: string): string {
  const map: Record<string, string> = {
    code_quality: 'Code Quality', security: 'Security', architecture: 'Architecture',
    frontend: 'Frontend', backend: 'Backend', testing: 'Testing',
    performance: 'Performance', documentation: 'Documentation',
    accessibility: 'Accessibility', originality: 'Originality', requirements: 'Requirements',
  };
  return map[key] ?? key;
}
