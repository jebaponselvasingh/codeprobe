import { Download, FileText, Table, Copy, Check } from 'lucide-react'
import { useState } from 'react'
import { exportReportCsv } from '../../utils/csvExport'
import { exportReportPdf } from '../../utils/pdfExport'

export function ExportPanel({ report }: { report: any }) {
  const [copied, setCopied] = useState(false)
  const [exporting, setExporting] = useState(false)

  const handleJson = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report-${report.meta?.student_name || 'code'}-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handlePdf = async () => {
    setExporting(true)
    try {
      await exportReportPdf(
        'report-export-root',
        `report-${report.meta?.student_name || 'code'}.pdf`,
      )
    } finally {
      setExporting(false)
    }
  }

  const handleCsv = () => exportReportCsv(report)

  const handleCopy = async () => {
    const summary = [
      `Code Review — ${report.meta?.student_name || 'Student'}`,
      `Score: ${report.scores?.overall}/10 (${report.scores?.grade})`,
      `Generated: ${report.meta?.generated_at}`,
      '',
      report.executive_summary?.substring(0, 500),
    ].join('\n')

    await navigator.clipboard.writeText(summary)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const btnStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 14px',
    borderRadius: 8,
    border: '1px solid var(--border)',
    background: 'var(--bg-secondary)',
    color: 'var(--text-secondary)',
    fontSize: 13,
    cursor: 'pointer',
    transition: 'opacity 0.15s',
  } as const

  return (
    <div className="flex flex-wrap gap-2">
      <button style={btnStyle} onClick={handleJson}>
        <Download size={14} /> Export JSON
      </button>
      <button
        style={{ ...btnStyle, opacity: exporting ? 0.5 : 1 }}
        onClick={handlePdf}
        disabled={exporting}
      >
        <FileText size={14} /> {exporting ? 'Exporting...' : 'Export PDF'}
      </button>
      <button style={btnStyle} onClick={handleCsv}>
        <Table size={14} /> Export CSV
      </button>
      <button style={btnStyle} onClick={handleCopy}>
        {copied ? <Check size={14} /> : <Copy size={14} />}
        {copied ? 'Copied!' : 'Copy Summary'}
      </button>
    </div>
  )
}
