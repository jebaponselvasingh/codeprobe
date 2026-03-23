

type BadgeColor = 'red' | 'amber' | 'green' | 'blue' | 'gray' | 'purple';

const colorMap: Record<BadgeColor, { bg: string; text: string }> = {
  red:    { bg: 'rgba(248,113,113,0.15)', text: 'var(--accent-red)' },
  amber:  { bg: 'rgba(251,191,36,0.15)',  text: 'var(--accent-amber)' },
  green:  { bg: 'rgba(52,211,153,0.15)',  text: 'var(--accent-green)' },
  blue:   { bg: 'rgba(79,143,247,0.15)',  text: 'var(--accent-blue)' },
  gray:   { bg: 'rgba(156,163,175,0.15)', text: 'var(--text-secondary)' },
  purple: { bg: 'rgba(167,139,250,0.15)', text: 'var(--accent-purple)' },
};

interface BadgeProps {
  children: React.ReactNode;
  color?: BadgeColor;
  className?: string;
}

export function Badge({ children, color = 'gray', className = '' }: BadgeProps) {
  const { bg, text } = colorMap[color];
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${className}`}
      style={{ background: bg, color: text }}
    >
      {children}
    </span>
  );
}
