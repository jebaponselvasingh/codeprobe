import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PriorityActionItems } from '../../components/report/PriorityActionItems'

const mockActions = [
  {
    rank: 1,
    severity: 'critical',
    title: 'Fix SQL Injection',
    detail: 'User input not sanitized',
    file: 'backend/routes.py',
    estimated_hours: 2,
    category: 'security',
  },
  {
    rank: 2,
    severity: 'high',
    title: 'Add Error Boundaries',
    detail: 'Components may crash',
    estimated_hours: 1,
    category: 'error_handling',
  },
]

describe('PriorityActionItems', () => {
  it('renders action titles', () => {
    render(<PriorityActionItems actions={mockActions} />)
    expect(screen.getByText('Fix SQL Injection')).toBeInTheDocument()
    expect(screen.getByText('Add Error Boundaries')).toBeInTheDocument()
  })

  it('shows severity badges', () => {
    render(<PriorityActionItems actions={mockActions} />)
    expect(screen.getByText('critical')).toBeInTheDocument()
    expect(screen.getByText('high')).toBeInTheDocument()
  })

  it('shows time estimates', () => {
    render(<PriorityActionItems actions={mockActions} />)
    expect(screen.getByText('~2h')).toBeInTheDocument()
    expect(screen.getByText('~1h')).toBeInTheDocument()
  })

  it('shows file reference when present', () => {
    render(<PriorityActionItems actions={mockActions} />)
    expect(screen.getByText('backend/routes.py')).toBeInTheDocument()
  })

  it('limits to 5 actions', () => {
    const many = Array.from({ length: 10 }, (_, i) => ({
      rank: i + 1, severity: 'low', title: `Action ${i + 1}`, detail: '', estimated_hours: 1,
    }))
    render(<PriorityActionItems actions={many} />)
    // Only first 5 should render
    expect(screen.getByText('Action 1')).toBeInTheDocument()
    expect(screen.getByText('Action 5')).toBeInTheDocument()
    expect(screen.queryByText('Action 6')).not.toBeInTheDocument()
  })

  it('renders empty state when no actions', () => {
    render(<PriorityActionItems actions={[]} />)
    expect(screen.getByText(/no priority actions/i)).toBeInTheDocument()
  })
})
