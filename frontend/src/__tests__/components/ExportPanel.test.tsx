import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ExportPanel } from '../../components/report/ExportPanel'

const mockReport = {
  meta: { student_name: 'Bob', generated_at: '2026-01-01T00:00:00Z', session_id: 'abc' },
  scores: { overall: 8.0, grade: 'A', categories: {} },
  executive_summary: 'Great work!',
}

afterEach(() => {
  vi.restoreAllMocks()
})

beforeEach(() => {
  global.URL.createObjectURL = vi.fn(() => 'blob:test')
  global.URL.revokeObjectURL = vi.fn()
  Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } })
  // Only intercept anchor elements, let React's createElement work normally
  const realCreate = document.createElement.bind(document)
  vi.spyOn(document, 'createElement').mockImplementation((tag: string, ...args: any[]) => {
    if (tag === 'a') {
      return { click: vi.fn(), href: '', download: '', style: {} } as any
    }
    return realCreate(tag, ...args)
  })
})

describe('ExportPanel', () => {
  it('renders all 4 export buttons', () => {
    render(<ExportPanel report={mockReport} />)
    expect(screen.getByText('Export JSON')).toBeInTheDocument()
    expect(screen.getByText(/Export PDF/)).toBeInTheDocument()
    expect(screen.getByText('Export CSV')).toBeInTheDocument()
    expect(screen.getByText('Copy Summary')).toBeInTheDocument()
  })

  it('triggers JSON download on click', () => {
    render(<ExportPanel report={mockReport} />)
    fireEvent.click(screen.getByText('Export JSON'))
    expect(URL.createObjectURL).toHaveBeenCalled()
  })

  it('copies summary to clipboard', async () => {
    render(<ExportPanel report={mockReport} />)
    fireEvent.click(screen.getByText('Copy Summary'))
    expect(navigator.clipboard.writeText).toHaveBeenCalled()
  })
})
