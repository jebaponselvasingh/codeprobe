import { describe, it, expect, vi, beforeEach } from 'vitest'
import { exportReportCsv } from '../../utils/csvExport'

// Mock DOM APIs
const mockClick = vi.fn()
const mockCreateObjectURL = vi.fn(() => 'blob:test')
const mockRevokeObjectURL = vi.fn()

beforeEach(() => {
  vi.spyOn(document, 'createElement').mockReturnValue({
    click: mockClick,
    href: '',
    download: '',
  } as any)
  global.URL.createObjectURL = mockCreateObjectURL
  global.URL.revokeObjectURL = mockRevokeObjectURL
})

const mockReport = {
  meta: { student_name: 'Alice', generated_at: '2026-01-01T00:00:00Z' },
  scores: {
    overall: 7.5,
    grade: 'B',
    categories: {
      code_quality: { score: 8.0, weight: 0.15, weighted: 1.2 },
      security: { score: 7.0, weight: 0.15, weighted: 1.05 },
    },
  },
  executive_summary: 'Good work.',
}

describe('csvExport', () => {
  it('creates a CSV blob and triggers download', () => {
    exportReportCsv(mockReport)
    expect(mockClick).toHaveBeenCalled()
    expect(mockCreateObjectURL).toHaveBeenCalledWith(expect.any(Blob))
  })

  it('revokes object URL after download', () => {
    exportReportCsv(mockReport)
    expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:test')
  })
})
