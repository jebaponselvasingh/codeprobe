export function exportReportCsv(report: any) {
  const cats = report.scores?.categories || {}
  const rows = [
    ['Category', 'Score', 'Weight', 'Weighted'],
    ...Object.entries(cats).map(([cat, val]: [string, any]) => [
      cat, val.score?.toFixed(2), val.weight, val.weighted?.toFixed(3)
    ]),
    [],
    ['Overall Score', report.scores?.overall],
    ['Grade', report.scores?.grade],
    ['Student', report.meta?.student_name],
    ['Generated At', report.meta?.generated_at],
  ]

  const csv = rows.map(row => row.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `code-review-${report.meta?.student_name || 'report'}-${Date.now()}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
