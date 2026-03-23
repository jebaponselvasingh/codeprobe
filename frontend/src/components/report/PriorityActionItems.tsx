interface ActionItem {
  rank?: number
  severity: string
  title: string
  detail?: string
  description?: string
  file?: string
  estimated_hours?: number
  category?: string
}

interface Props {
  actions: ActionItem[]
}

export function PriorityActionItems({ actions }: Props) {
  const top5 = (actions || []).slice(0, 5)

  if (top5.length === 0)
    return (
      <div className="text-sm text-center py-8" style={{ color: 'var(--text-secondary)' }}>
        No priority actions generated
      </div>
    )

  return (
    <div className="flex flex-col gap-3">
      {top5.map((action, i) => {
        const sev = action.severity || 'medium'
        const colors = {
          critical: { bg: 'rgba(239,68,68,0.15)', text: '#ef4444', border: '#ef4444' },
          high: { bg: 'rgba(249,115,22,0.15)', text: '#f97316', border: '#f97316' },
          medium: { bg: 'rgba(234,179,8,0.15)', text: '#eab308', border: '#eab308' },
          low: { bg: 'rgba(156,163,175,0.1)', text: '#9ca3af', border: '#9ca3af' },
        }
        const c = colors[sev as keyof typeof colors] || colors.medium

        return (
          <div
            key={i}
            className="flex gap-4 p-4 rounded-lg"
            style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
          >
            {/* Rank badge */}
            <div
              className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm"
              style={{ background: c.bg, color: c.text, border: `2px solid ${c.border}` }}
            >
              {action.rank || i + 1}
            </div>

            <div className="flex-1 flex flex-col gap-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
                  {action.title}
                </span>
                <div className="flex gap-2 flex-shrink-0">
                  {action.estimated_hours && (
                    <span
                      className="text-xs px-2 py-0.5 rounded-full"
                      style={{ background: 'rgba(79,143,247,0.1)', color: 'var(--accent-blue)' }}
                    >
                      ~{action.estimated_hours}h
                    </span>
                  )}
                  <span
                    className="text-xs px-2 py-0.5 rounded-full capitalize"
                    style={{ background: c.bg, color: c.text }}
                  >
                    {sev}
                  </span>
                </div>
              </div>
              {(action.detail || action.description) && (
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  {action.detail || action.description}
                </p>
              )}
              {action.file && (
                <code className="text-xs" style={{ color: 'var(--text-muted, #999)' }}>
                  {action.file}
                </code>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
