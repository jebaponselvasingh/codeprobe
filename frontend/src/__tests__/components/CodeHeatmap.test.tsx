import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CodeHeatmap } from '../../components/report/CodeHeatmap'

const mockFiles = [
  { file: 'src/components/Dashboard.tsx', issue_count: 8, severity_sum: 14 },
  { file: 'backend/services/orders.py', issue_count: 5, severity_sum: 12 },
  { file: 'src/utils/helpers.ts', issue_count: 2, severity_sum: 3 },
]

describe('CodeHeatmap', () => {
  it('renders file names', () => {
    render(<CodeHeatmap files={mockFiles} />)
    expect(screen.getByText('Dashboard.tsx')).toBeInTheDocument()
    expect(screen.getByText('orders.py')).toBeInTheDocument()
  })

  it('shows issue counts', () => {
    render(<CodeHeatmap files={mockFiles} />)
    expect(screen.getByText('8 issues')).toBeInTheDocument()
    expect(screen.getByText('5 issues')).toBeInTheDocument()
  })

  it('renders empty state when no files', () => {
    render(<CodeHeatmap files={[]} />)
    expect(screen.getByText(/no heatmap data/i)).toBeInTheDocument()
  })

  it('limits to 15 files', () => {
    const many = Array.from({ length: 20 }, (_, i) => ({
      file: `src/file${i}.ts`,
      issue_count: i,
      severity_sum: i * 2,
    }))
    const { container } = render(<CodeHeatmap files={many} />)
    // Should only render 15 bars
    const rows = container.querySelectorAll('.flex.items-center.gap-3')
    expect(rows.length).toBeLessThanOrEqual(15)
  })
})
