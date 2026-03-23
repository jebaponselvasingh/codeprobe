interface HeatmapFile {
  file: string
  issue_count: number
  severity_sum: number
}

interface Props {
  files: HeatmapFile[]
}

export function CodeHeatmap({ files }: Props) {
  const sorted = [...(files || [])]
    .sort((a, b) => b.severity_sum - a.severity_sum)
    .slice(0, 15)

  if (sorted.length === 0)
    return (
      <div className="text-sm text-center py-4" style={{ color: 'var(--text-secondary)' }}>
        No heatmap data available
      </div>
    )

  const maxSeverity = sorted[0].severity_sum || 1

  return (
    <div className="flex flex-col gap-2">
      {sorted.map((item, i) => {
        const ratio = item.severity_sum / maxSeverity
        // Color: high ratio = red, medium = amber, low = green
        const color = ratio > 0.6 ? '#ef4444' : ratio > 0.3 ? '#f59e0b' : '#22c55e'
        const filename = item.file.split('/').pop() || item.file
        const dir = item.file.includes('/')
          ? item.file.substring(0, item.file.lastIndexOf('/') + 1)
          : ''

        return (
          <div key={i} className="flex items-center gap-3">
            <div className="w-48 flex-shrink-0 text-right">
              <span className="text-xs" style={{ color: 'var(--text-muted, #999)' }}>
                {dir}
              </span>
              <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                {filename}
              </span>
            </div>
            <div
              className="flex-1 h-5 rounded-sm overflow-hidden"
              style={{ background: 'var(--bg-secondary)' }}
            >
              <div
                className="h-full rounded-sm transition-all duration-500"
                style={{ width: `${ratio * 100}%`, background: color }}
              />
            </div>
            <div className="w-16 flex-shrink-0 text-right">
              <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                {item.issue_count} issues
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
